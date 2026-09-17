"""Optional server-side TypeSafe judgment adapter."""

import json
import os
import urllib.request


def evaluate(state, questions):
    api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY is not configured")
    payload = json.dumps({"state": state, "model": "jev-latest", "questions": questions}).encode("utf-8")
    request = urllib.request.Request(
        os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai/v1/systemone"),
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise RuntimeError(f"TypeSafe request failed: {error}") from error