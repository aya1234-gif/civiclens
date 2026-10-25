import { useQuery } from '@tanstack/react-query'
import { Icon } from '../components/Icon'
import { useT, type Lang } from '../lib/i18n'
import { apiClient } from '../lib/api'

interface Props { lang: Lang; dark: boolean }

interface AuditRow {
  ts: string
  model_name: string
  model_version: string
  triggered_by: string
  inference_ms: number
  input_hash: string
}

interface BiasRow {
  region: string
  total: number
  flagged: number
  rate_per_1000: number
}

export function Governance({ lang }: Props) {
  const t = useT(lang)
  const ar = lang === "ar"

  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ['audit-log'],
    queryFn: () => apiClient.get<AuditRow[]>('/api/v1/governance/audit-log?limit=20').then(r => r.data),
  })

  const { data: biasData, isLoading: biasLoading } = useQuery({
    queryKey: ['bias-audit'],
    queryFn: () => apiClient.get<BiasRow[]>('/api/v1/governance/bias-audit').then(r => r.data),
  })

  const maxRate = Math.max(...(biasData?.map(b => b.rate_per_1000) ?? [1]))

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
      <div>
        <h1 className="serif" style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em" }}>
          {ar ? "الحوكمة والتدقيق" : "Gouvernance & audit"}
        </h1>
        <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 3 }}>
          {ar ? "الشفافية الكاملة لمسار البيانات والنماذج" : "Transparence totale sur la chaîne de données et les modèles IA"}
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "var(--gap)", alignItems: "start" }}>
        {/* audit log */}
        <div className="card" style={{ overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 9 }}>
            <Icon name="shield" size={17} style={{ color: "var(--muted)" }}/>
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t("auditLog")}</h3>
            {auditData && (
              <span className="badge" style={{ background: "var(--green-wash)", color: "var(--green-ink)", marginLeft: "auto" }}>
                {auditData.length} entrées
              </span>
            )}
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{ background: "var(--surface-sunk)" }}>
                  {["Horodatage", "Modèle", "Déclencheur", "ms"].map(h => (
                    <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 10.5,
                      fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
                      color: "var(--muted)", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {auditLoading && Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--line)" }}>
                    {[140, 120, 100, 50].map((w, j) => (
                      <td key={j} style={{ padding: "10px 14px" }}>
                        <div className="skeleton" style={{ height: 11, width: w, borderRadius: 4 }}/>
                      </td>
                    ))}
                  </tr>
                ))}
                {auditData?.map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--line)" }}>
                    <td className="mono" style={{ padding: "10px 14px", color: "var(--muted)", whiteSpace: "nowrap", fontSize: 11.5 }}>
                      {row.ts.replace("T", " ").slice(0, 19)}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span className="mono" style={{ fontSize: 11, padding: "2px 7px", borderRadius: 4,
                        background: "var(--surface-sunk)", color: "var(--ink-2)" }}>
                        {row.model_name} v{row.model_version}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--ink-2)", fontSize: 12.5 }}>
                      {row.triggered_by}
                    </td>
                    <td className="mono tnum" style={{ padding: "10px 14px", fontWeight: 700, textAlign: "right" }}>
                      {row.inference_ms}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* bias audit */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 6 }}>
            <Icon name="scale" size={17} style={{ color: "var(--muted)" }}/>
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t("biasAudit")}</h3>
          </div>
          <p style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 16, lineHeight: 1.5 }}>
            {ar ? "معدل الإبلاغ لكل 1000 صفقة" : "Taux de signalement pour 1 000 marchés"}
          </p>
          {biasLoading && Array.from({ length: 8 }).map((_, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "130px 1fr 44px", gap: 10, marginBottom: 9, alignItems: "center" }}>
              <div className="skeleton" style={{ height: 11, borderRadius: 4 }}/>
              <div className="skeleton" style={{ height: 8, borderRadius: 99 }}/>
              <div className="skeleton" style={{ height: 11, width: 36, borderRadius: 4 }}/>
            </div>
          ))}
          <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
            {biasData?.map((b) => (
              <div key={b.region} style={{ display: "grid", gridTemplateColumns: "130px 1fr 44px", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 11.5, color: "var(--ink-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {b.region}
                </span>
                <div style={{ height: 8, background: "var(--surface-sunk)", borderRadius: 99, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(b.rate_per_1000 / maxRate) * 100}%`,
                    background: b.rate_per_1000 > 150 ? "var(--sev-high)" : b.rate_per_1000 > 80 ? "var(--sev-med)" : "var(--sev-low)",
                    borderRadius: 99, transformOrigin: "left", animation: "growBar 0.8s cubic-bezier(0.2,0.8,0.2,1) both" }}/>
                </div>
                <span className="mono tnum" style={{ fontSize: 11.5, fontWeight: 700, textAlign: "right" }}>
                  {b.rate_per_1000}‰
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* lineage */}
      <div className="card" style={{ padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 20 }}>
          <Icon name="layers" size={17} style={{ color: "var(--muted)" }}/>
          <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t("lineage")}</h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 0, overflowX: "auto", paddingBottom: 8 }}>
          {[
            { icon: "globe",    label: "Sources",       sub: "marchespublics · data.gov.ma · HCP",     color: "var(--viz-6)" },
            { icon: "download", label: "Ingestion",     sub: "bulk_ingest.py · loader.py · Airflow",   color: "var(--viz-3)" },
            { icon: "table",    label: "Warehouse",     sub: "raw.tenders → stg_tenders · dbt",        color: "var(--viz-4)" },
            { icon: "sparkle",  label: "ML / Anomalie", sub: "IForest · SHAP · audit_log",             color: "var(--viz-2)" },
            { icon: "search",   label: "RAG · NLQ",     sub: "claude-sonnet-4-6 · FastAPI",            color: "var(--viz-1)" },
          ].map((step, i) => (
            <div key={step.label} style={{ display: "flex", alignItems: "center", gap: 0 }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, minWidth: 155, padding: "0 8px" }}>
                <span style={{ display: "inline-flex", width: 44, height: 44, borderRadius: 12, alignItems: "center", justifyContent: "center",
                  background: `color-mix(in srgb, ${step.color} 15%, var(--surface-sunk))`, color: step.color }}>
                  <Icon name={step.icon} size={22}/>
                </span>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 13.5, fontWeight: 700 }}>{step.label}</div>
                  <div style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.5, marginTop: 3 }}>{step.sub}</div>
                </div>
              </div>
              {i < 4 && <Icon name="chevR" size={18} style={{ color: "var(--line-strong)", flexShrink: 0 }}/>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
