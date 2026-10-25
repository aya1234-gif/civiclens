import type { Lang } from '../lib/i18n'
import { STATUSES } from '../lib/mockData'

type Tone = 'neutral' | 'red' | 'green' | 'amber'

interface BadgeProps { tone?: Tone; dot?: boolean; children: React.ReactNode }

const TONES: Record<Tone, { bg: string; fg: string }> = {
  neutral: { bg: "var(--surface-sunk)", fg: "var(--ink-2)" },
  red:     { bg: "var(--red-wash)",     fg: "var(--red-ink)" },
  green:   { bg: "var(--green-wash)",   fg: "var(--green-ink)" },
  amber:   { bg: "var(--sev-med-bg)",   fg: "var(--sev-med)" },
}

export function Badge({ tone = 'neutral', dot, children }: BadgeProps) {
  const t = TONES[tone]
  return (
    <span className="badge" style={{ background: t.bg, color: t.fg }}>
      {dot && <span style={{ width: 6, height: 6, borderRadius: 99, background: "currentColor" }}/>}
      {children}
    </span>
  )
}

export function StatusBadge({ status, lang }: { status: string; lang: Lang }) {
  const s = STATUSES.find((x) => x.id === status) ?? STATUSES[0]
  return (
    <Badge tone={s.tone as Tone} dot={status === "open" || status === "flagged"}>
      {lang === "ar" ? s.ar : s.fr}
    </Badge>
  )
}

export function SevBadge({ sev, lang }: { sev: string; lang: Lang }) {
  return (
    <span className="badge" style={{
      background: sev === "high" ? "var(--sev-high-bg)" : "var(--sev-med-bg)",
      color:      sev === "high" ? "var(--sev-high)"    : "var(--sev-med)",
    }}>
      {sev === "high"
        ? (lang === "ar" ? "خطورة عالية"   : "Sévérité élevée")
        : (lang === "ar" ? "خطورة متوسطة" : "Sévérité moyenne")}
    </span>
  )
}
