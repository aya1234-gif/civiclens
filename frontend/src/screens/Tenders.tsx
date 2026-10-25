import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Icon } from '../components/Icon'
import { StatusBadge } from '../components/Badge'
import { useT, type Lang } from '../lib/i18n'
import { fetchTenders, type Tender } from '../lib/api'
import { fmtMAD } from '../lib/formatters'

interface Props { lang: Lang }

const TYPE_LABELS: Record<string, string> = {
  travaux: "Travaux", fournitures: "Fournitures", services: "Services", autre: "Autre"
}
const TYPE_COLORS: Record<string, { bg: string; fg: string }> = {
  travaux:     { bg: "var(--red-wash)",   fg: "var(--red-ink)" },
  fournitures: { bg: "var(--green-wash)", fg: "var(--green-ink)" },
  services:    { bg: "rgba(var(--viz-6-rgb,0,0,0),.08)", fg: "var(--ink-2)" },
  autre:       { bg: "var(--surface-sunk)", fg: "var(--muted)" },
}

export function Tenders({ lang }: Props) {
  const t = useT(lang)
  const ar = lang === "ar"
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [q, setQ] = useState("")
  const [type, setType] = useState("")
  const [region, setRegion] = useState("")
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['tenders', page, q, type, region],
    queryFn: () => fetchTenders({ page, page_size: 20, q: q || undefined, tender_type: type || undefined, region: region || undefined }),
    placeholderData: (prev) => prev,
  })

  const total = data?.total ?? 0
  const pages = data?.pages ?? 1

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
      {/* header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 className="serif" style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em" }}>
            {ar ? "الصفقات العمومية" : "Marchés publics"}
          </h1>
          <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 3 }}>
            {total > 0 ? `${total.toLocaleString('fr-FR')} ${t("results")}` : t("loading")}
          </p>
        </div>
        <button className="btn btn-ghost btn-sm"><Icon name="download" size={15}/>{t("export")}</button>
      </div>

      {/* search + filters */}
      <div className="card" style={{ padding: "14px 16px", display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        <div style={{ position: "relative", flex: "1 1 260px" }}>
          <Icon name="search" size={15} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--muted)", pointerEvents: "none" }}/>
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { setQ(search); setPage(1) } }}
            placeholder={t("search")}
            style={{ width: "100%", paddingLeft: 36, paddingRight: 12, height: 38, border: "1px solid var(--line-2)", borderRadius: "var(--r-md)",
              background: "var(--surface)", fontSize: 13.5, outline: "none" }}/>
        </div>
        <select value={type} onChange={(e) => { setType(e.target.value); setPage(1) }}
          style={{ height: 38, padding: "0 12px", border: "1px solid var(--line-2)", borderRadius: "var(--r-md)", background: "var(--surface)", fontSize: 13.5, color: "var(--ink)", outline: "none" }}>
          <option value="">{t("allTypes")}</option>
          <option value="travaux">Travaux</option>
          <option value="fournitures">Fournitures</option>
          <option value="services">Services</option>
        </select>
        <input value={region} onChange={(e) => { setRegion(e.target.value); setPage(1) }}
          placeholder={t("allRegions")}
          style={{ height: 38, padding: "0 12px", border: "1px solid var(--line-2)", borderRadius: "var(--r-md)", background: "var(--surface)", fontSize: 13.5, outline: "none", width: 160 }}/>
        {(q || type || region) && (
          <button className="btn btn-sm btn-ghost" onClick={() => { setSearch(""); setQ(""); setType(""); setRegion(""); setPage(1) }}>
            <Icon name="close" size={13}/>{t("reset")}
          </button>
        )}
      </div>

      {/* table */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
            <thead>
              <tr style={{ background: "var(--surface-sunk)", borderBottom: "1px solid var(--line)" }}>
                {[t("ref"), t("buyer"), t("objet"), t("type"), t("regionW"), t("pub"), t("status"), ""].map((h, i) => (
                  <th key={i} style={{ padding: "10px var(--cell-x)", textAlign: "left", fontSize: 11, fontWeight: 700,
                    letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--muted)", whiteSpace: "nowrap" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading && Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--line)" }}>
                  {Array.from({ length: 8 }).map((__, j) => (
                    <td key={j} style={{ padding: "var(--pad-y) var(--cell-x)" }}>
                      <div className="skeleton" style={{ height: 12, width: j === 2 ? 200 : j === 1 ? 160 : 80, borderRadius: 4 }}/>
                    </td>
                  ))}
                </tr>
              ))}
              {!isLoading && data?.items.map((row: Tender) => {
                const typStyle = TYPE_COLORS[row.tender_type ?? "autre"] ?? TYPE_COLORS.autre
                const isExp = expanded === row.reference
                return (
                  <>
                    <tr key={row.reference}
                      onClick={() => setExpanded(isExp ? null : row.reference)}
                      style={{ borderBottom: "1px solid var(--line)", cursor: "pointer", transition: "background 0.1s" }}
                      onMouseEnter={(e) => !isExp && (e.currentTarget.style.background = "var(--surface-2)")}
                      onMouseLeave={(e) => !isExp && (e.currentTarget.style.background = "transparent")}>
                      <td style={{ padding: "var(--pad-y) var(--cell-x)" }}>
                        <span className="mono" style={{ fontSize: 11.5, fontWeight: 600, color: "var(--muted)" }}>{row.reference}</span>
                      </td>
                      <td style={{ padding: "var(--pad-y) var(--cell-x)", maxWidth: 180 }}>
                        <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 13 }}>
                          {row.contracting_authority ?? "—"}
                        </span>
                      </td>
                      <td style={{ padding: "var(--pad-y) var(--cell-x)", maxWidth: 280 }}>
                        <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 500 }}>
                          {row.object ?? "—"}
                        </span>
                      </td>
                      <td style={{ padding: "var(--pad-y) var(--cell-x)" }}>
                        <span className="badge" style={{ background: typStyle.bg, color: typStyle.fg }}>
                          {TYPE_LABELS[row.tender_type ?? "autre"] ?? row.tender_type ?? "—"}
                        </span>
                      </td>
                      <td style={{ padding: "var(--pad-y) var(--cell-x)", color: "var(--ink-2)", whiteSpace: "nowrap", fontSize: 12.5 }}>
                        {row.wilaya ?? row.region ?? "—"}
                      </td>
                      <td className="mono tnum" style={{ padding: "var(--pad-y) var(--cell-x)", fontSize: 12, color: "var(--muted)", whiteSpace: "nowrap" }}>
                        {row.publication_date ?? "—"}
                      </td>
                      <td style={{ padding: "var(--pad-y) var(--cell-x)" }}>
                        <StatusBadge status="open" lang={lang}/>
                      </td>
                      <td style={{ padding: "var(--pad-y) var(--cell-x)" }}>
                        <Icon name={isExp ? "chevUp" : "chevD"} size={14} style={{ color: "var(--muted)" }}/>
                      </td>
                    </tr>
                    {isExp && (
                      <tr key={`${row.reference}-exp`} style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--line)" }}>
                        <td colSpan={8} style={{ padding: "16px 20px" }}>
                          {row.object && (
                            <div style={{ marginBottom: 16 }}>
                              <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 4 }}>{t("objet")}</div>
                              <div style={{ fontSize: 13.5, lineHeight: 1.5 }}>{row.object}</div>
                            </div>
                          )}
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
                            {[
                              { l: t("ref"),   v: row.reference },
                              { l: t("buyer"),  v: row.contracting_authority },
                              { l: t("type"),   v: row.tender_type },
                              { l: t("pub"),    v: row.publication_date },
                              { l: t("delai"),  v: row.deadline_date },
                              { l: t("regionW"), v: row.wilaya ?? row.region },
                              // Only present for awarded tenders whose PV notice was
                              // successfully scraped — most tenders won't show this yet.
                              ...(row.montant_mad != null ? [{ l: ar ? "المبلغ" : "Montant attribué", v: `${fmtMAD(row.montant_mad)} MAD` }] : []),
                              ...(row.attributaire ? [{ l: ar ? "الفائز" : "Attributaire", v: row.attributaire }] : []),
                            ].map(({ l, v }) => v && (
                              <div key={l}>
                                <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 4 }}>{l}</div>
                                <div style={{ fontSize: 13.5 }}>{v}</div>
                              </div>
                            ))}
                          </div>
                          {row.source_url && (
                            <a href={row.source_url} target="_blank" rel="noopener noreferrer"
                              className="btn btn-sm btn-ghost" style={{ marginTop: 14, display: "inline-flex" }}>
                              <Icon name="external" size={14}/>marchespublics.gov.ma
                            </a>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
              {!isLoading && data?.items.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: "center", padding: "48px 20px", color: "var(--muted)" }}>{t("noResults")}</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* pagination */}
        {pages > 1 && (
          <div style={{ padding: "12px 20px", borderTop: "1px solid var(--line)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13 }}>
            <span style={{ color: "var(--muted)" }}>
              {t("page")} {page} / {pages} · {total.toLocaleString('fr-FR')} {t("results")}
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              <button className="btn btn-sm btn-ghost" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
                <Icon name="chevL" size={14}/>
              </button>
              <button className="btn btn-sm btn-ghost" disabled={page === pages} onClick={() => setPage((p) => p + 1)}>
                <Icon name="chevR" size={14}/>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
