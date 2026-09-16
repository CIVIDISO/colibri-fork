import { BrainCircuit, CheckCircle2, Gauge, MessageSquareText, ShieldCheck, TerminalSquare, Users } from "lucide-react"

const sections = [
  { icon: MessageSquareText, title: "Chat", body: "Talk directly to the active model for questions, explanations, drafts, and short coding discussions." },
  { icon: BrainCircuit, title: "Brain", body: "Watch expert routing activity. Bright cells show model experts that are hot or recently used." },
  { icon: Gauge, title: "Profiling", body: "See where generation time goes: disk reads, expert math, attention, and output head work." },
  { icon: TerminalSquare, title: "Workbench", body: "Choose a project, inspect files, ask the coding agent, and run commands. Commands and patches wait for approval." },
  { icon: Users, title: "Agent swarm", body: "Give agents separate roles such as investigator, tester, reviewer, or documentation writer. They run in parallel." },
  { icon: ShieldCheck, title: "Approval", body: "Review a command or unified diff first, then choose Approve and run or Approve and apply." },
]

export function Guide() {
  return <section className="guide-view">
    <header className="guide-header"><span className="eyebrow">COLIBRI FIELD GUIDE</span><h2>What you are looking at</h2><p>Colibri is a local control surface for model chat, project work, telemetry, and approved actions.</p></header>
    <div className="guide-grid">{sections.map(({ icon: Icon, title, body }) => <article className="guide-card" key={title}><Icon className="size-5" /><h3>{title}</h3><p>{body}</p></article>)}</div>
    <div className="guide-note"><CheckCircle2 className="size-4" /><span><strong>Why it may feel slow:</strong> the Qwen3.6 deep model is CPU-bound. The floating companion uses the faster GPU-backed Ollama coding model.</span></div>
  </section>
}
