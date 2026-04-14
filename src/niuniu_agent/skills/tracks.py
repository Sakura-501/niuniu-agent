from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class TrackProfile:
    track_id: str
    name: str
    focus: str
    priorities: tuple[str, ...]
    recommended_skills: tuple[str, ...]


TRACK_PROFILES = {
    "track1": TrackProfile(
        track_id="track1",
        name="识器·明理",
        focus="20+ SRC 场景，侧重自动化众测与主流漏洞发现。",
        priorities=(
            "优先快速摸清 Web/接口攻击面",
            "优先验证主流漏洞而不是冷门路径",
            "优先可复现、可批量、可快速得分的思路",
        ),
        recommended_skills=(
            "resource-aware-execution",
            "web-surface-mapping",
            "web-content-discovery",
            "service-enumeration",
            "port-scan-operations",
            "web-vulnerability-testing",
            "api-workflow-testing",
            "evidence-capture",
        ),
    ),
    "track2": TrackProfile(
        track_id="track2",
        name="洞见·虚实",
        focus="聚焦典型 CVE、云安全及 AI 基础设施漏洞。",
        priorities=(
            "先做组件与版本识别",
            "再做 CVE 映射与云/AI 攻击面确认",
            "优先走已知高可信利用链",
        ),
        recommended_skills=(
            "resource-aware-execution",
            "service-enumeration",
            "port-scan-operations",
            "known-vulnerability-mapping",
            "cve-template-scanning",
            "cloud-asset-assessment",
            "cloud-security-enumeration",
            "web-vulnerability-testing",
            "evidence-capture",
        ),
    ),
    "track3": TrackProfile(
        track_id="track3",
        name="执刃·循迹",
        focus="模拟多层网络环境，考验多步攻击规划与权限维持。",
        priorities=(
            "持续记录当前 foothold、下一跳和失败路径",
            "优先多步攻击规划与横向移动",
            "注意权限维持与阶段目标推进",
        ),
        recommended_skills=(
            "resource-aware-execution",
            "service-enumeration",
            "port-scan-operations",
            "lateral-movement-planning",
            "tunnel-and-pivot-operations",
            "privilege-path-analysis",
            "linux-privilege-escalation",
            "persistence-operations",
            "evidence-capture",
        ),
    ),
    "track4": TrackProfile(
        track_id="track4",
        name="铸剑·止戈",
        focus="基础域渗透，模拟企业核心内网环境的推演。",
        priorities=(
            "先识别域结构、主机角色和关键资产",
            "再做域渗透与权限路径分析",
            "优先最短可行权限路径",
        ),
        recommended_skills=(
            "resource-aware-execution",
            "service-enumeration",
            "port-scan-operations",
            "directory-identity-enumeration",
            "domain-operations",
            "lateral-movement-planning",
            "tunnel-and-pivot-operations",
            "privilege-path-analysis",
            "linux-privilege-escalation",
            "persistence-operations",
            "evidence-capture",
        ),
    ),
}


CHALLENGE_TRACK_OVERRIDES = {
    "6RmRST2HkeTbwgbyMJaN": "track3",
    "K7kbx40FbhQNODZkS": "track3",
    "2ihdUTWqg7iVcvvD7GAZzOadCxS": "track3",
}


def infer_track(description: str, challenge_code: str | None = None) -> str:
    if challenge_code and challenge_code in CHALLENGE_TRACK_OVERRIDES:
        return CHALLENGE_TRACK_OVERRIDES[challenge_code]
    haystack = description.lower()
    tokens = set(re.findall(r"[a-zA-Z0-9_]+", haystack))
    if any(keyword in haystack for keyword in ("domain", "ldap", "kerberos", "内网", "域")):
        return "track4"
    if any(keyword in haystack for keyword in ("pivot", "lateral", "foothold", "内网跳板", "横向")):
        return "track3"
    if any(keyword in tokens for keyword in ("cve", "cloud", "bucket", "metadata", "ai", "llm", "model")):
        return "track2"
    return "track1"
