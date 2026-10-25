import { useState, useRef, useEffect } from 'react'
import { Icon } from '../components/Icon'
import { Badge } from '../components/Badge'
import { useT, type Lang } from '../lib/i18n'
import { queryNL } from '../lib/api'
import { SUGGESTED_Q } from '../lib/mockData'

interface Props { lang: Lang }

interface Message {
  role: 'user' | 'ai'
  text?: string
  answer?: string
  sources?: { document_id: string; title: string; excerpt: string; relevance_score: number }[]
  model?: string
  inputTokens?: number
  outputTokens?: number
  isAr?: boolean
}

export function AI({ lang }: Props) {
  const t = useT(lang)
  const ar = lang === "ar"
  const [msgs, setMsgs] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [activeSrc, setActiveSrc] = useState<Message['sources']>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [msgs, loading])

  const ask = async (text: string) => {
    if (!text.trim() || loading) return
    const isAr = /[؀-ۿ]/.test(text)
    setMsgs((m) => [...m, { role: "user", text, isAr }])
    setInput("")
    setLoading(true)

    try {
      const result = await queryNL(text, isAr ? 'ar' : 'fr')
      setMsgs((m) => [...m, {
        role: "ai",
        answer: result.answer,
        sources: result.sources,
        model: "claude-sonnet-4-6",
        inputTokens: 0,
        outputTokens: 0,
      }])
      setActiveSrc(result.sources)
    } catch {
      setMsgs((m) => [...m, { role: "ai", answer: "Erreur lors de la connexion à l'API.", sources: [] }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "var(--gap)", height: "calc(100vh - 132px)", minHeight: 520 }}>
      {/* chat */}
      <div className="card" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* header */}
        <div style={{ padding: "15px 20px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <span style={{ display: "inline-flex", width: 30, height: 30, borderRadius: 8, alignItems: "center", justifyContent: "center", background: "var(--red-wash)", color: "var(--red)" }}>
              <Icon name="sparkle" size={17}/>
            </span>
            <div>
              <div style={{ fontSize: 14.5, fontWeight: 700 }}>{t("ai")}</div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>claude-sonnet-4-6 · RAG</div>
            </div>
          </div>
          <Badge tone="green" dot>{ar ? "متصل" : "En ligne"}</Badge>
        </div>

        {/* messages */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 18 }}>
          {msgs.length === 0 && !loading && (
            <div style={{ margin: "auto", textAlign: "center", maxWidth: 380, padding: 20 }}>
              <div style={{ display: "inline-flex", width: 54, height: 54, borderRadius: 14, alignItems: "center", justifyContent: "center", background: "var(--red-wash)", color: "var(--red)", marginBottom: 16 }}>
                <Icon name="sparkle" size={26}/>
              </div>
              <h3 className="serif" style={{ fontSize: 21, fontWeight: 600, marginBottom: 8 }}>
                {ar ? "اطرح سؤالاً عن الإنفاق العمومي" : "Interrogez la dépense publique"}
              </h3>
              <p style={{ fontSize: 13.5, color: "var(--muted)", lineHeight: 1.6 }}>
                {ar ? "بالفرنسية أو العربية. كل إجابة مدعومة بمصادر قابلة للتحقق." : "En français ou en arabe. Chaque réponse est sourcée et vérifiable."}
              </p>
              {/* suggested */}
              <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 8 }}>
                {SUGGESTED_Q.map((q) => (
                  <button key={q} onClick={() => ask(q)}
                    style={{ textAlign: ar ? "right" : "left", padding: "10px 14px", borderRadius: 10, border: "1px solid var(--line-2)",
                      background: "var(--surface)", fontSize: 13, color: "var(--ink-2)", cursor: "pointer", transition: "all 0.13s", lineHeight: 1.5 }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "var(--surface-sunk)"; e.currentTarget.style.borderColor = "var(--line-strong)" }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "var(--surface)"; e.currentTarget.style.borderColor = "var(--line-2)" }}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {msgs.map((m, i) => m.role === "user" ? (
            <div key={i} className={m.isAr ? "ar-text" : ""} style={{ alignSelf: ar ? "flex-start" : "flex-end", maxWidth: "82%" }}>
              <div style={{ background: "var(--red)", color: "#fff", padding: "11px 15px",
                borderRadius: ar ? "14px 14px 14px 4px" : "14px 14px 4px 14px", fontSize: 14, lineHeight: 1.5 }}>
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className={ar ? "ar-text" : ""} style={{ alignSelf: ar ? "flex-end" : "flex-start", maxWidth: "92%", animation: "fadeUp 0.4s ease both" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 8 }}>
                <span style={{ display: "inline-flex", width: 22, height: 22, borderRadius: 6, alignItems: "center", justifyContent: "center", background: "var(--red-wash)", color: "var(--red)" }}>
                  <Icon name="sparkle" size={13}/>
                </span>
                <span style={{ fontSize: 12, fontWeight: 700 }}>CivicLens</span>
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.7, color: "var(--ink)", whiteSpace: "pre-wrap", background: "var(--surface-2)",
                padding: "14px 16px", borderRadius: "4px 14px 14px 14px", border: "1px solid var(--line)" }}>
                {m.answer}
              </div>
              {m.sources && m.sources.length > 0 && (
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {m.sources.map((s) => (
                    <span key={s.document_id} className="mono" style={{ fontSize: 11, fontWeight: 700, padding: "2px 7px",
                      borderRadius: 5, background: "var(--red-wash)", color: "var(--red-ink)", cursor: "default" }}>
                      [{s.document_id}]
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ alignSelf: "flex-start", display: "flex", alignItems: "center", gap: 9, color: "var(--muted)", fontSize: 13 }}>
              <span style={{ display: "inline-flex", width: 22, height: 22, borderRadius: 6, alignItems: "center", justifyContent: "center",
                background: "var(--red-wash)", color: "var(--red)" }}>
                <Icon name="sparkle" size={13} style={{ animation: "spin 1s linear infinite" }}/>
              </span>
              {t("analysing")}
              <span style={{ display: "inline-flex", gap: 3 }}>
                {[0,1,2].map((d) => <span key={d} style={{ width: 5, height: 5, borderRadius: 99, background: "var(--red)", animation: `blink 1.2s ${d * 0.2}s infinite` }}/>)}
              </span>
            </div>
          )}
        </div>

        {/* input */}
        <div style={{ padding: "14px 16px", borderTop: "1px solid var(--line)", display: "flex", gap: 10 }}>
          <input value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && ask(input)}
            placeholder={t("askPlaceholder")}
            style={{ flex: 1, height: 42, padding: "0 14px", border: "1px solid var(--line-2)", borderRadius: "var(--r-md)",
              background: "var(--surface)", fontSize: 14, outline: "none", color: "var(--ink)" }}/>
          <button onClick={() => ask(input)} disabled={loading || !input.trim()}
            style={{ width: 42, height: 42, display: "inline-flex", alignItems: "center", justifyContent: "center",
              background: "var(--red)", color: "#fff", border: "none", borderRadius: "var(--r-md)", cursor: "pointer",
              opacity: loading || !input.trim() ? 0.5 : 1, transition: "opacity 0.15s" }}>
            <Icon name="send" size={17}/>
          </button>
        </div>
      </div>

      {/* sources panel */}
      <div className="card" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "15px 20px", borderBottom: "1px solid var(--line)" }}>
          <h3 style={{ fontSize: 14.5, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
            <Icon name="doc" size={16} style={{ color: "var(--muted)" }}/>
            {t("sources")} {activeSrc && activeSrc.length > 0 && `(${activeSrc.length})`}
          </h3>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
          {activeSrc && activeSrc.length === 0 && (
            <div style={{ textAlign: "center", color: "var(--muted)", fontSize: 13, marginTop: 40, lineHeight: 1.6 }}>
              <Icon name="doc" size={32} style={{ display: "block", margin: "0 auto 12px", opacity: 0.3 }}/>
              {ar ? "ستظهر المصادر هنا بعد طرح سؤال" : "Les sources apparaîtront ici après votre question"}
            </div>
          )}
          {activeSrc?.map((s) => (
            <div key={s.document_id} style={{ padding: "12px 14px", borderRadius: 10, border: "1px solid var(--line)",
              background: "var(--surface-2)", animation: "fadeUp 0.3s ease both" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span className="mono" style={{ fontSize: 11, fontWeight: 700, padding: "2px 6px", borderRadius: 4,
                  background: "var(--red-wash)", color: "var(--red-ink)" }}>[{s.document_id}]</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, lineHeight: 1.4 }}>{s.title}</div>
              <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                {s.excerpt.slice(0, 200)}…
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
