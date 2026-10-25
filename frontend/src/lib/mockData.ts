// Mock data — used while API data is loading, and for sections not yet wired to the API.

export const REGIONS = [
  { id: "tta", fr: "Tanger-Tétouan-Al Hoceïma", ar: "طنجة تطوان الحسيمة", tenders: 1284, valueMAD: 8.42e9, anomalies: 31, prov: ["Tanger-Assilah","Tétouan","Al Hoceïma","Larache","Chefchaouen","Ouezzane","M'diq-Fnideq"] },
  { id: "ori", fr: "Oriental", ar: "الشرق", tenders: 742, valueMAD: 4.10e9, anomalies: 22, prov: ["Oujda-Angad","Nador","Berkane","Taourirt","Jerada","Driouch","Guercif","Figuig"] },
  { id: "fme", fr: "Fès-Meknès", ar: "فاس مكناس", tenders: 1131, valueMAD: 6.88e9, anomalies: 27, prov: ["Fès","Meknès","El Hajeb","Ifrane","Taza","Sefrou","Boulemane","Moulay Yacoub","Taounate"] },
  { id: "rsk", fr: "Rabat-Salé-Kénitra", ar: "الرباط سلا القنيطرة", tenders: 1903, valueMAD: 14.27e9, anomalies: 44, prov: ["Rabat","Salé","Kénitra","Skhirate-Témara","Khémisset","Sidi Kacem","Sidi Slimane"] },
  { id: "bmk", fr: "Béni Mellal-Khénifra", ar: "بني ملال خنيفرة", tenders: 588, valueMAD: 3.21e9, anomalies: 19, prov: ["Béni Mellal","Khénifra","Khouribga","Azilal","Fquih Ben Salah"] },
  { id: "cst", fr: "Casablanca-Settat", ar: "الدار البيضاء سطات", tenders: 2611, valueMAD: 21.93e9, anomalies: 58, prov: ["Casablanca","Mohammedia","El Jadida","Settat","Berrechid","Benslimane","Médiouna","Nouaceur","Sidi Bennour"] },
  { id: "msa", fr: "Marrakech-Safi", ar: "مراكش آسفي", tenders: 1042, valueMAD: 7.36e9, anomalies: 33, prov: ["Marrakech","Safi","Essaouira","El Kelâa des Sraghna","Chichaoua","Al Haouz","Rehamna","Youssoufia"] },
  { id: "dta", fr: "Drâa-Tafilalet", ar: "درعة تافيلالت", tenders: 421, valueMAD: 2.04e9, anomalies: 14, prov: ["Errachidia","Ouarzazate","Zagora","Tinghir","Midelt"] },
  { id: "sma", fr: "Souss-Massa", ar: "سوس ماسة", tenders: 876, valueMAD: 5.55e9, anomalies: 25, prov: ["Agadir-Ida Outanane","Inezgane-Aït Melloul","Taroudant","Tiznit","Chtouka-Aït Baha","Tata"] },
  { id: "gon", fr: "Guelmim-Oued Noun", ar: "كلميم واد نون", tenders: 198, valueMAD: 1.12e9, anomalies: 9, prov: ["Guelmim","Tan-Tan","Sidi Ifni","Assa-Zag"] },
  { id: "lsh", fr: "Laâyoune-Sakia El Hamra", ar: "العيون الساقية الحمراء", tenders: 264, valueMAD: 2.71e9, anomalies: 17, prov: ["Laâyoune","Boujdour","Tarfaya","Es-Semara"] },
  { id: "doe", fr: "Dakhla-Oued Ed-Dahab", ar: "الداخلة وادي الذهب", tenders: 142, valueMAD: 1.88e9, anomalies: 12, prov: ["Oued Ed-Dahab","Aousserd"] },
]

export const STATUSES = [
  { id: "open",    fr: "Ouvert",         ar: "مفتوح",       tone: "green"   },
  { id: "closing", fr: "Clôture proche", ar: "قرب الإغلاق", tone: "amber"   },
  { id: "awarded", fr: "Attribué",       ar: "مُسند",        tone: "neutral" },
  { id: "flagged", fr: "Signalé",        ar: "مُبلّغ عنه",   tone: "red"     },
]

export const ANOMALY_TYPES = [
  { id: "prix",   fr: "Prix gonflé",           ar: "سعر مبالغ فيه", color: "var(--viz-1)" },
  { id: "unique", fr: "Soumissionnaire unique", ar: "متعهد وحيد",   color: "var(--viz-2)" },
  { id: "frac",   fr: "Marché fractionné",      ar: "صفقة مجزأة",   color: "var(--viz-3)" },
  { id: "delai",  fr: "Délai suspect",          ar: "أجل مشبوه",    color: "var(--viz-6)" },
]

export const ANOMALIES = [
  { id: "ANM-0481", tenderRef: "AOO-2026-01084", type: "prix",   score: 94, severity: "high",   region: "cst",
    buyer: "Conseil régional de Casablanca-Settat", objet: "Réhabilitation du réseau d'assainissement liquide", amount: 41.2e6,
    shap: [["Écart au prix de marché (+58%)", 0.42],["Historique acheteur", 0.21],["Concentration fournisseur", 0.18],["Délai anormal", 0.11],["Saisonnalité", 0.08]] },
  { id: "ANM-0479", tenderRef: "AOO-2026-01147", type: "unique", score: 88, severity: "high",   region: "rsk",
    buyer: "Commune urbaine de Rabat", objet: "Services de gardiennage et sécurité des bâtiments publics", amount: 12.6e6,
    shap: [["1 seul soumissionnaire", 0.51],["Réattribution récurrente", 0.22],["Cahier des charges restrictif", 0.15],["Délai publication court", 0.12]] },
  { id: "ANM-0474", tenderRef: "AOO-2026-00910", type: "frac",  score: 81, severity: "high",   region: "tta",
    buyer: "Conseil régional de Tanger", objet: "Réfection de la voirie et assainissement", amount: 4.9e6,
    shap: [["7 marchés < seuil sur 30j", 0.46],["Même attributaire", 0.27],["Objet quasi-identique", 0.19],["Même mois budgétaire", 0.08]] },
  { id: "ANM-0470", tenderRef: "AOO-2026-01231", type: "delai", score: 76, severity: "medium", region: "fme",
    buyer: "Ministère de l'Éducation Nationale", objet: "Fourniture de mobilier scolaire", amount: 8.1e6,
    shap: [["Délai soumission 9j (médiane 30j)", 0.44],["Publication veille de week-end", 0.24],["Attribution rapide", 0.2],["Acheteur récidiviste", 0.12]] },
  { id: "ANM-0468", tenderRef: "AOO-2026-00777", type: "prix",  score: 72, severity: "medium", region: "msa",
    buyer: "Agence Urbaine de Marrakech", objet: "Aménagement d'espaces verts urbains", amount: 6.4e6,
    shap: [["Écart au prix de marché (+31%)", 0.38],["Variabilité fournisseur", 0.26],["Faible concurrence", 0.21],["Localisation", 0.15]] },
]

export const SOURCES = [
  { name: "marchespublics.gov.ma", label: "Portail des marchés publics", count: "11 842 avis" },
  { name: "data.gov.ma",           label: "Open Data Maroc",             count: "datasets ouverts" },
  { name: "HCP",                   label: "Haut-Commissariat au Plan",   count: "indicateurs régionaux" },
  { name: "finances.gov.ma",       label: "Ministère des Finances",      count: "Loi de Finances 2026" },
]

export const SPEND_BY_MINISTRY = [
  { name: "Équipement & Eau", v: 18.4 },
  { name: "Santé", v: 12.1 },
  { name: "Éducation", v: 9.7 },
  { name: "Intérieur (DGCT)", v: 8.3 },
  { name: "ONEE", v: 6.9 },
  { name: "Transport", v: 5.2 },
  { name: "Agriculture", v: 3.8 },
]

export const SPEND_BY_TYPE = [
  { name: "Travaux",      v: 58, color: "var(--viz-1)" },
  { name: "Fournitures",  v: 27, color: "var(--viz-3)" },
  { name: "Services",     v: 15, color: "var(--viz-5)" },
]

export const MONTHLY_ACTIVITY = [
  { m: "Jan", v: 612 }, { m: "Fév", v: 698 }, { m: "Mar", v: 901 },
  { m: "Avr", v: 845 }, { m: "Mai", v: 1023 }, { m: "Juin", v: 1187 },
  { m: "Juil", v: 956 }, { m: "Août", v: 540 }, { m: "Sep", v: 1104 },
  { m: "Oct", v: 1240 }, { m: "Nov", v: 1098 }, { m: "Déc", v: 877 },
]

export const AUDIT_LOG = [
  { ts: "2026-06-04 09:42:11", model: "civiclens-anomaly-v3.2", action: "Détection anomalies — lot quotidien", region: "Toutes", inHash: "a91f…3c7d", outHash: "5e22…b801", records: 412 },
  { ts: "2026-06-04 09:41:03", model: "civiclens-nlq-v2.1",     action: "Requête NL → SQL",                  region: "cst",    inHash: "77b2…01ae", outHash: "c4f9…2210", records: 1 },
  { ts: "2026-06-04 08:15:55", model: "civiclens-ingest-v1.8",  action: "Ingestion marchespublics.gov.ma",   region: "Toutes", inHash: "1d0c…9f4b", outHash: "8a7e…ce30", records: 388 },
  { ts: "2026-06-03 22:00:02", model: "civiclens-anomaly-v3.2", action: "Recalcul scores SHAP",              region: "Toutes", inHash: "b3e1…77aa", outHash: "9012…44df", records: 11842 },
  { ts: "2026-06-03 14:09:21", model: "civiclens-bias-v0.9",    action: "Audit d'équité régionale",          region: "Toutes", inHash: "30dd…aa18", outHash: "7c66…1f52", records: 12 },
]

export const BIAS_AUDIT = REGIONS.map((reg) => ({
  id: reg.id, fr: reg.fr,
  rate: +((reg.anomalies / reg.tenders) * 1000).toFixed(1),
})).sort((a, b) => b.rate - a.rate)

export const TOTAL_TENDERS  = REGIONS.reduce((s, r) => s + r.tenders, 0)
export const TOTAL_VALUE    = REGIONS.reduce((s, r) => s + r.valueMAD, 0)
export const TOTAL_ANOMALIES = REGIONS.reduce((s, r) => s + r.anomalies, 0)

export const SUGGESTED_Q = [
  "Quelles régions ont le plus d'anomalies de prix en 2026 ?",
  "Montre les 5 plus gros marchés attribués à un soumissionnaire unique.",
  "Compare les dépenses en travaux entre Casablanca-Settat et Rabat-Salé-Kénitra.",
  "ما هي القطاعات الأكثر عرضة للصفقات المجزأة؟",
]
