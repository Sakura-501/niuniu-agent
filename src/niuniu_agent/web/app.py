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


class ModelRoutingRequest(BaseModel):
    provider_id: str
    model_override: str | None = None


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
            <h3>Model Routing</h3>
            <div id="model-routing-summary" class="card-list"></div>
            <div class="button-row" style="margin-top:12px;">
              <select id="provider-select"></select>
              <input id="provider-model" placeholder="模型名，可留空使用供应商默认模型" style="flex:1; min-width:240px; border-radius:14px; border:1px solid var(--line); padding:11px 14px; font:inherit; background:#fff;" />
              <button id="apply-provider">Apply</button>
              <button id="reset-provider" class="secondary">Reset Auto</button>
            </div>
          </section>
          <section class="panel">
            <h3>Callback Resources</h3>
            <div id="operator-resources" class="card-list"></div>
          </section>
          <section class="panel">
            <h3>Challenges</h3>
            <div id="challenge-list" class="card-list"></div>
          </section>
          <section class="panel">
            <h3>Recent Flow</h3>
            <pre id="recent-events">loading...</pre>
          </section>
          <section class="panel">
            <h3>Data Sources</h3>
            <pre id="data-sources">loading...</pre>
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

        function renderAgentTree(tree) {
          const target = document.getElementById('agent-list');
          target.innerHTML = '';
          for (const group of tree || []) {
            const details = document.createElement('details');
            details.className = 'card';
            details.open = true;
            const manager = group.manager || {};
            const summary = document.createElement('summary');
            const managerControls = manager.agent_id && manager.agent_id.startsWith('manager:competition:') ? `
              <div class="button-row" style="margin-top:10px;">
                <button data-stop-agent="${manager.agent_id}">Stop</button>
                <button class="secondary" data-delete-agent="${manager.agent_id}">Delete</button>
              </div>
            ` : '';
            summary.innerHTML = `
              <strong><a href="/agents/${encodeURIComponent(manager.agent_id || '')}">${manager.agent_id || 'manager'}</a></strong>
              <span class="muted"> · ${manager.status || ''}</span>
              <div class="mono">${manager.summary || ''}</div>
              ${managerControls}
            `;
            details.appendChild(summary);

            const list = document.createElement('div');
            list.className = 'card-list';
            list.style.marginTop = '12px';
            for (const worker of group.workers || []) {
              const item = document.createElement('div');
              item.className = 'card';
              const controls = worker.role === 'challenge_worker' ? `
                <div class="button-row" style="margin-top:10px;">
                  <button data-pause-agent="${worker.agent_id}">Pause</button>
                  <button class="secondary" data-delete-agent="${worker.agent_id}">Delete</button>
                </div>
              ` : '';
              item.innerHTML = `
                <strong><a href="/agents/${encodeURIComponent(worker.agent_id)}">${worker.agent_id}</a></strong>
                <div class="muted">${worker.role || ''} · ${worker.status || ''}</div>
                <div class="mono">${worker.summary || ''}</div>
                ${controls}
              `;
              list.appendChild(item);
            }
            if (!(group.workers || []).length) {
              const empty = document.createElement('div');
              empty.className = 'card muted';
              empty.textContent = 'no workers';
              list.appendChild(empty);
            }
            details.appendChild(list);
            target.appendChild(details);
          }
          if (!(tree || []).length) {
            target.innerHTML = '<div class="card muted">no data</div>';
          }
        }

        async function loadOverview() {
          const data = await api('/api/overview');
          renderCardList('process-list', Object.entries(data.process), ([name, state]) => `
            <strong>${name}</strong>
            <div class="muted mono">${JSON.stringify(state, null, 2)}</div>
          `);
          const routing = data.model_routing || {};
          renderCardList('model-routing-summary', routing.providers || [], (provider) => `
            <strong>${provider.display_name} (${provider.provider_id})</strong>
            <div class="muted">base_url=${provider.base_url}</div>
            <div class="muted">default_model=${provider.model} · effective_model=${provider.effective_model}</div>
            <div class="muted">selected=${provider.selected} · failures=${(provider.state && provider.state.consecutive_failures) || 0} · successes=${(provider.state && provider.state.total_successes) || 0}</div>
            <div class="mono">${provider.state && provider.state.last_error ? provider.state.last_error : 'no provider errors'}</div>
          `);
          const resources = data.operator_resources || {};
          renderCardList('operator-resources', Object.entries(resources), ([name, resource]) => `
            <strong>${name}</strong>
            <div class="muted">host=${resource.host || ''}</div>
            <div class="muted">username=${resource.username || ''}</div>
            <div class="mono">password=${resource.password || ''}</div>
            <div class="muted">${resource.usage || ''}</div>
          `);
          const providerSelect = document.getElementById('provider-select');
          const providerModelInput = document.getElementById('provider-model');
          providerSelect.innerHTML = '';
          for (const provider of routing.providers || []) {
            const option = document.createElement('option');
            option.value = provider.provider_id;
            option.textContent = `${provider.display_name} (${provider.provider_id})`;
            option.selected = provider.provider_id === routing.selected_provider_id;
            option.dataset.defaultModel = provider.model || '';
            providerSelect.appendChild(option);
          }
          providerSelect.onchange = () => {
            const selected = providerSelect.options[providerSelect.selectedIndex];
            providerModelInput.value = selected ? (selected.dataset.defaultModel || '') : '';
          };
          providerModelInput.value = routing.selected_model || '';
          renderAgentTree(data.agent_tree || []);
          renderCardList('challenge-list', data.contest.challenges || [], (challenge) => `
            <strong><a href="/challenges/${encodeURIComponent(challenge.code)}">${challenge.code}</a> · ${challenge.title}</strong>
            <div class="muted">instance=${challenge.instance_status} · completed=${challenge.completed} · hint_viewed=${challenge.hint_viewed}</div>
            <div class="muted">scheduler=${challenge.scheduler_status || 'unknown'} · reason=${challenge.scheduler_reason || ''}</div>
            <div class="mono">${(challenge.notes && Object.keys(challenge.notes).length) ? JSON.stringify(challenge.notes, null, 2) : 'no notes'}</div>
          `);
          document.getElementById('recent-events').textContent = JSON.stringify(data.recent_agent_events || [], null, 2);
          document.getElementById('data-sources').textContent = JSON.stringify({
            contest_capabilities: data.contest_capabilities || [],
            data_sources: data.data_sources || {},
          }, null, 2);
          document.querySelectorAll('[data-stop-agent]').forEach((button) => {
            button.onclick = async () => {
              await api(`/api/agents/${encodeURIComponent(button.dataset.stopAgent)}/stop`, {method: 'POST'});
              await loadOverview();
            };
          });
          document.querySelectorAll('[data-pause-agent]').forEach((button) => {
            button.onclick = async () => {
              await api(`/api/agents/${encodeURIComponent(button.dataset.pauseAgent)}/pause`, {method: 'POST'});
              await loadOverview();
            };
          });
          document.querySelectorAll('[data-delete-agent]').forEach((button) => {
            button.onclick = async () => {
              await api(`/api/agents/${encodeURIComponent(button.dataset.deleteAgent)}`, {method: 'DELETE'});
              await loadOverview();
            };
          });
        }

        document.getElementById('start-competition').onclick = async () => { await api('/api/competition/start', {method: 'POST'}); await loadOverview(); };
        document.getElementById('stop-competition').onclick = async () => { await api('/api/competition/stop', {method: 'POST'}); await loadOverview(); };
        document.getElementById('restart-competition').onclick = async () => { await api('/api/competition/restart', {method: 'POST'}); await loadOverview(); };
        document.getElementById('apply-provider').onclick = async () => {
          await api('/api/model-routing/select', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              provider_id: document.getElementById('provider-select').value,
              model_override: document.getElementById('provider-model').value || null,
            }),
          });
          await loadOverview();
        };
        document.getElementById('reset-provider').onclick = async () => {
          await api('/api/model-routing/reset', {method: 'POST'});
          await loadOverview();
        };
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
              <button id="stop-debug" class="secondary">Stop Session</button>
              <button id="delete-debug" class="secondary">Delete Session</button>
            </div>
            <pre id="debug-session-state">no session</pre>
          </section>
          <section class="panel">
            <h3>Conversation</h3>
            <div id="chat-log" class="chat-log"></div>
          </section>
        </div>
        """
        script = """
        const SESSION_KEY = 'niuniu-agent-debug-session-id';
        let sessionId = localStorage.getItem(SESSION_KEY) || null;

        function addBubble(kind, text) {
          const log = document.getElementById('chat-log');
          const div = document.createElement('div');
          div.className = `bubble ${kind}`;
          div.textContent = text;
          log.appendChild(div);
          log.scrollTop = log.scrollHeight;
          return div;
        }

        function renderTranscript(session) {
          const log = document.getElementById('chat-log');
          log.innerHTML = '';
          for (const item of session.transcript || []) {
            const kind = item.role === 'tool' ? 'tool' : item.role;
            addBubble(kind, item.text || '');
          }
          if (session.partial_output) {
            addBubble('assistant', session.partial_output);
          }
          document.getElementById('debug-session-state').textContent = JSON.stringify({
            session_id: session.session_id,
            status: session.status,
            agent_id: session.agent_id,
          }, null, 2);
        }

        async function loadSession() {
          if (!sessionId) {
            document.getElementById('debug-session-state').textContent = 'no session';
            document.getElementById('chat-log').innerHTML = '';
            return;
          }
          const response = await fetch(`/api/debug/sessions/${encodeURIComponent(sessionId)}`);
          if (!response.ok) return;
          const session = await response.json();
          renderTranscript(session);
        }

        async function ensureSession() {
          if (sessionId) return sessionId;
          const response = await fetch('/api/debug/sessions', {method: 'POST'});
          const payload = await response.json();
          sessionId = payload.session_id;
          localStorage.setItem(SESSION_KEY, sessionId);
          await loadSession();
          return sessionId;
        }

        async function sendDebug() {
          const message = document.getElementById('debug-input').value.trim();
          if (!message) return;
          document.getElementById('debug-input').value = '';
          const sid = await ensureSession();
          const response = await fetch(`/api/debug/sessions/${encodeURIComponent(sid)}/messages`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message}),
          });
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
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
                await loadSession();
                continue;
              }
              if (event === 'model' || event === 'final' || event === 'done') await loadSession();
            }
          }
          await loadSession();
        }

        async function stopDebugSession() {
          if (!sessionId) return;
          await fetch(`/api/agents/${encodeURIComponent(`debug:${sessionId}`)}/stop`, {method: 'POST'});
          await loadSession();
        }

        async function deleteDebugSession() {
          if (!sessionId) return;
          await fetch(`/api/agents/${encodeURIComponent(`debug:${sessionId}`)}`, {method: 'DELETE'});
          localStorage.removeItem(SESSION_KEY);
          sessionId = null;
          await loadSession();
        }

        document.getElementById('send-debug').onclick = sendDebug;
        document.getElementById('stop-debug').onclick = stopDebugSession;
        document.getElementById('delete-debug').onclick = deleteDebugSession;
        loadSession();
        setInterval(loadSession, 2000);
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
          document.getElementById('challenge-detail').innerHTML = `
            <div class="card"><strong>availability</strong><div class="mono">${{data.availability}}</div></div>
            <div class="card"><strong>official</strong><div class="mono">${{JSON.stringify(data.official || null, null, 2)}}</div></div>
            <div class="card"><strong>local</strong><div class="mono">${{JSON.stringify(data.local || null, null, 2)}}</div></div>
            <div class="card"><strong>scheduler</strong><div class="mono">${{JSON.stringify({{status:(data.official||{{}}).scheduler_status, reason:(data.official||{{}}).scheduler_reason, workers:(data.official||{{}}).assigned_workers}}, null, 2)}}</div></div>
            <div class="card"><strong>source_summary</strong><div class="mono">${{JSON.stringify(data.source_summary || null, null, 2)}}</div></div>
          `;
          document.getElementById('challenge-events').textContent = JSON.stringify((data.local && data.local.events) || [], null, 2);
        }}
        loadChallenge();
        setInterval(loadChallenge, 5000);
        """
        return HTMLResponse(page_shell(f"Challenge · {code}", body, script))

    @app.get("/agents/{agent_id}", response_class=HTMLResponse)
    async def agent_page(agent_id: str) -> HTMLResponse:
        controls = (
            '<button id="stop-agent">Stop</button><button id="delete-agent" class="secondary">Delete</button>'
            if agent_id.startswith("debug:")
            else '<button id="pause-agent">Pause</button><button id="delete-agent" class="secondary">Delete</button>'
        )
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
          document.getElementById('agent-detail').innerHTML = `
            <div class="card mono">${{JSON.stringify(data.status || {{}}, null, 2)}}</div>
            <div class="button-row" style="margin-top:12px;">
              {controls}
            </div>
          `;
          document.getElementById('agent-events').textContent = JSON.stringify(data.events || [], null, 2);
          const stopButton = document.getElementById('stop-agent');
          const pauseButton = document.getElementById('pause-agent');
          const deleteButton = document.getElementById('delete-agent');
          if (stopButton) stopButton.onclick = async () => {{ await fetch('/api/agents/{html.escape(agent_id)}/stop', {{method: 'POST'}}); await loadAgent(); }};
          if (pauseButton) pauseButton.onclick = async () => {{ await fetch('/api/agents/{html.escape(agent_id)}/pause', {{method: 'POST'}}); await loadAgent(); }};
          if (deleteButton) deleteButton.onclick = async () => {{ await fetch('/api/agents/{html.escape(agent_id)}', {{method: 'DELETE'}}); window.location.href = '/'; }};
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

    @app.get("/api/model-routing")
    async def api_get_model_routing(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).get_model_routing())

    @app.post("/api/model-routing/select")
    async def api_select_model_routing(payload: ModelRoutingRequest, request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).select_model_routing(payload.provider_id, payload.model_override))

    @app.post("/api/model-routing/reset")
    async def api_reset_model_routing(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).reset_model_routing())

    @app.post("/api/debug/sessions")
    async def api_create_debug_session(request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).create_debug_session())

    @app.get("/api/debug/sessions/{session_id}")
    async def api_get_debug_session(session_id: str, request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).get_debug_session(session_id))

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

    @app.post("/api/agents/{agent_id}/stop")
    async def api_stop_agent(agent_id: str, request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).stop_agent(agent_id))

    @app.post("/api/agents/{agent_id}/pause")
    async def api_pause_agent(agent_id: str, request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).pause_agent(agent_id))

    @app.delete("/api/agents/{agent_id}")
    async def api_delete_agent(agent_id: str, request: Request) -> JSONResponse:
        return JSONResponse(await current_service(request).delete_agent(agent_id))

    return app


app = create_app()
