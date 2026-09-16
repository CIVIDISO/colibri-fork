import { useEffect, useState } from "react"
import { Bot, ChevronRight, FolderTree, Play, RefreshCw, TerminalSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

const WORKBENCH_URL = import.meta.env.VITE_WORKBENCH_URL || "http://127.0.0.1:8787"

type FileResponse = { path: string; content: string }
type CommandResponse = { exitCode: number; output: string }
type PendingAction = { id: string; command?: string; kind?: string; status: string }

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${WORKBENCH_URL}${path}`)
  const body = await response.json()
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`)
  return body as T
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${WORKBENCH_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const result = await response.json()
  if (!response.ok) throw new Error(result.error || `${response.status} ${response.statusText}`)
  return result as T
}

export function Workbench() {
  const [files, setFiles] = useState<string[]>([])
  const [selected, setSelected] = useState("")
  const [content, setContent] = useState("")
  const [task, setTask] = useState("")
  const [command, setCommand] = useState("")
  const [output, setOutput] = useState("")
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null)
  const [answer, setAnswer] = useState("")
  const [patch, setPatch] = useState("")
  const [pendingPatch, setPendingPatch] = useState<PendingAction | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  const refreshFiles = async () => {
    setError("")
    try { setFiles((await getJson<{ files: string[] }>("/api/files")).files) }
    catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)) }
  }

  useEffect(() => { void refreshFiles() }, [])

  const openFile = async (path: string) => {
    setSelected(path)
    try { setContent((await getJson<FileResponse>(`/api/file?path=${encodeURIComponent(path)}`)).content) }
    catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)) }
  }

  const runCommand = async () => {
    if (!command.trim()) return
    setBusy(true); setError("")
    try {
      const result = await postJson<{ action: PendingAction }>("/api/actions", { command })
      setPendingAction(result.action)
      setOutput("Approval required before this command runs.")
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)) }
    finally { setBusy(false) }
  }

  const approveCommand = async () => {
    if (!pendingAction) return
    setBusy(true); setError("")
    try {
      const result = await postJson<{ action: CommandResponse & { status: string } }>(`/api/actions/${pendingAction.id}/approve`, {})
      setOutput(`exit ${result.action.exitCode}\n${result.action.output}`)
      setPendingAction(null)
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)) }
    finally { setBusy(false) }
  }

  const queuePatch = async () => {
    if (!patch.trim()) return
    setBusy(true); setError("")
    try {
      const result = await postJson<{ action: PendingAction }>("/api/patches", { patch })
      setPendingPatch(result.action)
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)) }
    finally { setBusy(false) }
  }

  const approvePatch = async () => {
    if (!pendingPatch) return
    setBusy(true); setError("")
    try {
      const result = await postJson<{ action: CommandResponse & { status: string } }>(`/api/actions/${pendingPatch.id}/approve`, {})
      setOutput(`patch ${result.action.status}\n${result.action.output}`)
      setPendingPatch(null)
      await refreshFiles()
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)) }
    finally { setBusy(false) }
  }

  const askAgent = async () => {
    if (!task.trim()) return
    setBusy(true); setError("")
    try { setAnswer((await postJson<{ answer: string }>("/api/ask", { task })).answer) }
    catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)) }
    finally { setBusy(false) }
  }

  return <section className="workbench-view">
    <header className="workbench-header">
      <div><span className="eyebrow">LOCAL CONTROL PLANE</span><h2>Project workbench</h2><p>Operate a selected project with your own model, terminal, and visual context.</p></div>
      <Button variant="secondary" onClick={() => void refreshFiles()} disabled={busy}><RefreshCw className="size-4" /> Refresh project</Button>
    </header>
    <div className="workbench-grid">
      <section className="workbench-panel file-panel">
        <div className="panel-title"><FolderTree className="size-4" /> Project files <span>{files.length}</span></div>
        <div className="file-list">{files.map((file) => <button key={file} className={cn("file-row", selected === file && "selected")} onClick={() => void openFile(file)}><ChevronRight className="size-3" />{file}</button>)}</div>
      </section>
      <section className="workbench-panel editor-panel">
        <div className="panel-title"><span>{selected || "Select a file"}</span></div>
        <pre className="file-preview">{content || "Read-only project preview will appear here."}</pre>
      </section>
      <section className="workbench-panel agent-panel">
        <div className="panel-title"><Bot className="size-4" /> Ask the local agent</div>
        <Textarea value={task} onChange={(event) => setTask(event.target.value)} placeholder="Inspect Omni's order workflow and identify the next safe change..." />
        <Button onClick={() => void askAgent()} disabled={busy || !task.trim()}><Bot className="size-4" /> {busy ? "Working..." : "Plan task"}</Button>
        {answer ? <pre className="agent-answer">{answer}</pre> : <p className="panel-hint">Plans are read-only until you queue an explicit patch for approval.</p>}
        <Textarea value={patch} onChange={(event) => setPatch(event.target.value)} placeholder="Paste a unified diff to review and apply..." />
        <Button variant="secondary" onClick={() => void queuePatch()} disabled={busy || !patch.trim()}>Review patch</Button>
        {pendingPatch ? <Button className="approve-command" onClick={() => void approvePatch()} disabled={busy}><Play className="size-4" /> Approve and apply patch</Button> : null}
      </section>
      <section className="workbench-panel terminal-panel">
        <div className="panel-title"><TerminalSquare className="size-4" /> Local terminal</div>
        <div className="command-row"><Input value={command} onChange={(event) => setCommand(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runCommand() }} placeholder="npm test" /><Button size="icon" aria-label="Queue command" onClick={() => void runCommand()} disabled={busy || !command.trim()}><Play className="size-4" /></Button></div>
        {pendingAction ? <Button className="approve-command" onClick={() => void approveCommand()} disabled={busy}><Play className="size-4" /> Approve and run</Button> : null}
        <pre className="terminal-output">{output || "Command output will appear here."}</pre>
      </section>
    </div>
    {error ? <div className="error-banner" role="alert">{error}</div> : null}
  </section>
}
