import { useEffect, useRef, useState } from "react"
import { ArrowUp, Bot, GripHorizontal, Minus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { streamChat, type ChatMessage } from "@/lib/api"
import { stored } from "@/lib/storage"
import { Markdown } from "@/components/Markdown"
import { getCurrentWindow } from "@tauri-apps/api/window"

const makeMessage = (role: ChatMessage["role"], content: string): ChatMessage => ({
  id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
  role,
  content,
})

export function Companion() {
  const baseUrl = stored(localStorage, "colibri.companionBaseUrl", "http://127.0.0.1:11434/v1")
  const model = stored(localStorage, "colibri.companionModel", "qwen2.5-coder:7b")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)
  const nativeWindow = typeof window !== "undefined" ? getCurrentWindow() : null
  const dragWindow = () => { void nativeWindow?.startDragging() }

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  const send = async () => {
    const content = draft.trim()
    if (!content || loading) return
    const user = makeMessage("user", content)
    const assistant = makeMessage("assistant", "")
    const history = [...messages, user]
    setMessages([...history, assistant])
    setDraft("")
    setError("")
    setLoading(true)
    const controller = new AbortController()
    try {
      await streamChat({
        baseUrl,
        apiKey: "",
        model,
        messages: history,
        temperature: 0.3,
        maxTokens: 512,
        enableThinking: false,
        cacheSlot: undefined,
        signal: controller.signal,
        onDelta: (delta) => setMessages((current) => current.map((item) => item.id === assistant.id ? { ...item, content: item.content + delta } : item)),
      })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
      setMessages((current) => current.filter((item) => item.id !== assistant.id || item.content))
    } finally {
      setLoading(false)
    }
  }

  return <div className="companion-shell">
    <header className="companion-titlebar" data-tauri-drag-region onPointerDown={(event) => {
      if (event.button === 0 && event.target === event.currentTarget) dragWindow()
    }}>
      <div className="companion-brand"><Bot className="size-4" /><strong>colibrì companion</strong><span>{model}</span></div>
      <div className="companion-window-actions" onPointerDown={(event) => event.stopPropagation()}><GripHorizontal className="size-4 drag-hint" /><button aria-label="Minimize" onClick={() => void nativeWindow?.minimize()}><Minus className="size-3.5" /></button><button aria-label="Close" onClick={() => void nativeWindow?.close()}><X className="size-3.5" /></button></div>
    </header>
    <main className="companion-messages">
      {!messages.length ? <div className="companion-empty"><Bot className="size-8" /><strong>Ready when you are.</strong><span>Ask about a project, a command, or the next thing to build.</span></div> : messages.map((item) => <article key={item.id} className={`companion-message ${item.role}`}><span>{item.role === "user" ? "You" : "colibrì"}</span>{item.role === "assistant" ? <Markdown source={item.content || "..."} /> : <p>{item.content}</p>}</article>)}
      <div ref={bottomRef} />
    </main>
    {error ? <div className="companion-error">{error}</div> : null}
    <form className="companion-composer" onSubmit={(event) => { event.preventDefault(); void send() }}>
      <Textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask colibrì..." disabled={loading} />
      <Button size="icon" aria-label="Send" type="submit" disabled={loading || !draft.trim()}><ArrowUp className="size-4" /></Button>
    </form>
  </div>
}
