# Colibri Workbench

A standalone local coding partner for any repository. It is independent of PBOMNI and can target PBOMNI, another project, or the current directory when you choose.

The workbench reads relevant text files, sends a bounded repository context to a local Colibri OpenAI-compatible server, prints a coding plan, and saves the complete result locally so the task can be resumed later.

## Start Colibri

From the repository root, start the local API using a model that fits your machine:

```powershell
python c/coli serve --model D:\models\your-model --host 127.0.0.1 --port 8000
```

## Ask it to help with Omni

```powershell
python workbench/colibri_workbench.py --project .\PBOMNI "Inspect the order workflow and propose the next safe implementation step"
```

The default endpoint is `http://127.0.0.1:8000/v1`. Override it with `COLIBRI_BASE_URL` or `--base-url`; set `COLIBRI_API_KEY` only when the server requires one. Override the model with `COLIBRI_MODEL` or `--model`.

Each run saves a JSON session under `workbench/sessions/` in this standalone tool. The session includes the task, model endpoint, selected files, and response. The workbench does not modify the target project.

## Visual control plane

The dashboard's **Workbench** tab provides a project file browser, read-only file
preview, local terminal, and agent planning panel. Run the control server in a
second PowerShell window, pointing it at whichever project you want Colibri to
operate on:

```powershell
python workbench\server.py --project . --port 8787
```

The launcher defaults to the standalone Colibri checkout as its first project.
Point it at another project, including Omni, with `COLIBRI_PROJECT` or the
workbench `--project` option. MCP clients can target another workbench instance
with `COLIBRI_WORKBENCH_URL`.

Start the dashboard separately:

```powershell
cd web
npm install
npm run dev
```

Open `http://127.0.0.1:5173`, then select **Workbench**. The API server is
bound to localhost and the command runner uses the selected project as its
working directory. Do not bind it to a public interface until authentication,
command approval, and an actual OS sandbox are added.

The workbench can inspect files, plan tasks, queue commands for approval, and
review/apply valid unified diffs after explicit approval. It does not silently
write to target projects.

## Skills and memory

`skills.json` is the standalone skill registry. Skills declare whether they are
read-only or require operator approval; disabled skills are placeholders for
future Graphify, browser, media, and sandbox adapters.

Durable project memory is stored outside target repositories in
`workbench/state/memory.json`. The control API exposes:

```text
GET  /api/skills
GET  /api/memory?limit=100
POST /api/memory { "kind": "decision", "content": "..." }
```

The memory file is local runtime state and should not be committed or synced as
project source.

Additional control-plane endpoints:

```text
GET  /api/providers
POST /api/decide { "task": "Fix the parser and run tests" }
GET  /api/decisions
GET  /api/graph/query?q=How%20does%20the%20workbench%20run%20commands%3F
POST /api/actions { "command": "npm test" }
POST /api/actions/{id}/approve
POST /api/patches { "patch": "diff --git ..." }
GET  /api/instances
POST /api/instances { "id": "omni", "project": "C:\\projects\\PBOMNI", "port": 8788 }
POST /api/instances/{id}/start
POST /api/instances/{id}/stop
POST /api/browser/open { "url": "https://example.com" }
POST /api/sandbox/run { "image": "python:3.12", "command": "python --version" }
POST /api/media/queue { "url": "http://127.0.0.1:8188/prompt", "payload": {} }
GET  /api/trading/account
POST /api/trading/order { "symbol": "AAPL", "side": "buy", "quantity": 1, "price": 100 }
POST /api/trading/reset
```

Terminal actions are pending until explicitly approved. Browser, Docker/VM,
Docker/VM, and ComfyUI adapters also return pending actions and never execute
until `/api/actions/{id}/approve` is called. `workbench/mcp_server.py` exposes
read-only project status, memory, and Graphify tools over MCP stdio for clients
that support MCP.

Paper trading is deterministic local simulation only: `$100,000` starting cash,
`$5,000` maximum order value, no shorting, no broker credentials, no withdrawals,
and no live orders. Use it for strategy experiments and backtests before any
separate broker integration is considered.

## Design boundary

- Colibri is the standalone local model server and dashboard.
- The workbench is a portable client and task memory layer.
- PBOMNI is only a target project when passed through `--project`.
- No PBOMNI runtime code or configuration is required.
