#!/usr/bin/env python3
"""Minimal stdio MCP server for the standalone Colibri workbench."""

import json
import sys
import urllib.parse
import urllib.request
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def response(request_id, result=None, error=None):
    payload = {"jsonrpc": "2.0", "id": request_id}
    if error:
        payload["error"] = {"code": -32000, "message": error}
    else:
        payload["result"] = result
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def call(method, params):
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "colibri-workbench", "version": "0.1"}}
    if method == "notifications/initialized":
        return {}
    if method == "tools/list":
        return {"tools": [
            {"name": "project_status", "description": "Read the selected project's file count and path.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "project_memory", "description": "Read durable memory for the selected project.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "graph_query", "description": "Query the local Graphify project graph.", "inputSchema": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}},
        ]}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        base = os.environ.get("COLIBRI_WORKBENCH_URL", "http://127.0.0.1:8787").rstrip("/")
        if name == "project_status":
            data = json.loads(urllib.request.urlopen(base + "/api/status", timeout=10).read())
        elif name == "project_memory":
            data = json.loads(urllib.request.urlopen(base + "/api/memory", timeout=10).read())
        elif name == "graph_query":
            query = urllib.parse.quote(str(arguments.get("question", "")))
            data = json.loads(urllib.request.urlopen(base + "/api/graph/query?q=" + query, timeout=180).read())
        else:
            raise ValueError(f"unknown tool: {name}")
        return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]}
    raise ValueError(f"unsupported method: {method}")


for line in sys.stdin:
    try:
        request = json.loads(line)
        if "id" not in request:
            continue
        response(request["id"], call(request.get("method", ""), request.get("params") or {}))
    except Exception as error:
        response(request.get("id") if "request" in locals() else None, error=str(error))
