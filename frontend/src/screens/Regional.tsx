import { useState } from 'react'
import { Icon } from '../components/Icon'
import { HBarChart, ColumnChart } from '../components/Charts'
import { MoroccoMap } from '../components/MoroccoMap'
import { useT, type Lang } from '../lib/i18n'
import { fmtMAD, fmtInt } from '../lib/formatters'
import { REGIONS, SPEND_BY_MINISTRY, MONTHLY_ACTIVITY } from '../lib/mockData'

interface Props { lang: Lang; dark: boolean }

type Metric = 'tenders' | 'valueMAD' | 'anomalies'

export function Regional({ lang, dark }: Props) {
  const t = useT(lang)
  const ar = lang === "ar"
  const [metric, setMetric] = useState<Metric>('tenders')
  const [selected, setSelected] = useState<string | null>(null)

  const region = selected ? REGIONS.find((r) => r.id === selected) : null

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
      <div>
        <h1 className="serif" style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em" }}>
          {ar ? "التحليل الجهوي" : "Analytique régionale"}
        </h1>
        <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 3 }}>
          {ar ? "استكشف الإنفاق العمومي عبر 12 جهة مغربية" : "Explorez la dépense publique à travers les 12 régions marocaines"}
        </p>
      </div>

      {/* metric toggle */}
      <div style={{ display: "flex", gap: 6 }}>
        {([['tenders', t("byTenderCount")], ['valueMAD', t("byValue")], ['anomalies', t("anomaliesFlagged")]] as [Metric, string][]).map(([m, label]) => (
          <button key={m} onClick={() => setMetric(m)}
            className={`btn btn-sm ${metric === m ? 'btn-primary' : 'btn-ghost'}`}>
            {label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: "var(--gap)", alignItems: "start" }}>
        {/* map */}
        <div className="card" style={{ padding: 24 }}>
          <div className="eyebrow" style={{ marginBottom: 16 }}>
            {ar ? "انقر على جهة للتفاصيل" : "Cliquez une région pour explorer"}
          </div>
          <MoroccoMap metric={metric} onSelect={setSelected} lang={lang} dark={dark}/>
          {selected && (
            <button onClick={() => setSelected(null)} className="btn btn-sm btn-ghost" style={{ marginTop: 14 }}>
              <Icon name="chevL" size={14}/>{t("back")}
            </button>
          )}
        </div>

        {/* detail panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
          {region ? (
            <>
              <div className="card animate-fadeUp" style={{ padding: 20 }}>
                <h2 className="serif" style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>{ar ? region.ar : region.fr}</h2>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginTop: 16 }}>
                  {[
                    { l: t("tendersIndexed"),   v: fmtInt(region.tenders),                          icon: "table",  a: "neutral" },
                    { l: t("valueTracked"),       v: fmtMAD(region.valueMAD, { compact: true }),   icon: "coins",  a: "green" },
                    { l: t("anomaliesFlagged"),   v: fmtInt(region.anomalies),                     icon: "alert",  a: "red" },
                  ].map((s) => (
                    <div key={s.l} style={{ padding: "14px 16px", borderRadius: 10, background: "var(--surface-sunk)", display: "flex", flexDirection: "column", gap: 8 }}>
                      <span style={{ display: "inline-flex", width: 28, height: 28, borderRadius: 7, alignItems: "center", justifyContent: "center",
                        background: s.a === "red" ? "var(--red-wash)" : s.a === "green" ? "var(--green-wash)" : "var(--surface)",
                        color: s.a === "red" ? "var(--red)" : s.a === "green" ? "var(--green-ink)" : "var(--ink-2)" }}>
                        <Icon name={s.icon} size={15}/>
                      </span>
                      <span className="serif tnum" style={{ fontSize: 24, fontWeight: 600 }}>{s.v}</span>
                      <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>{s.l}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card animate-fadeUp" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14.5, fontWeight: 700, marginBottom: 14 }}>
                  {ar ? "الأقاليم" : "Provinces"} ({region.prov.length})
                </h3>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
                  {region.prov.map((p) => (
                    <span key={p} style={{ padding: "5px 10px", borderRadius: 6, background: "var(--surface-sunk)", fontSize: 12.5, color: "var(--ink-2)" }}>{p}</span>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="card animate-fadeUp" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>{t("byMinistry")}</h3>
                <HBarChart data={SPEND_BY_MINISTRY.map((d) => ({ ...d, v: d.v * 1e9 }))} money/>
              </div>
              <div className="card animate-fadeUp" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>{t("byMonth")}</h3>
                <p style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 12 }}>2026</p>
                <ColumnChart data={MONTHLY_ACTIVITY}/>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
