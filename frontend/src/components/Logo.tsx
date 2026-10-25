import logoIcon from '../assets/logo-icon.png'

interface LogoProps { size?: number; light?: boolean }

export function Logo({ size = 26, light }: LogoProps) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
      <img src={logoIcon} alt="CivicLens" width={size} height={size} style={{ display: "block", objectFit: "contain" }}/>
      <span className="serif" style={{ fontSize: size * 0.74, fontWeight: 600, letterSpacing: "-0.01em", color: light ? "#fff" : "var(--ink)" }}>
        Civic<span style={{ color: light ? "#fff" : "var(--red)" }}>Lens</span>
      </span>
    </div>
  )
}
