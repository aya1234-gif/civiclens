// Stylised cartogram of Morocco's 12 regions
import type { Lang } from '../lib/i18n'
import { REGIONS } from '../lib/mockData'
import { fmtMAD, fmtInt } from '../lib/formatters'
import { useState } from 'react'

const LAYOUT: Record<string, { c: number; r: number }> = {
  tta: { c: 2, r: 0 }, ori: { c: 3, r: 0 },
  rsk: { c: 1, r: 1 }, fme: { c: 2, r: 1 },
  cst: { c: 1, r: 2 }, bmk: { c: 2, r: 2 }, dta: { c: 3, r: 2 },
  msa: { c: 1, r: 3 }, sma: { c: 0, r: 3 },
  gon: { c: 0, r: 4 }, lsh: { c: 0, r: 5 }, doe: { c: 0, r: 6 },
}

interface Props {
  metric?: 'tenders' | 'valueMAD' | 'anomalies'
  compact?: boolean
  onSelect?: (id: string) => void
  lang?: Lang
  dark?: boolean
}

export function MoroccoMap({ metric = 'tenders', compact, onSelect, lang = 'fr' }: Props) {
  const [hovered, setHovered] = useState<string | null>(null)
  const values = REGIONS.map((r) => (r as Record<string, unknown>)[metric] as number)
  const max = Math.max(...values)
  const cell = compact ? 44 : 56
  const gap = 3

  return (
    <div style={{ position: "relative", width: (5 * cell) + (4 * gap), margin: "0 auto" }}>
      {REGIONS.map((reg) => {
        const pos = LAYOUT[reg.id]
        if (!pos) return null
        const val = (reg as Record<string, unknown>)[metric] as number
        const intensity = val / max
        const x = pos.c * (cell + gap)
        const y = pos.r * (cell + gap)
        const isHov = hovered === reg.id
        return (
          <div key={reg.id}
            onMouseEnter={() => setHovered(reg.id)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => onSelect?.(reg.id)}
            title={lang === 'ar' ? reg.ar : reg.fr}
            style={{
              position: "absolute", left: x, top: y,
              width: cell, height: cell, borderRadius: 8,
              background: `color-mix(in srgb, var(--red) ${Math.round(intensity * 80 + 10)}%, var(--surface-sunk))`,
              border: isHov ? "2px solid var(--red)" : "1px solid var(--line)",
              cursor: onSelect ? "pointer" : "default",
              transition: "all 0.15s",
              transform: isHov ? "scale(1.05)" : "none",
              zIndex: isHov ? 2 : 1,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
            <span style={{ fontSize: compact ? 8 : 9.5, fontWeight: 700, color: intensity > 0.5 ? "#fff" : "var(--ink-2)",
              textAlign: "center", lineHeight: 1.2, padding: 2 }}>
              {reg.fr.split("-")[0].trim()}
            </span>
            {isHov && !compact && (
              <div style={{ position: "absolute", bottom: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)",
                background: "var(--ink)", color: "#fff", borderRadius: 7, padding: "6px 10px", fontSize: 11,
                fontWeight: 600, whiteSpace: "nowrap", zIndex: 10, pointerEvents: "none",
                boxShadow: "var(--shadow-md)" }}>
                {lang === 'ar' ? reg.ar : reg.fr}<br/>
                <span className="mono" style={{ fontWeight: 400, color: "rgba(255,255,255,0.75)" }}>
                  {metric === 'valueMAD' ? fmtMAD(val, { compact: true }) + " MAD"
                   : metric === 'anomalies' ? fmtInt(val) + " anomalies"
                   : fmtInt(val) + " marchés"}
                </span>
              </div>
            )}
          </div>
        )
      })}
      {/* invisible spacer to size the container */}
      <div style={{ height: 7 * (cell + gap) - gap, width: 4 * (cell + gap) + cell }} aria-hidden="true"/>
    </div>
  )
}
