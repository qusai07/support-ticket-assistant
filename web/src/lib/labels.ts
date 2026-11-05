/** Bilingual labels for DATA values (channels, scenario tags, permissions, routing keys).
 *  UI chrome strings live in i18n.tsx; these describe things the backend sends as codes. */
import type { Lang } from "./i18n";

type L = { en: string; ar: string };
type LD = L & { den?: string; dar?: string }; // optional description

const pick = (m: Record<string, L>, k: string, lang: Lang) => m[k]?.[lang] ?? k;

export const CHANNELS: Record<string, L> = {
  email: { en: "Email", ar: "البريد الإلكتروني" },
  chat: { en: "Live chat", ar: "المحادثة المباشرة" },
  web_form: { en: "Web form", ar: "نموذج الموقع" },
  phone: { en: "Phone", ar: "الهاتف" },
};

export const TAGS: Record<string, L> = {
  simple: { en: "Simple", ar: "بسيطة" }, positive: { en: "Positive", ar: "إيجابية" },
  policy_edge: { en: "Policy edge case", ar: "حالة حدّية في السياسة" }, action_required: { en: "Needs human action", ar: "تتطلب إجراءً بشرياً" },
  money: { en: "Money", ar: "مالية" }, angry: { en: "Angry customer", ar: "عميل غاضب" }, very_negative: { en: "Very negative", ar: "سلبية جداً" },
  churn_risk: { en: "Churn risk", ar: "خطر فقدان العميل" }, safety: { en: "Safety", ar: "سلامة" }, chargeback: { en: "Chargeback", ar: "اعتراض بنكي" },
  refund_over_threshold: { en: "Refund over limit", ar: "استرداد يتجاوز الحد" }, vip: { en: "VIP", ar: "كبار العملاء" },
  legal: { en: "Legal", ar: "قانونية" }, fraud: { en: "Fraud", ar: "احتيال" }, missing_info: { en: "Missing info", ar: "معلومات ناقصة" },
  multi_issue: { en: "Multiple issues", ar: "مشكلات متعددة" }, prompt_injection: { en: "Prompt injection", ar: "حقن أوامر" },
  social_engineering: { en: "Social engineering", ar: "هندسة اجتماعية" }, non_english: { en: "Non-English", ar: "غير إنجليزية" },
  arabic: { en: "Arabic", ar: "عربية" }, msa: { en: "Modern Standard", ar: "فصحى" }, gulf: { en: "Gulf dialect", ar: "لهجة خليجية" },
  levantine: { en: "Levantine dialect", ar: "لهجة شامية" }, egyptian: { en: "Egyptian dialect", ar: "لهجة مصرية" },
  arabizi: { en: "Arabizi", ar: "عربيزي" }, mixed_language: { en: "Mixed language", ar: "لغة مختلطة" },
  false_positive_trap: { en: "False-positive trap", ar: "فخ إنذار كاذب" },
};

export const PERMISSIONS: Record<string, LD> = {
  "tickets:view": { en: "View team tickets", ar: "عرض تذاكر الفريق", den: "See tickets routed to their own team", dar: "رؤية التذاكر الموجّهة إلى فريقه" },
  "tickets:view_all": { en: "View all tickets", ar: "عرض كل التذاكر", den: "See every team's tickets", dar: "رؤية تذاكر جميع الفرق" },
  "tickets:create": { en: "Create tickets", ar: "إنشاء تذاكر", den: "Submit new tickets on a customer's behalf", dar: "إدخال تذاكر جديدة نيابةً عن العميل" },
  "tickets:review": { en: "Review AI drafts", ar: "مراجعة مسودات الذكاء الاصطناعي", den: "Approve, edit or reject replies", dar: "اعتماد الردود أو تعديلها أو رفضها" },
  "tickets:handle_escalated": { en: "Handle escalations", ar: "معالجة التصعيدات", den: "Act on escalated (P1, legal, safety…) tickets", dar: "التعامل مع التذاكر المُصعَّدة (عاجلة، قانونية، سلامة…)" },
  "tickets:reassign": { en: "Reassign tickets", ar: "إعادة إسناد التذاكر", den: "Move tickets between teams and agents", dar: "نقل التذاكر بين الفرق والموظفين" },
  "kb:manage": { en: "Edit knowledge base", ar: "تحرير قاعدة المعرفة", den: "Create and edit help articles the AI cites", dar: "إنشاء وتعديل المقالات التي يستشهد بها الذكاء الاصطناعي" },
  "settings:manage": { en: "Change settings & rules", ar: "تغيير الإعدادات والقواعد", den: "Thresholds, models and routing rules", dar: "الحدود والنماذج وقواعد التوجيه" },
  "users:manage": { en: "Manage users & roles", ar: "إدارة المستخدمين والأدوار", den: "Users, role permissions and teams", dar: "المستخدمون وصلاحيات الأدوار والفرق" },
  "analytics:view": { en: "View analytics", ar: "عرض التحليلات", den: "Dashboards and evaluation results", dar: "لوحات المؤشرات ونتائج التقييم" },
  "audit:view": { en: "View audit log", ar: "عرض سجل التدقيق", den: "Every sensitive action and who did it", dar: "كل إجراء حساس ومن قام به" },
};

export const PERMISSION_GROUPS: { id: string; label: L; perms: string[] }[] = [
  { id: "tickets", label: { en: "Tickets", ar: "التذاكر" }, perms: ["tickets:view", "tickets:view_all", "tickets:create", "tickets:review", "tickets:handle_escalated", "tickets:reassign"] },
  { id: "knowledge", label: { en: "Knowledge & insights", ar: "المعرفة والتحليلات" }, perms: ["kb:manage", "analytics:view"] },
  { id: "admin", label: { en: "Administration", ar: "الإدارة" }, perms: ["settings:manage", "users:manage", "audit:view"] },
];

export const ROLE_INFO: Record<string, LD> = {
  admin: { en: "Admin", ar: "مدير النظام", den: "Full access. Always has every permission.", dar: "صلاحيات كاملة دائماً، ولا يمكن تقييده." },
  lead: { en: "Team lead", ar: "قائد فريق", den: "Supervises queues, handles escalations, edits the knowledge base.", dar: "يشرف على قوائم العمل ويعالج التصعيدات ويحرّر قاعدة المعرفة." },
  agent: { en: "Agent", ar: "موظف دعم", den: "Reviews AI drafts for their team.", dar: "يراجع مسودات الذكاء الاصطناعي لفريقه." },
  analyst: { en: "Analyst", ar: "محلل", den: "Read-only access to tickets and analytics.", dar: "وصول للقراءة فقط إلى التذاكر والتحليلات." },
};

export const ROUTING_KEYS: Record<string, LD> = {
  safety: { en: "Safety hazard", ar: "خطر على السلامة", den: "Smoke, fire, swelling, overheating", dar: "دخان، حريق، انتفاخ، سخونة مفرطة" },
  legal: { en: "Legal threat", ar: "تهديد قانوني", den: "Lawyer, lawsuit, consumer protection, GDPR", dar: "محامٍ، دعوى، حماية المستهلك، حماية البيانات" },
  fraud: { en: "Fraud / hacked account", ar: "احتيال / اختراق حساب", den: "Unauthorized orders or access", dar: "طلبات أو دخول غير مصرّح به" },
  chargeback: { en: "Chargeback", ar: "اعتراض بنكي", den: "Customer disputes the payment with the bank", dar: "العميل يعترض على الدفع لدى البنك" },
  vip_customer: { en: "VIP customer", ar: "عميل من كبار العملاء", den: "Customer flagged VIP in the CRM", dar: "عميل مصنّف كبار العملاء في نظام العملاء" },
  very_negative_sentiment: { en: "Very angry customer", ar: "عميل غاضب جداً", den: "Very negative sentiment + anger cues", dar: "مشاعر سلبية جداً مع مؤشرات غضب" },
  refund_over_threshold: { en: "Large refund", ar: "استرداد كبير", den: "Refund above the configured limit", dar: "استرداد يتجاوز الحد المحدد" },
  priority_p1: { en: "Critical priority (P1)", ar: "أولوية حرجة (P1)" },
  reviewer_escalated: { en: "Escalated by reviewer", ar: "صعّدها المراجِع" },
  billing: { en: "Billing", ar: "الفوترة" }, refund: { en: "Refund", ar: "الاسترداد" }, shipping: { en: "Shipping", ar: "الشحن" },
  technical: { en: "Technical", ar: "تقني" }, account: { en: "Account", ar: "الحساب" }, other: { en: "Other", ar: "أخرى" },
};

export const ACTIONS: Record<string, L> = {
  send: { en: "Send", ar: "إرسال" }, human_review: { en: "Human review", ar: "مراجعة بشرية" }, escalate: { en: "Escalate", ar: "تصعيد" },
};
export const DECISIONS: Record<string, L> = {
  approve: { en: "Approved", ar: "اعتُمدت" }, edit: { en: "Edited & approved", ar: "عُدّلت واعتُمدت" },
  reject: { en: "Rejected", ar: "رُفضت" }, escalate: { en: "Escalated", ar: "صُعِّدت" },
};
export const ESC_SOURCES: Record<string, L> = {
  routing_rules: { en: "routing rules", ar: "قواعد التوجيه" }, agent: { en: "the AI agent", ar: "وكيل الذكاء الاصطناعي" },
  reviewer: { en: "a reviewer", ar: "مراجِع" },
};
export const SENTIMENTS: Record<string, L> = {
  very_negative: { en: "Very negative", ar: "سلبية جداً" }, negative: { en: "Negative", ar: "سلبية" },
  neutral: { en: "Neutral", ar: "محايدة" }, positive: { en: "Positive", ar: "إيجابية" },
};
export const LANGUAGES: Record<string, L> = {
  en: { en: "English", ar: "الإنجليزية" }, ar: { en: "Arabic", ar: "العربية" },
  mixed: { en: "Arabic + English", ar: "عربية + إنجليزية" }, ar_latn: { en: "Arabizi", ar: "عربيزي" },
  unknown: { en: "Not classified", ar: "غير مصنّفة" },
};

export const label = (m: Record<string, L>, k: string, lang: Lang) => pick(m, k, lang);
export const desc = (m: Record<string, LD>, k: string, lang: Lang) => (lang === "ar" ? m[k]?.dar : m[k]?.den) ?? "";
