import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Icon } from '../components/Icon'
import { Gauge } from '../components/Gauge'
import { SevBadge } from '../components/Badge'
import { useT, type Lang } from '../lib/i18n'
import { ANOMALY_TYPES } from '../lib/mockData'
import { apiClient } from '../lib/api'

interface AnomalyItem {
  tender_reference: string
  anomaly_score: number
  anomaly_type: string
  explanation: string
  detected_at: string
  region: string | null
}

interface AnomalyList {
  items: AnomalyItem[]
  total: number
  page: number
  page_size: number
}

interface Props { lang: Lang; go: (r: string) => void }

export function Anomalies({ lang, go }: Props) {
  const t = useT(lang)
  const ar = lang === "ar"
  const [sevFilter, setSevFilter] = useState<'all' | 'high' | 'medium'>('all')
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<string | null>(null)

  const minScore = sevFilter === 'high' ? 0.8 : sevFilter === 'medium' ? 0.5 : 0.0

  const { data, isLoading } = useQuery({
    queryKey: ['anomalies', sevFilter, page],
    queryFn: () =>
      apiClient.get<AnomalyList>('/api/v1/anomalies/', {
        params: { min_score: minScore, page, page_size: 20 },
      }).then(r => r.data),
    placeholderData: prev => prev,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const pages = Math.ceil(total / 20)

  // If no real anomaly data yet, show a hint
  const modelNotTrained = !isLoading && total === 0 && minScore === 0

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
      {/* header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 className="serif" style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em" }}>
            {ar ? "الحالات الشاذة والتنبيهات" : "Anomalies & alertes"}
          </h1>
          <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 3 }}>
            {isLoading ? t("loading") : `${total.toLocaleString('fr-FR')} ${ar ? "حالة مكتشفة" : "anomalies détectées"} · Isolation Forest`}
          </p>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {(['all', 'high', 'medium'] as const).map(s => (
            <button key={s} onClick={() => { setSevFilter(s); setPage(1) }}
              className={`btn btn-sm ${sevFilter === s ? 'btn-primary' : 'btn-ghost'}`}>
              {s === 'all' ? t("all") : s === 'high' ? t("high") : t("medium")}
            </button>
          ))}
        </div>
      </div>

      {/* model not trained hint */}
      {modelNotTrained && (
        <div className="card" style={{ padding: 32, textAlign: "center", color: "var(--muted)" }}>
          <Icon name="alert" size={36} style={{ display: "block", margin: "0 auto 12px", opacity: 0.4 }}/>
          <h3 style={{ fontWeight: 600, marginBottom: 8, color: "var(--ink)" }}>
            {ar ? "النموذج لم يتم تدريبه بعد" : "Modèle non encore entraîné"}
          </h3>
          <p style={{ fontSize: 13.5, maxWidth: 400, margin: "0 auto", lineHeight: 1.6 }}>
            {ar ? "شغّل أولاً:" : "Lancez d'abord :"}
            <br/>
            <code style={{ background: "var(--surface-sunk)", padding: "2px 8px", borderRadius: 4, fontSize: 12 }}>
              make transform &amp;&amp; make train
            </code>
          </p>
        </div>
      )}

      {/* anomaly list */}
      {!modelNotTrained && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {isLoading && Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card" style={{ padding: 20 }}>
              <div style={{ display: "grid", gridTemplateColumns: "80px 1fr", gap: 18 }}>
                <div className="skeleton" style={{ width: 80, height: 80, borderRadius: "50%" }}/>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div className="skeleton" style={{ height: 14, width: "60%" }}/>
                  <div className="skeleton" style={{ height: 12, width: "90%" }}/>
                  <div className="skeleton" style={{ height: 12, width: "40%" }}/>
                </div>
              </div>
            </div>
          ))}

          {items.map((a) => {
            const score100 = Math.round(a.anomaly_score * 100)
            const sev = score100 >= 80 ? 'high' : 'medium'
            const at = ANOMALY_TYPES.find(x => x.id === a.anomaly_type)
            const isExp = expanded === a.tender_reference

            return (
              <div key={a.tender_reference}
                onClick={() => setExpanded(isExp ? null : a.tender_reference)}
                className="card animate-fadeUp"
                style={{ padding: 20, cursor: "pointer", transition: "all 0.15s",
                  borderColor: isExp ? "var(--red)" : undefined,
                  boxShadow: isExp ? "var(--ring), var(--shadow-sm)" : undefined }}>
                <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 18, alignItems: "center" }}>
                  <Gauge value={score100} size={80}/>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
                      <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)" }}>
                        {a.tender_reference}
                      </span>
                      {at && (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12.5, fontWeight: 700 }}>
                          <span style={{ width: 8, height: 8, borderRadius: 2, background: at.color }}/>
                          {ar ? at.ar : at.fr}
                        </span>
                      )}
                      <SevBadge sev={sev} lang={lang}/>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {a.explanation}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--muted)", display: "flex", gap: 16, flexWrap: "wrap" }}>
                      {a.region && <span><Icon name="pin" size={12} style={{ verticalAlign: "middle" }}/> {a.region}</span>}
                      <span className="mono tnum">score: {a.anomaly_score.toFixed(3)}</span>
                    </div>
                  </div>
                  <Icon name={isExp ? "chevUp" : "chevD"} size={16} style={{ color: "var(--muted)" }}/>
                </div>

                {isExp && (
                  <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--line)" }}>
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 6 }}>{t("ref")}</div>
                        <div className="mono" style={{ fontSize: 13 }}>{a.tender_reference}</div>
                      </div>
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 6 }}>{t("score")}</div>
                        <div className="mono" style={{ fontSize: 13, fontWeight: 700 }}>{score100} / 100</div>
                      </div>
                      <div style={{ flex: 2, minWidth: 300 }}>
                        <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 6 }}>{t("objet")}</div>
                        <div style={{ fontSize: 13, lineHeight: 1.5 }}>{a.explanation}</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 10 }}>
                      <button onClick={e => { e.stopPropagation(); go("tenders") }}
                        className="btn btn-sm btn-ghost">
                        <Icon name="external" size={13}/>{t("viewTender")}
                      </button>
                      <button onClick={e => { e.stopPropagation(); go("ai") }}
                        className="btn btn-sm btn-ghost">
                        <Icon name="sparkle" size={13}/>{ar ? "تحليل بالذكاء الاصطناعي" : "Analyser avec IA"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* pagination */}
      {pages > 1 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13, color: "var(--muted)" }}>
          <span>{total.toLocaleString('fr-FR')} anomalies · page {page}/{pages}</span>
          <div style={{ display: "flex", gap: 6 }}>
            <button className="btn btn-sm btn-ghost" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
              <Icon name="chevL" size={14}/>
            </button>
            <button className="btn btn-sm btn-ghost" disabled={page === pages} onClick={() => setPage(p => p + 1)}>
              <Icon name="chevR" size={14}/>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
