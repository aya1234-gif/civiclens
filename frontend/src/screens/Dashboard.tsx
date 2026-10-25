import { useQuery } from '@tanstack/react-query'
import { Icon } from '../components/Icon'
import { StatCard } from '../components/StatCard'
import { Gauge } from '../components/Gauge'
import { ColumnChart, Donut } from '../components/Charts'
import { StatusBadge } from '../components/Badge'
import { useT, type Lang } from '../lib/i18n'
import { fmtInt } from '../lib/formatters'
import { ANOMALIES, ANOMALY_TYPES, MONTHLY_ACTIVITY, SPEND_BY_TYPE } from '../lib/mockData'
import { fetchTenders, apiClient } from '../lib/api'

interface Props { lang: Lang; dark: boolean; go: (r: string) => void }

export function Dashboard({ lang, go }: Props) {
  const t = useT(lang)
  const ar = lang === "ar"

  const { data: tendersData } = useQuery({
    queryKey: ['tenders-dashboard'],
    queryFn: () => fetchTenders({ page_size: 6, page: 1 }),
  })
  const { data: anomalyData } = useQuery({
    queryKey: ['anomalies-count'],
    queryFn: () => apiClient.get('/api/v1/anomalies/', { params: { min_score: 0.5, page_size: 1 } }).then(r => r.data),
  })

  const recentTenders = tendersData?.items ?? []
  const totalTenders = tendersData?.total ?? 0
  const topAnoms = ANOMALIES.slice(0, 3)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
      {/* greeting */}
      <div className="animate-fadeUp">
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          {ar ? "مرحباً" : "Vue d'ensemble"} · {new Date().toLocaleDateString(ar ? 'ar-MA' : 'fr-MA', { day: 'numeric', month: 'long', year: 'numeric' })}
        </div>
        <h1 className="serif" style={{ fontSize: 30, fontWeight: 600, letterSpacing: "-0.02em" }}>
          {ar ? "نبض الإنفاق العمومي اليوم" : "Le pouls de la dépense publique, aujourd'hui"}
        </h1>
      </div>

      {/* stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--gap)" }}>
        <StatCard icon="table"  label={t("todayTenders")}      value={fmtInt(totalTenders)}  sub={ar ? "صفقة مفهرسة" : "avis indexés"}   trend={6}  accent="neutral" delay={0}/>
        <StatCard icon="coins"  label={t("valueTracked")}      value="79.1 Md"               sub="MAD"                                    trend={3}  accent="green"   delay={60}/>
        <StatCard icon="alert"  label={t("anomaliesFlagged")}  value={anomalyData?.total != null ? fmtInt(anomalyData.total) : "—"} sub={ar ? "بحاجة لمراجعة" : "à examiner"} trend={12} accent="red"     delay={120}/>
        <StatCard icon="map"    label={t("activeRegions")}     value="12 / 12"               sub={ar ? "كل الجهات نشطة" : "toutes régions actives"} accent="neutral" delay={180}/>
      </div>

      {/* main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: "var(--gap)", alignItems: "start" }}>
        {/* recent tenders */}
        <div className="card animate-fadeUp" style={{ animationDelay: "120ms", overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", borderBottom: "1px solid var(--line)" }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
              <Icon name="pulse" size={17} style={{ color: "var(--red)" }}/>
              {ar ? "أحدث الصفقات" : "Derniers marchés publiés"}
            </h3>
            <button className="btn btn-sm btn-ghost" onClick={() => go("tenders")}>
              {ar ? "عرض الكل" : "Tout voir"}<Icon name="chevR" size={14}/>
            </button>
          </div>
          <div>
            {recentTenders.length === 0 && (
              <div style={{ padding: "32px 20px", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
                <div className="skeleton" style={{ height: 14, marginBottom: 10, borderRadius: 6 }}/>
                <div className="skeleton" style={{ height: 14, width: "70%", margin: "0 auto" }}/>
              </div>
            )}
            {recentTenders.map((row, i) => (
              <div key={row.reference} onClick={() => go("tenders")}
                style={{ display: "grid", gridTemplateColumns: "auto 1fr auto auto", gap: 14, alignItems: "center",
                  padding: "13px 20px", borderBottom: i < recentTenders.length - 1 ? "1px solid var(--line)" : "none",
                  cursor: "pointer", transition: "background 0.12s" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-2)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                <span className="mono" style={{ fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>
                  {row.reference.slice(-6)}
                </span>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {row.object ?? "—"}
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {row.contracting_authority ?? "—"}
                  </div>
                </div>
                <span className="mono tnum" style={{ fontSize: 12.5, fontWeight: 700, whiteSpace: "nowrap", color: "var(--muted)" }}>
                  {row.wilaya ?? row.region ?? "—"}
                </span>
                <StatusBadge status="open" lang={lang}/>
              </div>
            ))}
          </div>
        </div>

        {/* right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          {/* anomalies preview */}
          <div className="card animate-fadeUp" style={{ animationDelay: "180ms", padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
                <Icon name="alert" size={17} style={{ color: "var(--sev-high)" }}/>
                {ar ? "أبرز الحالات الشاذة" : "Anomalies prioritaires"}
              </h3>
              <button className="btn btn-sm btn-ghost" onClick={() => go("anomalies")}><Icon name="chevR" size={14}/></button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {topAnoms.map((a) => {
                const at = ANOMALY_TYPES.find((x) => x.id === a.type)!
                return (
                  <div key={a.id} onClick={() => go("anomalies")}
                    style={{ display: "flex", gap: 13, alignItems: "center", cursor: "pointer", padding: 8, margin: -8, borderRadius: 9 }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-2)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                    <Gauge value={a.score} size={54}/>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                        <span style={{ width: 8, height: 8, borderRadius: 2, background: at.color }}/>
                        <span style={{ fontSize: 12.5, fontWeight: 700 }}>{ar ? at.ar : at.fr}</span>
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {a.objet}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* ask AI mini */}
          <div className="card animate-fadeUp" style={{ animationDelay: "240ms", padding: 20, background: "var(--surface-2)" }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <Icon name="sparkle" size={17} style={{ color: "var(--red)" }}/>
              {ar ? "اسأل CivicLens" : "Demandez à CivicLens"}
            </h3>
            <div onClick={() => go("ai")} style={{ display: "flex", alignItems: "center", gap: 10, padding: "11px 14px", borderRadius: 10,
              border: "1px solid var(--line-2)", background: "var(--surface)", cursor: "text", color: "var(--muted)", fontSize: 13.5 }}>
              <Icon name="search" size={16}/>{ar ? "أي جهة سجّلت أكبر إنفاق؟" : "Quelle région dépense le plus ?"}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginTop: 12 }}>
              {(ar ? ["الصفقات المجزأة", "متعهد وحيد"] : ["Prix gonflés 2026", "Marchés fractionnés"]).map((q) => (
                <button key={q} onClick={() => go("ai")} className="badge"
                  style={{ background: "var(--surface)", border: "1px solid var(--line-2)", color: "var(--ink-2)", cursor: "pointer" }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* bottom charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: "var(--gap)", alignItems: "start" }}>
        <div className="card animate-fadeUp" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>{t("byMonth")}</h3>
          <p style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 8 }}>
            {ar ? "عدد الصفقات المنشورة شهرياً · 2026" : "Avis publiés par mois · 2026"}
          </p>
          <ColumnChart data={MONTHLY_ACTIVITY}/>
        </div>
        <div className="card animate-fadeUp" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>{t("byType")}</h3>
          <Donut data={SPEND_BY_TYPE} size={138}/>
        </div>
      </div>
    </div>
  )
}
