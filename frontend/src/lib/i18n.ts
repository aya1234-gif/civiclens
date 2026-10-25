export type Lang = 'fr' | 'ar'

const STR: Record<Lang, Record<string, string>> = {
  fr: {
    explore: "Explorer les données", login: "Se connecter", live: "Données en direct",
    tendersIndexed: "Marchés indexés", valueTracked: "Valeur suivie (MAD)", anomaliesFlagged: "Anomalies signalées",
    dashboard: "Tableau de bord", tenders: "Marchés publics", ai: "Analyse IA", anomalies: "Anomalies & alertes",
    regional: "Analytique régionale", governance: "Gouvernance & audit",
    search: "Rechercher un marché, un acheteur, une référence…", export: "Exporter CSV",
    region: "Région", type: "Type", authority: "Acheteur", amount: "Montant", date: "Date", status: "Statut",
    allRegions: "Toutes les régions", allTypes: "Tous les types",
    ref: "Référence", buyer: "Acheteur public", objet: "Objet", montant: "Montant estimé (MAD)", regionW: "Région / Wilaya",
    pub: "Date publication", delai: "Délai", results: "résultats", filters: "Filtres", reset: "Réinitialiser",
    askPlaceholder: "Posez une question en français ou en arabe…", analysing: "CivicLens analyse…",
    suggested: "Questions suggérées", sources: "Sources citées", tokens: "jetons", model: "Modèle",
    severity: "Sévérité", high: "Élevée", medium: "Moyenne", all: "Toutes", score: "Score d'anomalie",
    explanation: "Explication du modèle (SHAP)", viewTender: "Voir le marché", exportReport: "Exporter le rapport",
    byTenderCount: "Nb de marchés", byValue: "Valeur totale",
    byMinistry: "Dépenses par ministère (Md MAD)", byType: "Répartition par type", byMonth: "Activité mensuelle",
    auditLog: "Journal d'audit des modèles", biasAudit: "Audit d'équité — taux de signalement par région",
    lineage: "Traçabilité des données", back: "Retour",
    todayTenders: "Marchés du jour", activeRegions: "Régions actives", provinces: "provinces",
    navigation: "Navigation", sources_label: "Sources",
    noResults: "Aucun résultat", loading: "Chargement…",
  },
  ar: {
    explore: "استكشف البيانات", login: "تسجيل الدخول", live: "بيانات مباشرة",
    tendersIndexed: "الصفقات المفهرسة", valueTracked: "القيمة المتتبَّعة (درهم)", anomaliesFlagged: "الحالات الشاذة",
    dashboard: "لوحة القيادة", tenders: "الصفقات العمومية", ai: "تحليل بالذكاء الاصطناعي", anomalies: "الحالات الشاذة والتنبيهات",
    regional: "التحليل الجهوي", governance: "الحوكمة والتدقيق",
    search: "ابحث عن صفقة أو مشترٍ أو مرجع…", export: "تصدير CSV",
    region: "الجهة", type: "النوع", authority: "المشتري", amount: "المبلغ", date: "التاريخ", status: "الحالة",
    allRegions: "كل الجهات", allTypes: "كل الأنواع",
    ref: "المرجع", buyer: "المشتري العمومي", objet: "الموضوع", montant: "المبلغ التقديري (درهم)", regionW: "الجهة / الولاية",
    pub: "تاريخ النشر", delai: "الأجل", results: "نتيجة", filters: "عوامل التصفية", reset: "إعادة ضبط",
    askPlaceholder: "اطرح سؤالاً بالفرنسية أو العربية…", analysing: "…CivicLens يحلّل",
    suggested: "أسئلة مقترحة", sources: "المصادر المذكورة", tokens: "وحدات", model: "النموذج",
    severity: "الخطورة", high: "مرتفعة", medium: "متوسطة", all: "الكل", score: "درجة الشذوذ",
    explanation: "تفسير النموذج (SHAP)", viewTender: "عرض الصفقة", exportReport: "تصدير التقرير",
    byTenderCount: "عدد الصفقات", byValue: "القيمة الإجمالية",
    byMinistry: "النفقات حسب الوزارة (مليار درهم)", byType: "التوزيع حسب النوع", byMonth: "النشاط الشهري",
    auditLog: "سجل تدقيق النماذج", biasAudit: "تدقيق الإنصاف — معدل الإبلاغ حسب الجهة",
    lineage: "تتبّع مصدر البيانات", back: "رجوع",
    todayTenders: "صفقات اليوم", activeRegions: "الجهات النشطة", provinces: "أقاليم",
    navigation: "التنقل", sources_label: "المصادر",
    noResults: "لا توجد نتائج", loading: "جارٍ التحميل…",
  },
}

export function useT(lang: Lang) {
  return (k: string): string => STR[lang]?.[k] ?? STR.fr[k] ?? k
}
