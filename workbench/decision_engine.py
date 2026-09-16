"""Local Jev-inspired decision layer for routing and approval recommendations."""

import json
import re
import uuid
from datetime import datetime, timezone


HIGH_RISK = re.compile(r"\b(delete|drop|destroy|format|credential|password|secret|deploy|production|payment|sudo|rm\s+-rf)\b", re.I)
PATCH_WORDS = re.compile(r"\b(fix|change|edit|patch|implement|refactor|update|add|remove)\b", re.I)
TEST_WORDS = re.compile(r"\b(test|check|validate|lint|typecheck|build|verify)\b", re.I)
BROWSER_WORDS = re.compile(r"\b(browser|webpage|website|click|navigate|login)\b", re.I)
MEDIA_WORDS = re.compile(r"\b(image|video|render|generate|comfyui|animate)\b", re.I)


def _rules(text):
    risk = "high" if HIGH_RISK.search(text) else "medium" if PATCH_WORDS.search(text) else "low"
    if TEST_WORDS.search(text):
        decision, agent = "test", "validator"
    elif BROWSER_WORDS.search(text):
        decision, agent = "browser", "browser-operator"
    elif MEDIA_WORDS.search(text):
        decision, agent = "media", "media-operator"
    elif PATCH_WORDS.search(text):
        decision, agent = "patch", "implementation"
    else:
        decision, agent = "plan", "investigator"
    return decision, agent, risk


def decide(task, model_answer=None):
    task = str(task).strip()
    if not task:
        raise ValueError("task is required")
    decision, agent, risk = _rules(task)
    confidence = 0.76 if decision in {"test", "browser", "media"} else 0.68
    if model_answer:
        try:
            parsed = json.loads(model_answer)
            if parsed.get("decision") in {"plan", "patch", "test", "browser", "sandbox", "media"}:
                decision = parsed["decision"]
            if parsed.get("next_agent"):
                agent = str(parsed["next_agent"])
            confidence = max(0.0, min(1.0, float(parsed.get("confidence", confidence))))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    needs_approval = risk != "low" or decision in {"patch", "browser", "sandbox", "media"}
    if HIGH_RISK.search(task):
        needs_approval = True
        confidence = min(confidence, 0.49)
    return {
        "id": "dec_" + uuid.uuid4().hex,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "confidence": round(confidence, 3),
        "risk": risk,
        "nextAgent": agent,
        "needsApproval": needs_approval,
        "reason": "Deterministic task classification with hard safety overrides.",
        "task": task,
    }
