#!/usr/bin/env python3
"""Local control plane for the Colibri visual workbench.

Binds to localhost only. It exposes project inspection, command execution, and
local-model requests for the browser UI. It is intentionally separate from
PBOMNI and any target project's runtime.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

WORKBENCH_DIR = Path(__file__).resolve().parent
DEFAULT_PROJECT = WORKBENCH_DIR.parent
MAX_BODY = 2 * 1024 * 1024
MAX_OUTPUT = 120_000
IGNORED_DIRS = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv", "venv"}
TEXT_SUFFIXES = {".c", ".cc", ".cpp", ".h", ".hpp", ".js", ".mjs", ".ts", ".tsx", ".py", ".json", ".md", ".sql", ".ps1", ".sh", ".toml", ".yml", ".yaml"}


def safe_path(root, value):
    candidate = (root / (value or ".")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("path is outside the configured project") from error
    return candidate


def list_files(root):
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path.relative_to(root).as_posix())
    return sorted(files)[:5000]


def json_response(handler, status, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    origin = handler.headers.get("Origin", "")
    allowed_origin = origin if origin in {"http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000", "http://localhost:8000"} else "http://127.0.0.1:5173"
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", allowed_origin)
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(data)


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "ColibriWorkbench/0.1"

    @property
    def root(self):
        return self.server.project_root

    def log_message(self, format, *args):
        sys.stderr.write("[workbench] " + format % args + "\n")

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("request body is too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_OPTIONS(self):
        json_response(self, 204, {})

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == "/api/status":
                json_response(self, 200, {"ok": True, "project": str(self.root), "files": len(list_files(self.root))})
            elif parsed.path == "/api/files":
                json_response(self, 200, {"files": list_files(self.root)})
            elif parsed.path == "/api/file":
                path = safe_path(self.root, query.get("path", [""])[0])
                if not path.is_file():
                    raise ValueError("file does not exist")
                text = path.read_text(encoding="utf-8")
                json_response(self, 200, {"path": path.relative_to(self.root).as_posix(), "content": text[:MAX_OUTPUT]})
            else:
                json_response(self, 404, {"error": "not found"})
        except (ValueError, OSError, UnicodeDecodeError) as error:
            json_response(self, 400, {"error": str(error)})

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            body = self.read_body()
            if parsed.path == "/api/command":
                command = str(body.get("command", "")).strip()
                if not command:
                    raise ValueError("command is required")
                cwd = safe_path(self.root, str(body.get("cwd", ".")))
                if not cwd.is_dir():
                    raise ValueError("working directory does not exist")
                completed = subprocess.run(command, cwd=cwd, shell=True, capture_output=True,
                                           text=True, timeout=min(max(int(body.get("timeout", 120)), 1), 600),
                                           env=os.environ.copy())
                output = (completed.stdout + completed.stderr)[-MAX_OUTPUT:]
                json_response(self, 200, {"exitCode": completed.returncode, "output": output})
            elif parsed.path == "/api/ask":
                from colibri_workbench import collect_context, request_completion
                task = str(body.get("task", "")).strip()
                if not task:
                    raise ValueError("task is required")
                context, files = collect_context(self.root, task)
                answer = request_completion(self.server.model_url, self.server.api_key, self.server.model, [
                    {"role": "system", "content": "You are a local coding agent. Use only supplied repository evidence. Return a concise plan, files to change, and validation commands. Do not claim actions you did not perform."},
                    {"role": "user", "content": f"Project: {self.root}\n\nTask: {task}\n\nRepository context:\n{context}"},
                ])
                json_response(self, 200, {"answer": answer, "files": files, "model": self.server.model})
            else:
                json_response(self, 404, {"error": "not found"})
        except subprocess.TimeoutExpired:
            json_response(self, 408, {"error": "command timed out"})
        except (ValueError, OSError, UnicodeDecodeError, RuntimeError) as error:
            json_response(self, 400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description="Run the local Colibri visual workbench control plane.")
    parser.add_argument("--project", default=os.environ.get("COLIBRI_WORKBENCH_PROJECT", str(DEFAULT_PROJECT)))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--model-url", default=os.environ.get("COLIBRI_BASE_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--model", default=os.environ.get("COLIBRI_MODEL", "glm-5.2-colibri"))
    parser.add_argument("--api-key", default=os.environ.get("COLIBRI_API_KEY", ""))
    args = parser.parse_args()
    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"project does not exist: {root}")
    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    server.project_root = root
    server.model_url = args.model_url.rstrip("/")
    server.model = args.model
    server.api_key = args.api_key
    print(f"Colibri workbench: http://{args.host}:{args.port}/")
    print(f"Project root: {root}")
    server.serve_forever()


if __name__ == "__main__":
    main()
