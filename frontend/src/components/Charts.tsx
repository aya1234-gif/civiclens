import { useState } from 'react'

// ── Horizontal bar chart ──────────────────────────────────────────────────
interface BarItem { name: string; v: number; color?: string }
interface BarChartProps { data: BarItem[]; color?: string; money?: boolean }

export function HBarChart({ data, color = "var(--viz-1)", money }: BarChartProps) {
  const max = Math.max(...data.map((d) => d.v))
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
      {data.map((d, i) => (
        <div key={i} style={{ display: "grid", gridTemplateColumns: "minmax(120px, 38%) 1fr auto", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: "var(--ink-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.name}</span>
          <div style={{ height: 9, background: "var(--surface-sunk)", borderRadius: 99, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${(d.v / max) * 100}%`, background: d.color ?? color, borderRadius: 99,
              transformOrigin: "left", animation: `growBar 0.8s cubic-bezier(0.2,0.8,0.2,1) ${i * 70}ms both` }}/>
          </div>
          <span className="mono tnum" style={{ fontSize: 12.5, fontWeight: 600, minWidth: 48, textAlign: "right" }}>
            {money ? ((d.v >= 1e9 ? (d.v/1e9).toFixed(1) + " Md" : (d.v/1e6).toFixed(1) + " M")) : d.v}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Column chart ──────────────────────────────────────────────────────────
interface ColItem { m: string; v: number }
interface ColumnChartProps { data: ColItem[]; height?: number }

export function ColumnChart({ data, height = 150 }: ColumnChartProps) {
  const max = Math.max(...data.map((d) => d.v))
  const [hover, setHover] = useState<number | null>(null)
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height, paddingTop: 22 }}>
      {data.map((d, i) => (
        <div key={i} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
          style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 7, height: "100%", justifyContent: "flex-end", cursor: "default" }}>
          <div style={{ position: "relative", width: "100%", display: "flex", justifyContent: "center", alignItems: "flex-end", height: "100%" }}>
            {hover === i && (
              <span className="mono tnum" style={{ position: "absolute", top: -20, fontSize: 11, fontWeight: 700, color: "var(--ink)" }}>{d.v}</span>
            )}
            <div style={{ width: "76%", height: `${(d.v / max) * 100}%`, background: hover === i ? "var(--red)" : "var(--viz-4)",
              borderRadius: "5px 5px 2px 2px", transition: "background 0.15s",
              animation: `growBar 0.7s cubic-bezier(0.2,0.8,0.2,1) ${i * 40}ms both` }}/>
          </div>
          <span style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 600 }}>{d.m}</span>
        </div>
      ))}
    </div>
  )
}

// ── Donut ─────────────────────────────────────────────────────────────────
interface DonutItem { name: string; v: number; color: string }
interface DonutProps { data: DonutItem[]; size?: number }

export function Donut({ data, size = 150 }: DonutProps) {
  const total = data.reduce((s, d) => s + d.v, 0)
  const r = size / 2 - 12
  const c = 2 * Math.PI * r
  let off = 0
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 22, flexWrap: "wrap" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
        {data.map((d, i) => {
          const frac = d.v / total
          const seg = c * frac
          const el = (
            <circle key={i} cx={size/2} cy={size/2} r={r} fill="none" stroke={d.color} strokeWidth="22"
              strokeDasharray={`${seg} ${c - seg}`} strokeDashoffset={-off}/>
          )
          off += seg
          return el
        })}
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data.map((d, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: d.color, flexShrink: 0 }}/>
            <span style={{ fontSize: 13, color: "var(--ink-2)" }}>{d.name}</span>
            <span className="mono tnum" style={{ fontSize: 13, fontWeight: 700, marginLeft: "auto" }}>{d.v}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
