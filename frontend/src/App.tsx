import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Icon } from './components/Icon'
import { Logo } from './components/Logo'
import { Landing } from './screens/Landing'
import { Dashboard } from './screens/Dashboard'
import { Tenders } from './screens/Tenders'
import { AI } from './screens/AI'
import { Anomalies } from './screens/Anomalies'
import { Regional } from './screens/Regional'
import { Governance } from './screens/Governance'
import { SOURCES, TOTAL_ANOMALIES } from './lib/mockData'
import { useT, type Lang } from './lib/i18n'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, retry: 1 } },
})

type Route = 'landing' | 'dashboard' | 'tenders' | 'ai' | 'anomalies' | 'regional' | 'governance'
type Density = 'compact' | 'regular' | 'comfy'
// eslint-disable-next-line @typescript-eslint/no-unused-vars








const NAV: { id: Route; icon: string; badge?: number }[] = [
  { id: "dashboard",  icon: "dashboard" },
  { id: "tenders",    icon: "table" },
  { id: "ai",         icon: "sparkle" },
  { id: "anomalies",  icon: "alert", badge: TOTAL_ANOMALIES },
  { id: "regional",   icon: "map" },
  { id: "governance", icon: "shield" },
]

function Shell() {
  const [route, setRoute]     = useState<Route>(() => (localStorage.getItem('cl_route') as Route) ?? 'landing')
  const [dark, setDark]       = useState(() => localStorage.getItem('cl_dark') === '1')
  const [lang, setLang]       = useState<Lang>(() => (localStorage.getItem('cl_lang') as Lang) ?? 'fr')
  const [density] = useState<Density>(() => (localStorage.getItem('cl_density') as Density) ?? 'regular')
  const [navOpen, setNavOpen] = useState(false)
  const t = useT(lang)
  const ar = lang === "ar"

  useEffect(() => {
    const el = document.documentElement
    el.setAttribute('data-theme', dark ? 'dark' : 'light')
    el.setAttribute('data-lang', lang)
    el.setAttribute('data-density', density)
    localStorage.setItem('cl_dark', dark ? '1' : '0')
    localStorage.setItem('cl_lang', lang)
    localStorage.setItem('cl_density', density)
    localStorage.setItem('cl_route', route)
  }, [dark, lang, density, route])

  const go = (r: string) => { setRoute(r as Route); setNavOpen(false); window.scrollTo(0, 0) }

  if (route === 'landing') {
    return <Landing onEnter={() => go('dashboard')} lang={lang} setLang={setLang} dark={dark}/>
  }

  const cur = NAV.find((n) => n.id === route)!

  return (
    <div className={ar ? "ar-text" : ""} style={{ display: "flex", minHeight: "100vh", background: "var(--paper)" }}>
      {/* sidebar */}
      <aside className="cl-sidebar" data-open={navOpen}
        style={{ position: "fixed", top: 0, bottom: 0, [ar ? "right" : "left"]: 0,
          width: "var(--sidebar-w)", background: "var(--surface)",
          borderInlineEnd: "1px solid var(--line)", display: "flex", flexDirection: "column", zIndex: 40 }}>
        <div style={{ padding: "20px 18px 18px", borderBottom: "1px solid var(--line)" }}>
          <button onClick={() => go('landing')} style={{ display: "block" }}><Logo size={24}/></button>
        </div>

        <nav style={{ flex: 1, padding: "14px 12px", display: "flex", flexDirection: "column", gap: 3, overflowY: "auto" }}>
          <div className="eyebrow" style={{ padding: "8px 12px 6px", fontSize: 9.5 }}>{t("navigation")}</div>
          {NAV.map((n) => {
            const on = route === n.id
            return (
              <button key={n.id} onClick={() => go(n.id)}
                style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 12px", borderRadius: 9, width: "100%",
                  background: on ? "var(--red-wash)" : "transparent", color: on ? "var(--red-ink)" : "var(--ink-2)",
                  fontWeight: on ? 700 : 500, fontSize: 14, transition: "all 0.13s", textAlign: ar ? "right" : "left" }}
                onMouseEnter={(e) => { if (!on) e.currentTarget.style.background = "var(--surface-sunk)" }}
                onMouseLeave={(e) => { if (!on) e.currentTarget.style.background = "transparent" }}>
                <Icon name={n.icon} size={18} stroke={on ? 2 : 1.7}/>
                <span style={{ flex: 1 }}>{t(n.id)}</span>
                {n.badge && (
                  <span className="badge tnum" style={{ background: on ? "var(--red)" : "var(--surface-sunk)",
                    color: on ? "#fff" : "var(--muted)", fontSize: 10.5, padding: "1px 7px" }}>
                    {n.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* sources */}
        <div style={{ padding: "14px 16px", borderTop: "1px solid var(--line)" }}>
          <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 8 }}>{t("sources_label")}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
            {SOURCES.map((s) => (
              <span key={s.name} className="mono" style={{ fontSize: 9.5, color: "var(--muted)", background: "var(--surface-sunk)", padding: "2px 6px", borderRadius: 4 }}>
                {s.name.replace(".gov.ma", "")}
              </span>
            ))}
          </div>
        </div>

        {/* user stub */}
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ display: "inline-flex", width: 34, height: 34, borderRadius: 99, alignItems: "center", justifyContent: "center",
            background: "var(--green-wash)", color: "var(--green-ink)", fontWeight: 700, fontSize: 13 }}>SE</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12.5, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>S. El Amrani</div>
            <div style={{ fontSize: 11, color: "var(--muted)" }}>{ar ? "صحفية استقصائية" : "Journaliste · CSO"}</div>
          </div>
        </div>
      </aside>

      {/* scrim */}
      {navOpen && <div onClick={() => setNavOpen(false)} className="cl-scrim"
        style={{ position: "fixed", inset: 0, background: "rgba(20,14,6,0.4)", zIndex: 35 }}/>}

      {/* main */}
      <div className="cl-main" style={{ flex: 1, marginInlineStart: "var(--sidebar-w)", display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* topbar */}
        <header style={{ position: "sticky", top: 0, zIndex: 30, display: "flex", alignItems: "center", gap: 14,
          padding: "0 clamp(16px,3vw,32px)", height: 64,
          background: "color-mix(in srgb, var(--paper) 88%, transparent)", backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--line)" }}>
          <button className="icon-btn cl-burger" onClick={() => setNavOpen((o) => !o)} style={{ display: "none" }}>
            <Icon name="menu" size={20}/>
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 0 }}>
            <Icon name={cur.icon} size={18} style={{ color: "var(--red)" }}/>
            <h1 style={{ fontSize: 16, fontWeight: 700, whiteSpace: "nowrap" }}>{t(route)}</h1>
          </div>
          <div style={{ flex: 1 }}/>
          <button onClick={() => go('ai')} className="cl-topsearch"
            style={{ display: "flex", alignItems: "center", gap: 9, height: 38, padding: "0 14px", borderRadius: 99,
              border: "1px solid var(--line-2)", background: "var(--surface)", color: "var(--muted)", fontSize: 13,
              minWidth: 200, maxWidth: 320, cursor: "pointer" }}>
            <Icon name="search" size={16}/>
            <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {ar ? "اسأل CivicLens…" : "Demander à CivicLens…"}
            </span>
          </button>
          <button className="icon-btn" onClick={() => setLang(ar ? 'fr' : 'ar')}>
            <span style={{ fontSize: 12.5, fontWeight: 700 }}>{ar ? "FR" : "ع"}</span>
          </button>
          <button className="icon-btn" onClick={() => setDark((d) => !d)}>
            <Icon name={dark ? "sun" : "moon"} size={18}/>
          </button>
        </header>

        {/* content */}
        <main style={{ flex: 1, padding: "clamp(18px,3vw,30px) clamp(16px,3vw,32px) 48px", maxWidth: 1320, width: "100%", margin: "0 auto" }}>
          {route === "dashboard"  && <Dashboard  lang={lang} dark={dark} go={go}/>}
          {route === "tenders"    && <Tenders    lang={lang}/>}
          {route === "ai"         && <AI         lang={lang}/>}
          {route === "anomalies"  && <Anomalies  lang={lang} go={go}/>}
          {route === "regional"   && <Regional   lang={lang} dark={dark}/>}
          {route === "governance" && <Governance lang={lang} dark={dark}/>}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Shell/>
    </QueryClientProvider>
  )
}
