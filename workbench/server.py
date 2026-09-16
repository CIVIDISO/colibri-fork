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
import uuid
import webbrowser
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from memory_store import MemoryStore

WORKBENCH_DIR = Path(__file__).resolve().parent
SKILLS_PATH = WORKBENCH_DIR / "skills.json"
PROVIDERS_PATH = WORKBENCH_DIR / "providers.json"
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


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def command_argv(command):
    if os.name == "nt":
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command]
    return ["/bin/sh", "-lc", command]


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
            elif parsed.path == "/api/skills":
                json_response(self, 200, {"skills": load_json(SKILLS_PATH, [])})
            elif parsed.path == "/api/providers":
                json_response(self, 200, {"providers": load_json(PROVIDERS_PATH, [])})
            elif parsed.path == "/api/instances":
                json_response(self, 200, {"instances": self.server.instances})
            elif parsed.path == "/api/graph/query":
                question = query.get("q", [""])[0].strip()
                if not question:
                    raise ValueError("q is required")
                completed = subprocess.run(["graphify", "query", question, "--budget", "1200"],
                                           cwd=self.server.graph_root, capture_output=True, text=True, timeout=180)
                json_response(self, 200, {"exitCode": completed.returncode, "answer": completed.stdout[-MAX_OUTPUT:], "error": completed.stderr[-4000:]})
            elif parsed.path == "/api/memory":
                limit = int(query.get("limit", [100])[0])
                json_response(self, 200, {"memory": self.server.memory.list(str(self.root), limit)})
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
                completed = subprocess.run(command_argv(command), cwd=cwd, capture_output=True,
                                           text=True, timeout=min(max(int(body.get("timeout", 120)), 1), 600),
                                           env=os.environ.copy())
                output = (completed.stdout + completed.stderr)[-MAX_OUTPUT:]
                json_response(self, 200, {"exitCode": completed.returncode, "output": output})
            elif parsed.path == "/api/actions":
                command = str(body.get("command", "")).strip()
                if not command:
                    raise ValueError("command is required")
                action = {"id": "act_" + uuid.uuid4().hex, "kind": "terminal", "command": command,
                          "cwd": str(body.get("cwd", ".")), "status": "pending", "project": str(self.root)}
                self.server.actions[action["id"]] = action
                json_response(self, 202, {"action": action})
            elif parsed.path.startswith("/api/actions/") and parsed.path.endswith("/approve"):
                action_id = parsed.path.split("/")[3]
                action = self.server.actions.get(action_id)
                if not action:
                    raise ValueError("action does not exist")
                if action["status"] != "pending":
                    raise ValueError("action is not pending")
                cwd = safe_path(self.root, action["cwd"])
                if action["kind"] == "browser":
                    action["status"] = "completed" if webbrowser.open(action["url"]) else "failed"
                    action["output"] = action["url"]
                    action["exitCode"] = 0 if action["status"] == "completed" else 1
                elif action["kind"] == "sandbox":
                    completed = subprocess.run(command_argv(action["command"]), cwd=cwd, capture_output=True,
                                               text=True, timeout=600, env=os.environ.copy())
                    action.update({"status": "completed", "exitCode": completed.returncode,
                                   "output": (completed.stdout + completed.stderr)[-MAX_OUTPUT:]})
                elif action["kind"] == "media":
                    request = urllib.request.Request(action["url"], data=json.dumps(action["payload"]).encode(),
                                                     headers={"Content-Type": "application/json"}, method="POST")
                    with urllib.request.urlopen(request, timeout=60) as result:
                        action.update({"status": "completed", "exitCode": 0,
                                       "output": result.read().decode("utf-8", errors="replace")[-MAX_OUTPUT:]})
                else:
                    completed = subprocess.run(command_argv(action["command"]), cwd=cwd, capture_output=True,
                                               text=True, timeout=120, env=os.environ.copy())
                    action.update({"status": "completed", "exitCode": completed.returncode,
                                   "output": (completed.stdout + completed.stderr)[-MAX_OUTPUT:]})
                json_response(self, 200, {"action": action})
            elif parsed.path == "/api/browser/open":
                url = str(body.get("url", "")).strip()
                if not url.startswith(("http://", "https://")):
                    raise ValueError("browser URL must use http or https")
                action = {"id": "act_" + uuid.uuid4().hex, "kind": "browser", "url": url,
                          "status": "pending", "project": str(self.root)}
                self.server.actions[action["id"]] = action
                json_response(self, 202, {"action": action})
            elif parsed.path == "/api/sandbox/run":
                image = str(body.get("image", "")).strip()
                command = str(body.get("command", "")).strip()
                if not image or not command:
                    raise ValueError("image and command are required")
                action = {"id": "act_" + uuid.uuid4().hex, "kind": "sandbox",
                          "command": f"docker run --rm -v \"{self.root}:\\workspace\" -w /workspace {image} {command}",
                          "cwd": ".", "status": "pending", "project": str(self.root)}
                self.server.actions[action["id"]] = action
                json_response(self, 202, {"action": action})
            elif parsed.path == "/api/media/queue":
                url = str(body.get("url", "http://127.0.0.1:8188/prompt")).strip()
                payload = body.get("payload")
                if not isinstance(payload, dict) or not url.startswith(("http://", "https://")):
                    raise ValueError("media url and object payload are required")
                action = {"id": "act_" + uuid.uuid4().hex, "kind": "media", "url": url,
                          "payload": payload, "status": "pending", "project": str(self.root)}
                self.server.actions[action["id"]] = action
                json_response(self, 202, {"action": action})
            elif parsed.path == "/api/instances":
                instance = {"id": str(body.get("id") or "instance-" + uuid.uuid4().hex[:8]),
                            "project": str(Path(body.get("project", self.root)).expanduser().resolve()),
                            "modelUrl": str(body.get("modelUrl", self.server.model_url)),
                            "model": str(body.get("model", self.server.model)),
                            "port": int(body.get("port", 8787)), "status": "configured"}
                self.server.instances[instance["id"]] = instance
                json_response(self, 201, {"instance": instance})
            elif parsed.path.startswith("/api/instances/") and parsed.path.endswith("/start"):
                instance_id = parsed.path.split("/")[3]
                instance = self.server.instances.get(instance_id)
                if not instance:
                    raise ValueError("instance does not exist")
                if instance.get("processId"):
                    raise ValueError("instance is already running")
                process = subprocess.Popen([sys.executable, str(WORKBENCH_DIR / "server.py"),
                                            "--project", instance["project"], "--port", str(instance["port"]),
                                            "--model-url", instance["modelUrl"], "--model", instance["model"]])
                instance.update({"processId": process.pid, "status": "running"})
                json_response(self, 200, {"instance": instance})
            elif parsed.path.startswith("/api/instances/") and parsed.path.endswith("/stop"):
                instance_id = parsed.path.split("/")[3]
                instance = self.server.instances.get(instance_id)
                if not instance:
                    raise ValueError("instance does not exist")
                if instance.get("processId"):
                    subprocess.run(["taskkill", "/PID", str(instance["processId"]), "/T", "/F"], capture_output=True)
                instance.update({"processId": None, "status": "stopped"})
                json_response(self, 200, {"instance": instance})
            elif parsed.path == "/api/memory":
                row = self.server.memory.add(
                    str(self.root), body.get("kind", "note"), body.get("content", ""), body.get("source", "operator")
                )
                json_response(self, 201, {"memory": row})
            elif parsed.path == "/api/ask":
                from colibri_workbench import collect_context, request_completion
                task = str(body.get("task", "")).strip()
                if not task:
                    raise ValueError("task is required")
                context, files = collect_context(self.root, task)
                memories = self.server.memory.list(str(self.root), 20)
                answer = request_completion(self.server.model_url, self.server.api_key, self.server.model, [
                    {"role": "system", "content": "You are a local coding agent. Use only supplied repository evidence and durable project memory. Return a concise plan, files to change, and validation commands. Do not claim actions you did not perform."},
                    {"role": "user", "content": f"Project: {self.root}\n\nTask: {task}\n\nDurable memory:\n{json.dumps(memories, ensure_ascii=False)}\n\nRepository context:\n{context}"},
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
    server.memory = MemoryStore(WORKBENCH_DIR / "state")
    server.graph_root = WORKBENCH_DIR.parent
    server.actions = {}
    server.instances = {}
    print(f"Colibri workbench: http://{args.host}:{args.port}/")
    print(f"Project root: {root}")
    server.serve_forever()


if __name__ == "__main__":
    main()
