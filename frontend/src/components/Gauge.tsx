import { useState, useEffect } from 'react'

interface GaugeProps { value: number; size?: number; label?: string }

export function Gauge({ value, size = 92, label }: GaugeProps) {
  const r = (size - 14) / 2
  const c = 2 * Math.PI * r
  const col = value >= 80 ? "var(--sev-high)" : value >= 60 ? "var(--sev-med)" : "var(--sev-low)"
  const [shown, setShown] = useState(0)
  useEffect(() => { const t = setTimeout(() => setShown(value), 60); return () => clearTimeout(t) }, [value])

  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--surface-sunk)" strokeWidth="8"/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={col} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (c * shown) / 100}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.2,0.8,0.2,1)" }}/>
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span className="serif tnum" style={{ fontSize: size * 0.3, fontWeight: 600, color: col, lineHeight: 1 }}>{value}</span>
        {label && <span style={{ fontSize: 9.5, color: "var(--muted)", fontWeight: 600 }}>{label}</span>}
      </div>
    </div>
  )
}
