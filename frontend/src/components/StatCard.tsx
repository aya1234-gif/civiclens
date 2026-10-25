import { Icon } from './Icon'

interface StatCardProps {
  icon: string
  label: string
  value: string | number
  sub?: string
  trend?: number
  accent?: 'neutral' | 'red' | 'green'
  delay?: number
}

function Trend({ v }: { v: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 2, fontSize: 12.5, fontWeight: 700,
      color: v >= 0 ? "var(--green-ink)" : "var(--red)" }}>
      <Icon name={v >= 0 ? "arrowUp" : "arrowDn"} size={13} stroke={2.2}/>{Math.abs(v)}%
    </span>
  )
}

export function StatCard({ icon, label, value, sub, trend, accent = 'neutral', delay = 0 }: StatCardProps) {
  return (
    <div className="card animate-fadeUp" style={{ padding: "18px 20px", animationDelay: `${delay}ms` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
        <span style={{ display: "inline-flex", width: 34, height: 34, borderRadius: 9, alignItems: "center", justifyContent: "center",
          background: accent === "red" ? "var(--red-wash)" : accent === "green" ? "var(--green-wash)" : "var(--surface-sunk)",
          color: accent === "red" ? "var(--red)" : accent === "green" ? "var(--green-ink)" : "var(--ink-2)" }}>
          <Icon name={icon} size={18}/>
        </span>
        <span className="eyebrow" style={{ fontSize: 10.5 }}>{label}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <span className="serif tnum" style={{ fontSize: 30, fontWeight: 600, lineHeight: 1, letterSpacing: "-0.02em" }}>{value}</span>
        {trend != null && <Trend v={trend}/>}
      </div>
      {sub && <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 7 }}>{sub}</div>}
    </div>
  )
}
