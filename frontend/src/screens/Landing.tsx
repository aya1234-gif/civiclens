import { Icon } from '../components/Icon'
import { Logo } from '../components/Logo'
import { MoroccoMap } from '../components/MoroccoMap'
import { fmtMAD, fmtInt } from '../lib/formatters'
import { SOURCES, TOTAL_TENDERS, TOTAL_VALUE, TOTAL_ANOMALIES } from '../lib/mockData'
import { useT, type Lang } from '../lib/i18n'

// Zellige tessellation background
function Zellige({ opacity = 0.06 }) {
  function starPts(cx: number, cy: number, ro: number, ri: number) {
    const p: string[] = []
    for (let i = 0; i < 16; i++) {
      const r = i % 2 ? ri : ro, a = (Math.PI / 8) * i - Math.PI / 2
      p.push(`${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`)
    }
    return p.join(" ")
  }
  return (
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, pointerEvents: "none", color: "var(--red)" }} aria-hidden="true">
      <defs>
        <pattern id="zlg" width="92" height="92" patternUnits="userSpaceOnUse">
          <polygon points={starPts(46, 46, 30, 15)} fill="none" stroke="currentColor" strokeWidth="1.2" opacity={opacity}/>
          <polygon points={starPts(0, 0, 18, 9)} fill="none" stroke="currentColor" strokeWidth="1.2" opacity={opacity}/>
          <polygon points={starPts(92, 0, 18, 9)} fill="none" stroke="currentColor" strokeWidth="1.2" opacity={opacity}/>
          <polygon points={starPts(0, 92, 18, 9)} fill="none" stroke="currentColor" strokeWidth="1.2" opacity={opacity}/>
          <polygon points={starPts(92, 92, 18, 9)} fill="none" stroke="currentColor" strokeWidth="1.2" opacity={opacity}/>
          <rect x="41" y="41" width="10" height="10" transform="rotate(45 46 46)" fill="currentColor" opacity={opacity * 0.8}/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#zlg)"/>
    </svg>
  )
}

interface Props { onEnter: () => void; lang: Lang; setLang: (l: Lang) => void; dark: boolean }

export function Landing({ onEnter, lang, setLang, dark }: Props) {
  const t = useT(lang)
  const ar = lang === "ar"
  return (
    <div className={ar ? "ar-text" : ""} style={{ minHeight: "100vh", background: "var(--paper)", overflowX: "hidden", position: "relative" }}>
      {/* hero background */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 900, overflow: "hidden", pointerEvents: "none" }} aria-hidden="true">
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(120% 80% at 100% 0%, var(--red-wash) 0%, transparent 42%), radial-gradient(100% 70% at 0% 12%, var(--green-wash) 0%, transparent 38%)", opacity: 0.7 }}/>
        <div style={{ position: "absolute", inset: 0, maskImage: "linear-gradient(to bottom, #000 0%, #000 55%, transparent 100%)", WebkitMaskImage: "linear-gradient(to bottom, #000 0%, #000 55%, transparent 100%)" }}>
          <Zellige opacity={dark ? 0.1 : 0.07}/>
        </div>
      </div>

      {/* header */}
      <header style={{ position: "sticky", top: 0, zIndex: 20, display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px clamp(20px,5vw,64px)", background: "color-mix(in srgb, var(--paper) 86%, transparent)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--line)" }}>
        <Logo size={26}/>
        <nav style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button className="btn btn-sm btn-ghost" onClick={() => setLang(ar ? "fr" : "ar")}><Icon name="globe" size={15}/>{ar ? "FR" : "AR"}</button>
          <button className="btn btn-sm btn-ghost" onClick={onEnter}>{t("login")}</button>
          <button className="btn btn-sm btn-primary" onClick={onEnter}>{t("explore")}</button>
        </nav>
      </header>

      {/* hero */}
      <section style={{ position: "relative", zIndex: 1, maxWidth: 1240, margin: "0 auto",
        padding: "clamp(40px,7vw,92px) clamp(20px,5vw,64px) 40px",
        display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: "clamp(28px,5vw,64px)", alignItems: "center" }}>
        <div className="animate-fadeUp">
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "5px 12px 5px 8px", borderRadius: 99,
            background: "var(--surface)", border: "1px solid var(--line)", marginBottom: 26, boxShadow: "var(--shadow-sm)" }}>
            <span style={{ display: "inline-flex", width: 18, height: 18, borderRadius: 99, background: "var(--green)", alignItems: "center", justifyContent: "center" }}>
              <span style={{ width: 7, height: 7, borderRadius: 99, background: "#fff", animation: "blink 2s infinite" }}/>
            </span>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink-2)" }}>
              {ar ? "تحديث يومي من المصادر الرسمية" : "Mise à jour quotidienne des sources officielles"}
            </span>
          </div>
          <h1 className="serif" style={{ fontSize: "clamp(38px,5.4vw,68px)", fontWeight: 600, lineHeight: 1.04, letterSpacing: "-0.025em", marginBottom: 24 }}>
            {ar
              ? <><span>تتبّع كل </span><span style={{ color: "var(--red)" }}>درهم</span><span> من الميزانية العمومية المغربية.</span></>
              : <><span>Suivez chaque </span><span style={{ color: "var(--red)", fontStyle: "italic" }}>dirham</span><span> du budget public marocain.</span></>}
          </h1>
          <p style={{ fontSize: "clamp(16px,1.5vw,19px)", color: "var(--ink-2)", lineHeight: 1.6, maxWidth: 540, marginBottom: 32 }}>
            {ar
              ? "منصة شفافية تعتمد الذكاء الاصطناعي: تستوعب كل بيانات الصفقات العمومية، ترصد الحالات الشاذة، وتتيح طرح الأسئلة بلغة طبيعية حول الإنفاق العام."
              : "La plateforme de transparence qui ingère l'ensemble des marchés publics, détecte les anomalies et répond à vos questions sur la dépense publique — en langage naturel."}
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button className="btn btn-primary" onClick={onEnter} style={{ height: 50, fontSize: 15.5, padding: "0 26px" }}>
              {t("explore")}<Icon name="chevR" size={17}/>
            </button>
            <button className="btn btn-ghost" onClick={onEnter} style={{ height: 50, fontSize: 15.5, padding: "0 22px" }}>
              <Icon name="sparkle" size={17}/>{ar ? "جرّب التحليل" : "Essayer l'analyse IA"}
            </button>
          </div>
        </div>

        {/* map card */}
        <div className="card animate-fadeUp" style={{ padding: 22, animationDelay: "120ms" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span className="eyebrow">{ar ? "خريطة جهوية" : "Carte régionale"}</span>
            <span className="badge" style={{ background: "var(--surface-sunk)", color: "var(--muted)" }}>
              <Icon name="map" size={12}/>{ar ? "12 جهة" : "12 régions"}
            </span>
          </div>
          <MoroccoMap metric="valueMAD" compact onSelect={onEnter} lang={lang}/>
        </div>
      </section>

      {/* stats bar */}
      <section style={{ position: "relative", zIndex: 1, maxWidth: 1240, margin: "0 auto", padding: "20px clamp(20px,5vw,64px) 56px" }}>
        <div className="card" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", overflow: "hidden", boxShadow: "var(--shadow-md)" }}>
          {[
            { v: fmtInt(TOTAL_TENDERS), l: t("tendersIndexed"), icon: "table", a: "neutral" },
            { v: fmtMAD(TOTAL_VALUE, { compact: true }) + " MAD", l: t("valueTracked"), icon: "coins", a: "green" },
            { v: fmtInt(TOTAL_ANOMALIES), l: t("anomaliesFlagged"), icon: "alert", a: "red" },
          ].map((s, i) => (
            <div key={i} style={{ padding: "30px 32px", borderRight: i < 2 ? "1px solid var(--line)" : "none", display: "flex", flexDirection: "column", gap: 8 }}>
              <span style={{ display: "inline-flex", width: 36, height: 36, borderRadius: 9, alignItems: "center", justifyContent: "center",
                background: s.a === "red" ? "var(--red-wash)" : s.a === "green" ? "var(--green-wash)" : "var(--surface-sunk)",
                color: s.a === "red" ? "var(--red)" : s.a === "green" ? "var(--green-ink)" : "var(--ink-2)", marginBottom: 6 }}>
                <Icon name={s.icon} size={19}/>
              </span>
              <span className="serif tnum" style={{ fontSize: "clamp(28px,3.4vw,42px)", fontWeight: 600, lineHeight: 1, letterSpacing: "-0.02em" }}>{s.v}</span>
              <span style={{ fontSize: 13.5, color: "var(--muted)", fontWeight: 500 }}>{s.l}</span>
            </div>
          ))}
        </div>
      </section>

      {/* features */}
      <section style={{ maxWidth: 1240, margin: "0 auto", padding: "0 clamp(20px,5vw,64px) 64px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 18 }}>
          {[
            { icon: "table",   t: ar ? "مستكشف الصفقات" : "Explorateur de marchés",         d: ar ? "تصفية حسب الجهة والنوع والمبلغ والمشتري." : "Filtrez par région, type, montant et acheteur." },
            { icon: "alert",   t: ar ? "كشف الحالات الشاذة" : "Détection d'anomalies",       d: ar ? "أسعار مبالغ فيها، متعهد وحيد، صفقات مجزأة." : "Prix gonflés, soumissionnaire unique, fractionnement." },
            { icon: "sparkle", t: ar ? "تحليل بالذكاء الاصطناعي" : "Analyse en langage naturel", d: ar ? "اطرح أسئلتك بالفرنسية أو العربية مع مصادر." : "Posez vos questions, réponses sourcées et citées." },
            { icon: "shield",  t: ar ? "حوكمة وتدقيق" : "Gouvernance & audit",              d: ar ? "سجلّ النماذج، تدقيق الإنصاف، تتبّع المصدر." : "Journal des modèles, audit d'équité, traçabilité." },
          ].map((f, i) => (
            <div key={i} className="card animate-fadeUp" style={{ padding: "22px 22px 24px", animationDelay: `${i * 70}ms` }}>
              <span style={{ display: "inline-flex", width: 40, height: 40, borderRadius: 10, alignItems: "center", justifyContent: "center",
                background: "var(--surface-sunk)", color: "var(--red)", marginBottom: 16 }}>
                <Icon name={f.icon} size={20}/>
              </span>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 7 }}>{f.t}</h3>
              <p style={{ fontSize: 13.5, color: "var(--muted)", lineHeight: 1.55 }}>{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* sources */}
      <section style={{ background: "var(--surface)", borderTop: "1px solid var(--line)", borderBottom: "1px solid var(--line)" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto", padding: "44px clamp(20px,5vw,64px)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
            <Icon name="shield" size={18} style={{ color: "var(--muted)" }}/>
            <span className="eyebrow">{ar ? "مصادر رسمية وموثوقة" : "Sources officielles & vérifiables"}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 16 }}>
            {SOURCES.map((s, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 13, padding: "14px 16px", borderRadius: 11, border: "1px solid var(--line)", background: "var(--surface-2)" }}>
                <span style={{ display: "inline-flex", width: 38, height: 38, borderRadius: 9, alignItems: "center", justifyContent: "center", background: "var(--red-wash)", color: "var(--red)", flexShrink: 0 }}>
                  <Icon name="shield" size={18}/>
                </span>
                <div style={{ minWidth: 0 }}>
                  <div className="mono" style={{ fontSize: 12.5, fontWeight: 700, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)" }}>{s.label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ maxWidth: 1240, margin: "0 auto", padding: "64px clamp(20px,5vw,64px)" }}>
        <div style={{ borderRadius: "var(--r-xl)", background: "var(--red)", color: "#fff", padding: "clamp(32px,5vw,56px)", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", inset: 0, opacity: 0.12, backgroundImage: "radial-gradient(circle at 1px 1px, #fff 1px, transparent 0)", backgroundSize: "22px 22px" }}/>
          <div style={{ position: "relative", maxWidth: 620 }}>
            <h2 className="serif" style={{ fontSize: "clamp(26px,3.4vw,40px)", fontWeight: 600, lineHeight: 1.1, marginBottom: 14, letterSpacing: "-0.02em" }}>
              {ar ? "الشفافية تبدأ بالبيانات." : "La transparence commence par la donnée."}
            </h2>
            <p style={{ fontSize: 16, opacity: 0.9, lineHeight: 1.6, marginBottom: 28 }}>
              {ar ? "للصحفيين، المجتمع المدني، الباحثين والمسؤولين." : "Pour les journalistes, la société civile, les chercheurs et les responsables publics."}
            </p>
            <button className="btn" onClick={onEnter} style={{ background: "#fff", color: "var(--red-ink)", height: 50, fontSize: 15.5, padding: "0 26px" }}>
              {t("explore")}<Icon name="chevR" size={17}/>
            </button>
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 36, flexWrap: "wrap", gap: 12 }}>
          <Logo size={22}/>
          <span style={{ fontSize: 12.5, color: "var(--muted)" }}>{ar ? "نموذج أولي توضيحي · بيانات تجريبية" : "Prototype de démonstration · données illustratives"}</span>
        </div>
      </section>
    </div>
  )
}
