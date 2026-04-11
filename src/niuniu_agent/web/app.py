from __future__ import annotations

from contextlib import asynccontextmanager
import html
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from niuniu_agent.web.service import AgentWebService, page_shell


class DebugMessageRequest(BaseModel):
    message: str


def create_app(service: object | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if service is not None:
            app.state.service = service
            yield
            return
        default_service = AgentWebService()
        await default_service.startup()
        app.state.service = default_service
        try:
            yield
        finally:
            await default_service.shutdown()

    app = FastAPI(title="niuniu-agent web console", lifespan=lifespan)
    if service is not None:
        app.state.service = service

    def current_service(request: Request):
        return request.app.state.service

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        body = """
        <div class="layout">
          <section class="panel">
            <div class="eyebrow">Operator Actions</div>
            <h2>Agent Console</h2>
            <p class="muted">通过这个页面查看比赛状态、manager / worker agent、最近执行流程，并一键启动或重启比赛执行。</p>
            <div class="button-row">
              <button id="start-competition">Start Competition</button>
              <button id="stop-competition" class="secondary">Stop Competition</button>
              <button id="restart-competition" class="secondary">Restart Competition</button>
            </div>
          </section>
          <div class="grid-2">
            <section class="panel">
              <h3>Processes</h3>
              <div id="process-list" class="card-list"></div>
            </section>
            <section class="panel">
              <h3>Agents</h3>
              <div id="agent-list" class="card-list"></div>
            </section>
          </div>
          <section class="panel">
            <h3>Challenges</h3>
            <div id="challenge-list" class="card-list"></div>
          </section>
          <section class="panel">
            <h3>Recent Flow</h3>
            <pre id="recent-events">loading...</pre>
          </section>
        </div>
        """
        script = """
        async function api(path, options = {}) {
          const response = await fetch(path, options);
          if (!response.ok) throw new Error(await response.text());
          return response.json();
        }

        function renderCardList(targetId, items, formatter) {
          const target = document.getElementById(targetId);
          target.innerHTML = "";
          for (const item of items) {
            const div = document.createElement("div");
            div.className = "card";
            div.innerHTML = formatter(item);
            target.appendChild(div);
          }
          if (!items.length) target.innerHTML = '<div class="card muted">no data</div>';
        }

        async function loadOverview() {
          const data = await api('/api/overview');
          renderCardList('process-list', Object.entries(data.process), ([name, state]) => `
            <strong>${name}</strong>
            <div class="muted mono">${JSON.stringify(state, null, 2)}</div>
          `);
          renderCardList('agent-list', data.agents || [], (agent) => `
            <strong><a href="/agents/${encodeURIComponent(agent.agent_id)}">${agent.agent_id}</a></strong>
            <div class="muted">${agent.role} · ${agent.status}</div>
            <div class="mono">${agent.summary || ''}</div>
          `);
          renderCardList('challenge-list', data.contest.challenges || [], (challenge) => `
            <strong><a href="/challenges/${encodeURIComponent(challenge.code)}">${challenge.code}</a> · ${challenge.title}</strong>
            <div class="muted">instance=${challenge.instance_status} · completed=${challenge.completed}</div>
            <div class="mono">${(challenge.notes && Object.keys(challenge.notes).length) ? JSON.stringify(challenge.notes, null, 2) : 'no notes'}</div>
          `);
          document.getElementById('recent-events').textContent = JSON.stringify(data.recent_agent_events || [], null, 2);
        }

        document.getElementById('start-competition').onclick = async () => { await api('/api/competition/start', {method: 'POST'}); await loadOverview(); };
        document.getElementById('stop-competition').onclick = async () => { await api('/api/competition/stop', {method: 'POST'}); await loadOverview(); };
        document.getElementById('restart-competition').onclick = async () => { await api('/api/competition/restart', {method: 'POST'}); await loadOverview(); };
        loadOverview();
        setInterval(loadOverview, 5000);
        """
        return HTMLResponse(page_shell("Agent Console", body, script))

    @app.get("/debug", response_class=HTMLResponse)
    async def debug_page() -> HTMLResponse:
        body = """
        <div class="grid-2">
          <section class="panel">
            <div class="eyebrow">Online Debug</div>
            <h2>Debug Chat</h2>
            <p class="muted">这里直接调用 debug agent，支持流式展示模型输出和工具事件。</p>
            <textarea id="debug-input" placeholder="输入调试问题，例如：查看当前任务状态，并总结每题进度"></textarea>
            <div class="button-row" style="margin-top:12px;">
              <button id="send-debug">Send</button>
            </div>
          </section>
          <section class="panel">
            <h3>Conversation</h3>
            <div id="chat-log" class="chat-log"></div>
          </section>
        </div>
        """
        script = """
        let sessionId = null;

        function addBubble(kind, text) {
          const log = document.getElementById('chat-log');
          const div = document.createElement('div');
          div.className = `bubble ${kind}`;
          div.textContent = text;
          log.appendChild(div);
          log.scrollTop = log.scrollHeight;
          return div;
        }

        async function ensureSession() {
          if (sessionId) return sessionId;
          const response = await fetch('/api/debug/sessions', {method: 'POST'});
          const payload = await response.json();
          sessionId = payload.session_id;
          return sessionId;
        }

        async function sendDebug() {
          const message = document.getElementById('debug-input').value.trim();
          if (!message) return;
          document.getElementById('debug-input').value = '';
          addBubble('user', message);
          const sid = await ensureSession();
          const response = await fetch(`/api/debug/sessions/${encodeURIComponent(sid)}/messages`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message}),
          });
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let finalBubble = null;
          while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            const chunks = buffer.split('\\n\\n');
            buffer = chunks.pop();
            for (const chunk of chunks) {
              const eventMatch = chunk.match(/^event:\\s*(.+)$/m);
              const dataMatch = chunk.match(/^data:\\s*(.+)$/m);
              if (!eventMatch || !dataMatch) continue;
              const event = eventMatch[1].trim();
              const payload = JSON.parse(dataMatch[1]);
              if (event === 'tool_start' || event === 'tool_done' || event === 'error') {
                addBubble('tool', `${event}: ${JSON.stringify(payload, null, 2)}`);
                continue;
              }
              if (event === 'final' || event === 'done') {
                if (!finalBubble) finalBubble = addBubble('assistant', '');
                finalBubble.textContent += payload.text || '';
                continue;
              }
              if (event === 'model') {
                if (!finalBubble) finalBubble = addBubble('assistant', '');
                finalBubble.textContent += payload.text || '';
              }
            }
          }
        }

        document.getElementById('send-debug').onclick = sendDebug;
        """
        return HTMLResponse(page_shell("Debug Chat", body, script))

    @app.get("/challenges/{code}", response_class=HTMLResponse)
    async def challenge_page(code: str) -> HTMLResponse:
        body = f"""
        <div class="layout">
          <section class="panel">
            <div class="eyebrow">Challenge Detail</div>
            <h2>{html.escape(code)}</h2>
            <div id="challenge-detail" class="card-list"></div>
          </section>
          <section class="panel">
            <h3>Execution Flow</h3>
            <pre id="challenge-events">loading...</pre>
          </section>
        </div>
        """
        script = f"""
        async function loadChallenge() {{
          const response = await fetch('/api/challenges/{html.escape(code)}');
          const data = await response.json();
          document.getElementById('challenge-detail').innerHTML = `<div class="card mono">${{JSON.stringify(data.challenge || {{}}, null, 2)}}</div>`;
          document.getElementById('challenge-events').textContent = JSON.stringify(data.events || [], null, 2);
        }}
        loadChallenge();
        setInterval(loadChallenge, 5000);
        """
        return HTMLResponse(page_shell(f"Challenge · {code}", body, script))

    @app.get("/agents/{agent_id}", response_class=HTMLResponse)
    async def agent_page(agent_id: str) -> HTMLResponse:
        body = f"""
        <div class="layout">
          <section class="panel">
            <div class="eyebrow">Agent Detail</div>
            <h2>{html.escape(agent_id)}</h2>
            <div id="agent-detail" class="card-list"></div>
          </section>
          <section class="panel">
            <h3>Agent Events</h3>
            <pre id="agent-events">loading...</pre>
          </section>
        </div>
        """
        script = f"""
        async function loadAgent() {{
          const response = await fetch('/api/agents/{html.escape(agent_id)}');
          const data = await response.json();
          document.getElementById('agent-detail').innerHTML = `<div class="card mono">${{JSON.stringify(data.status || {{}}, null, 2)}}</div>`;
          document.getElementById('agent-events').textContent = JSON.stringify(data.events || [], null, 2);
        }}
        loadAgent();
        setInterval(loadAgent, 5000);
        """
        return HTMLResponse(page_shell(f"Agent · {agent_id}", body, script))

    @app.get("/api/overview")
    async def api_overview(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).overview())

    @app.get("/api/challenges/{code}")
    async def api_challenge_detail(code: str, request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).challenge_detail(code))

    @app.get("/api/agents/{agent_id}")
    async def api_agent_detail(agent_id: str, request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).agent_detail(agent_id))

    @app.post("/api/competition/start")
    async def api_start_competition(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).start_competition())

    @app.post("/api/competition/stop")
    async def api_stop_competition(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).stop_competition())

    @app.post("/api/competition/restart")
    async def api_restart_competition(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).restart_competition())

    @app.post("/api/debug/sessions")
    async def api_create_debug_session(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).create_debug_session())

    @app.post("/api/debug/sessions/{session_id}/messages")
    async def api_debug_message(
        session_id: str,
        payload: DebugMessageRequest,
        request: Request,
    ) -> StreamingResponse:
        if not payload.message.strip():
            raise HTTPException(status_code=400, detail="message is required")
        return StreamingResponse(
            current_service(request).stream_debug_reply(session_id, payload.message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return app


app = create_app()
