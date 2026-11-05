"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

export type Lang = "en" | "ar";

const en = {
  appName: "Lumora Support Desk",
  // nav
  "nav.inbox": "Inbox", "nav.escalations": "Escalations", "nav.mine": "Assigned to me", "nav.kb": "Knowledge base",
  "nav.analytics": "Analytics", "nav.users": "Users & roles", "nav.audit": "Audit log", "nav.settings": "Settings",
  "nav.workspace": "Workspace", "nav.admin": "Administration",
  // auth
  "auth.title": "Sign in to your workspace", "auth.email": "Email", "auth.password": "Password",
  "auth.signIn": "Sign in", "auth.signOut": "Sign out", "auth.invalid": "Invalid email or password",
  "auth.demo": "Demo accounts", "auth.demoHint": "Password for all demo accounts:",
  "auth.tooMany": "Too many failed attempts. For your security, try again in 15 minutes.",
  // common
  "common.loading": "Loading…", "common.save": "Save", "common.cancel": "Cancel", "common.edit": "Edit",
  "common.create": "Create", "common.search": "Search…", "common.all": "All", "common.none": "None",
  "common.yes": "Yes", "common.no": "No", "common.saved": "Saved", "common.error": "Something went wrong",
  "common.refresh": "Refresh", "common.close": "Close", "common.language": "Language", "common.theme": "Theme",
  "common.light": "Light", "common.dark": "Dark", "common.noAccess": "You don't have access to this page.",
  "common.live": "Live", "common.offline": "Reconnecting…", "common.justNow": "just now", "common.ago": "ago",
  // status
  "status.new": "Processing", "status.triaged": "Processing", "status.in_review": "Needs review",
  "status.escalated": "Escalated", "status.ready_to_send": "Ready to send", "status.approved": "Approved",
  "status.rejected": "Rejected", "status.sent": "Sent",
  // categories
  "cat.billing": "Billing", "cat.shipping": "Shipping", "cat.technical": "Technical", "cat.account": "Account",
  "cat.refund": "Refund", "cat.other": "Other",
  // roles
  "role.admin": "Admin", "role.lead": "Team lead", "role.agent": "Agent", "role.analyst": "Analyst",
  // inbox
  "inbox.empty": "No tickets here.", "inbox.select": "Select a ticket to review it", "inbox.newTicket": "New ticket",
  "inbox.queued": "Ticket queued. The AI pipeline will process it shortly.",
  "inbox.kpi.total": "Tickets", "inbox.kpi.review": "Needs review", "inbox.kpi.escalated": "Escalated",
  "inbox.kpi.ready": "Ready to send", "inbox.kpi.latency": "Avg. processing",
  // ticket
  "ticket.from": "From", "ticket.via": "via", "ticket.team": "Team", "ticket.assignee": "Assignee",
  "ticket.unassigned": "Unassigned", "ticket.processing": "The AI pipeline is working on this ticket…",
  "ticket.tab.reply": "Reply", "ticket.tab.triage": "Triage & routing", "ticket.tab.trace": "Tool trace",
  "ticket.tab.context": "Context", "ticket.tab.history": "History",
  "ticket.confidence": "Confidence", "ticket.modelSaid": "model said", "ticket.recommends": "Recommends",
  "ticket.sources": "Sources", "ticket.noSources": "None cited", "ticket.whyReview": "Why it needs review",
  "ticket.guardrails": "Guardrails flagged", "ticket.replyPlaceholder": "Write a reply…",
  "ticket.note": "Note for the log (optional)", "ticket.approve": "Approve & send",
  "ticket.saveEdit": "Save edit & approve", "ticket.reject": "Reject", "ticket.escalate": "Escalate",
  "ticket.readOnly": "Your role can view this ticket but not act on it.",
  "ticket.escalatedLeadOnly": "Escalated tickets are handled by team leads.",
  "ticket.escalatedBy": "Escalated by", "ticket.noAgent": "Escalated before the AI agent ran — write the reply yourself.",
  "ticket.language": "Language", "ticket.category": "Category", "ticket.priority": "Priority",
  "ticket.sentiment": "Sentiment", "ticket.injection": "Prompt injection", "ticket.suspected": "Suspected",
  "ticket.signals": "Signals", "ticket.orders": "Order IDs", "ticket.amounts": "Amounts",
  "ticket.missing": "Missing info", "ticket.rules": "Routing rules", "ticket.noRules": "No escalation rule fired — the ticket went to the AI agent.",
  "ticket.prefetch": "Pipeline prefetch", "ticket.agentCall": "Agent", "ticket.llmCalls": "LLM calls",
  "ticket.cited": "cited", "ticket.helpArticle": "Help article", "ticket.pastTicket": "Past ticket",
  "ticket.reassign": "Reassign", "ticket.moveTo": "Move to team", "ticket.assignTo": "Assign to",
  "ticket.original": "AI draft", "ticket.sent": "Sent version", "ticket.reviewedBy": "by",
  // new ticket form
  "form.customerEmail": "Customer email", "form.subject": "Subject", "form.message": "Message",
  "form.channel": "Channel", "form.example": "Start from an example", "form.submit": "Submit ticket",
  // kb
  "kb.title": "Knowledge base", "kb.subtitle": "Policies the AI may cite. Edits are re-indexed instantly.",
  "kb.new": "New article", "kb.english": "English", "kb.arabic": "Arabic", "kb.titleField": "Title",
  "kb.body": "Body", "kb.category": "Category", "kb.id": "Article ID", "kb.missingAr": "No Arabic version",
  // analytics
  "an.title": "Analytics", "an.ops": "Operations", "an.eval": "Offline evaluation",
  "an.evalNone": "No evaluation results yet. Run: python -m evals.run_eval",
  "an.autoResolved": "Auto-resolved", "an.editRate": "Edit rate", "an.byTeam": "Tickets by team",
  "an.byLanguage": "By language", "an.byPriority": "By priority", "an.daily": "Daily volume",
  "an.reviews": "Review decisions", "an.catAcc": "Category accuracy", "an.priAcc": "Priority accuracy",
  "an.actionAcc": "Action accuracy", "an.escRecall": "Escalation recall", "an.escPrecision": "Escalation precision",
  "an.unsafe": "Unsafe auto-sends", "an.grounded": "Claims supported", "an.byLang": "English vs Arabic",
  "an.confusion": "Action confusion (rows = expected)", "an.byTag": "Accuracy by scenario",
  // users
  "users.title": "Users & roles", "users.new": "New user", "users.name": "Full name", "users.role": "Role",
  "users.team": "Team", "users.active": "Active", "users.lastLogin": "Last login", "users.never": "Never",
  "users.matrix": "Permissions by role", "users.password": "Password (min. 10 characters)",
  "users.deactivate": "Deactivate", "users.activate": "Activate",
  // audit
  "audit.title": "Audit log", "audit.when": "When", "audit.who": "Who", "audit.action": "Action",
  "audit.target": "Target", "audit.detail": "Detail",
  // settings
  "set.title": "Settings", "set.subtitle": "Applied to new tickets within seconds — no restart needed.",
  "set.refund": "Refund escalation threshold ($)", "set.refundHint": "Refunds above this amount always go to a human.",
  "set.conf": "Auto-send confidence", "set.confHint": "Drafts below this confidence go to review.",
  "set.neg": "Very-negative sentiment threshold", "set.negHint": "Combined with lexical anger cues to escalate.",
  "set.lowRisk": "Low-risk categories (eligible for auto-send)", "set.lowRiskHint": "Billing and refunds always get human review.",
  "set.autoSend": "Auto-send enabled", "set.autoSendHint": "Kill switch: when off, every AI draft goes to human review.",
  "set.triageModel": "Triage model", "set.agentModel": "Agent model", "set.default": "Default",
  // new ticket form
  "form.groupEnglish": "English tickets", "form.groupArabic": "Arabic tickets", "form.groupArabizi": "Arabizi tickets",
  "form.examplePlaceholder": "Search 66 sample tickets…",
  // queue cards
  "queue.review.hint": "AI drafted · waiting for your decision", "queue.escalated.hint": "Urgent · routed to a specialist",
  "queue.ready.hint": "Safe to send as drafted", "queue.processing.hint": "AI pipeline at work",
  "queue.done": "Done", "queue.done.hint": "Approved or rejected", "queue.all": "All tickets", "queue.all.hint": "Everything you can see",
  "inbox.searchList": "Search subject, email or ID…", "inbox.avgTime": "Avg. AI processing time",
  // admin
  "nav.roles": "Roles & permissions", "nav.teams": "Teams", "nav.routing": "Routing rules",
  "admin.title": "Administration",
  "roles.subtitle": "Choose what each role can do. Changes apply within seconds, no restart.",
  "roles.locked": "Admin always has full access", "roles.users": "active users", "roles.reset": "Reset to default",
  "roles.unsaved": "Unsaved changes", "roles.custom": "Customized",
  "teams.subtitle": "Queues that tickets are routed to.", "teams.new": "New team", "teams.nameEn": "Name (English)",
  "teams.nameAr": "Name (Arabic)", "teams.description": "Description", "teams.members": "Members",
  "teams.open": "Open tickets", "teams.inactive": "Inactive",
  "routing.subtitle": "Which team receives each kind of ticket. Checked top to bottom: the first match wins.",
  "routing.signals": "1 · Urgent signals", "routing.signalsHint": "Detected in the ticket text. These tickets are always escalated.",
  "routing.rules": "2 · Escalation rules", "routing.rulesHint": "Based on the customer, sentiment and refund amount.",
  "routing.categories": "3 · Everything else, by category", "routing.categoriesHint": "Default owner when nothing above matched.",
  "routing.thresholds": "Edit thresholds in Settings",
  "users.search": "Search users…", "users.allRoles": "All roles", "users.allTeams": "All teams", "users.you": "you",
  "users.subtitle": "People who can sign in, their role and their team.",
  // workflow & monitoring
  "nav.monitor": "Monitor", "ticket.tab.workflow": "Workflow",
  "wf.received": "Received", "wf.triage": "AI triage", "wf.routing": "Routing", "wf.draft": "AI draft",
  "wf.review": "Human review", "wf.resolved": "Resolved", "wf.escalated": "Escalated", "wf.skipped": "Skipped",
  "ev.received": "Ticket received", "ev.picked_up": "Picked up by the AI worker", "ev.failed": "Processing failed",
  "ev.ai_triage": "AI classified the ticket", "ev.ai_retrieve": "Knowledge base searched", "ev.ai_route": "Routing rules applied",
  "ev.ai_agent": "AI agent drafted a reply", "ev.ai_hitl": "Review gate decided", "ev.ai_escalate": "Escalation summary prepared",
  "ev.escalated": "Escalated", "ev.assigned": "Reassigned", "ev.reviewed": "Reviewed",
  "actor.ai": "AI", "actor.rules": "Rules", "actor.human": "Person", "actor.system": "System", "actor.customer": "Customer",
  "sla.on_track": "On track", "sla.at_risk": "At risk", "sla.breached": "Overdue", "sla.met": "SLA met", "sla.missed": "SLA missed",
  "sla.left": "left", "sla.over": "overdue", "sla.target": "Target", "sla.title": "SLA",
  "mon.subtitle": "Live view of the ticket workflow, SLAs and the AI pipeline.",
  "mon.open": "Open tickets", "mon.atRisk": "SLA at risk", "mon.breached": "Overdue", "mon.queue": "Waiting for AI",
  "mon.failed": "Failed jobs", "mon.flow": "Ticket flow", "mon.flowHint": "Where the AI sent each ticket, and how it ended",
  "mon.slaByPriority": "SLA by priority", "mon.atRiskList": "Needs attention now", "mon.pipeline": "AI pipeline health",
  "mon.stages": "Average time per stage", "mon.workload": "Team workload", "mon.activity": "Live activity",
  "mon.worker": "Worker", "mon.workerIdle": "Idle", "mon.workerBusy": "Processing", "mon.oldestWait": "Oldest waiting",
  "mon.lastDone": "Last completed", "mon.allGood": "Nothing at risk right now", "mon.oldest": "oldest",
  "mon.stage.triage": "Triage", "mon.stage.retrieve": "Retrieval", "mon.stage.route": "Routing", "mon.stage.agent": "AI agent",
  "mon.stage.hitl": "Review gate", "mon.stage.escalate": "Escalation",
  "flow.received": "Received", "flow.processing": "Processing", "flow.escalated": "Escalated", "flow.in_review": "Needs review",
  "flow.ready_to_send": "Auto-ready", "flow.approved": "Approved", "flow.edited": "Edited", "flow.rejected": "Rejected", "flow.open": "Still open",
  "act.received": "New ticket", "act.ai_done": "AI finished", "act.reviewed": "reviewed",
  "set.sla": "SLA targets (hours to resolve)", "set.slaHint": "Per priority. A ticket is “at risk” after 75% of its target.",
};

type Dict = typeof en;
export type TKey = keyof Dict;

// `satisfies Record<TKey, string>`: the build fails if any English key lacks an Arabic translation.
const ar = {
  appName: "مكتب دعم Lumora",
  "nav.inbox": "صندوق الوارد", "nav.escalations": "التصعيدات", "nav.mine": "المُسندة إليّ", "nav.kb": "قاعدة المعرفة",
  "nav.analytics": "التحليلات", "nav.users": "المستخدمون والأدوار", "nav.audit": "سجل التدقيق", "nav.settings": "الإعدادات",
  "nav.workspace": "مساحة العمل", "nav.admin": "الإدارة",
  "auth.title": "سجّل الدخول إلى مساحة العمل", "auth.email": "البريد الإلكتروني", "auth.password": "كلمة المرور",
  "auth.signIn": "تسجيل الدخول", "auth.signOut": "تسجيل الخروج", "auth.invalid": "البريد الإلكتروني أو كلمة المرور غير صحيحة",
  "auth.demo": "حسابات تجريبية", "auth.demoHint": "كلمة المرور لجميع الحسابات التجريبية:",
  "auth.tooMany": "محاولات فاشلة كثيرة. لحمايتك، حاول مجدداً بعد 15 دقيقة.",
  "common.loading": "جارٍ التحميل…", "common.save": "حفظ", "common.cancel": "إلغاء", "common.edit": "تعديل",
  "common.create": "إنشاء", "common.search": "بحث…", "common.all": "الكل", "common.none": "لا يوجد",
  "common.yes": "نعم", "common.no": "لا", "common.saved": "تم الحفظ", "common.error": "حدث خطأ ما",
  "common.refresh": "تحديث", "common.close": "إغلاق", "common.language": "اللغة", "common.theme": "المظهر",
  "common.light": "فاتح", "common.dark": "داكن", "common.noAccess": "ليست لديك صلاحية الوصول إلى هذه الصفحة.",
  "common.live": "مباشر", "common.offline": "جارٍ إعادة الاتصال…", "common.justNow": "الآن", "common.ago": "منذ",
  "status.new": "قيد المعالجة", "status.triaged": "قيد المعالجة", "status.in_review": "بحاجة لمراجعة",
  "status.escalated": "مُصعَّدة", "status.ready_to_send": "جاهزة للإرسال", "status.approved": "معتمدة",
  "status.rejected": "مرفوضة", "status.sent": "مُرسلة",
  "cat.billing": "الفوترة", "cat.shipping": "الشحن", "cat.technical": "تقني", "cat.account": "الحساب",
  "cat.refund": "استرداد", "cat.other": "أخرى",
  "role.admin": "مدير النظام", "role.lead": "قائد فريق", "role.agent": "موظف دعم", "role.analyst": "محلل",
  "inbox.empty": "لا توجد تذاكر هنا.", "inbox.select": "اختر تذكرة لمراجعتها", "inbox.newTicket": "تذكرة جديدة",
  "inbox.queued": "تمت إضافة التذكرة إلى قائمة الانتظار وستعالجها منظومة الذكاء الاصطناعي قريباً.",
  "inbox.kpi.total": "التذاكر", "inbox.kpi.review": "بحاجة لمراجعة", "inbox.kpi.escalated": "مُصعَّدة",
  "inbox.kpi.ready": "جاهزة للإرسال", "inbox.kpi.latency": "متوسط المعالجة",
  "ticket.from": "من", "ticket.via": "عبر", "ticket.team": "الفريق", "ticket.assignee": "المسؤول",
  "ticket.unassigned": "غير مُسندة", "ticket.processing": "منظومة الذكاء الاصطناعي تعالج هذه التذكرة…",
  "ticket.tab.reply": "الرد", "ticket.tab.triage": "التصنيف والتوجيه", "ticket.tab.trace": "سجل الأدوات",
  "ticket.tab.context": "السياق", "ticket.tab.history": "السجل",
  "ticket.confidence": "الثقة", "ticket.modelSaid": "تقدير النموذج", "ticket.recommends": "التوصية",
  "ticket.sources": "المصادر", "ticket.noSources": "لا مصادر", "ticket.whyReview": "سبب الحاجة للمراجعة",
  "ticket.guardrails": "تنبيهات الحماية", "ticket.replyPlaceholder": "اكتب رداً…",
  "ticket.note": "ملاحظة للسجل (اختياري)", "ticket.approve": "اعتماد وإرسال",
  "ticket.saveEdit": "حفظ التعديل واعتماد", "ticket.reject": "رفض", "ticket.escalate": "تصعيد",
  "ticket.readOnly": "يمكن لدورك عرض هذه التذكرة دون اتخاذ إجراء عليها.",
  "ticket.escalatedLeadOnly": "التذاكر المُصعَّدة يتولاها قادة الفرق.",
  "ticket.escalatedBy": "صُعِّدت بواسطة", "ticket.noAgent": "صُعِّدت قبل أن يعمل وكيل الذكاء الاصطناعي — اكتب الرد بنفسك.",
  "ticket.language": "اللغة", "ticket.category": "الفئة", "ticket.priority": "الأولوية",
  "ticket.sentiment": "المشاعر", "ticket.injection": "محاولة حقن أوامر", "ticket.suspected": "مشتبه بها",
  "ticket.signals": "الإشارات", "ticket.orders": "أرقام الطلبات", "ticket.amounts": "المبالغ",
  "ticket.missing": "معلومات ناقصة", "ticket.rules": "قواعد التوجيه", "ticket.noRules": "لم تنطبق أي قاعدة تصعيد — ذهبت التذكرة إلى وكيل الذكاء الاصطناعي.",
  "ticket.prefetch": "جلب مسبق من المنظومة", "ticket.agentCall": "الوكيل", "ticket.llmCalls": "استدعاءات النموذج",
  "ticket.cited": "مُستشهد به", "ticket.helpArticle": "مقال مساعدة", "ticket.pastTicket": "تذكرة سابقة",
  "ticket.reassign": "إعادة إسناد", "ticket.moveTo": "نقل إلى فريق", "ticket.assignTo": "إسناد إلى",
  "ticket.original": "مسودة الذكاء الاصطناعي", "ticket.sent": "النسخة المُرسلة", "ticket.reviewedBy": "بواسطة",
  "form.customerEmail": "بريد العميل", "form.subject": "الموضوع", "form.message": "الرسالة",
  "form.channel": "القناة", "form.example": "ابدأ من مثال", "form.submit": "إرسال التذكرة",
  "kb.title": "قاعدة المعرفة", "kb.subtitle": "السياسات التي يستشهد بها الذكاء الاصطناعي. تُفهرس التعديلات فوراً.",
  "kb.new": "مقال جديد", "kb.english": "الإنجليزية", "kb.arabic": "العربية", "kb.titleField": "العنوان",
  "kb.body": "المحتوى", "kb.category": "الفئة", "kb.id": "رقم المقال", "kb.missingAr": "لا توجد نسخة عربية",
  "an.title": "التحليلات", "an.ops": "التشغيل", "an.eval": "التقييم المسبق",
  "an.evalNone": "لا توجد نتائج تقييم بعد. شغّل: python -m evals.run_eval",
  "an.autoResolved": "حُلّت تلقائياً", "an.editRate": "نسبة التعديل", "an.byTeam": "التذاكر حسب الفريق",
  "an.byLanguage": "حسب اللغة", "an.byPriority": "حسب الأولوية", "an.daily": "الحجم اليومي",
  "an.reviews": "قرارات المراجعة", "an.catAcc": "دقة الفئة", "an.priAcc": "دقة الأولوية",
  "an.actionAcc": "دقة القرار", "an.escRecall": "استدعاء التصعيد", "an.escPrecision": "دقة التصعيد",
  "an.unsafe": "إرسال تلقائي غير آمن", "an.grounded": "ادعاءات موثّقة", "an.byLang": "الإنجليزية مقابل العربية",
  "an.confusion": "مصفوفة القرارات (الصفوف = المتوقع)", "an.byTag": "الدقة حسب السيناريو",
  "users.title": "المستخدمون والأدوار", "users.new": "مستخدم جديد", "users.name": "الاسم الكامل", "users.role": "الدور",
  "users.team": "الفريق", "users.active": "نشط", "users.lastLogin": "آخر دخول", "users.never": "أبداً",
  "users.matrix": "الصلاحيات حسب الدور", "users.password": "كلمة المرور (10 أحرف على الأقل)",
  "users.deactivate": "تعطيل", "users.activate": "تفعيل",
  "audit.title": "سجل التدقيق", "audit.when": "الوقت", "audit.who": "المستخدم", "audit.action": "الإجراء",
  "audit.target": "الهدف", "audit.detail": "التفاصيل",
  "set.title": "الإعدادات", "set.subtitle": "تُطبَّق على التذاكر الجديدة خلال ثوانٍ — دون إعادة تشغيل.",
  "set.refund": "حد تصعيد الاسترداد ($)", "set.refundHint": "الاستردادات التي تتجاوز هذا المبلغ تذهب دائماً إلى موظف.",
  "set.conf": "حد الثقة للإرسال التلقائي", "set.confHint": "المسودات الأقل ثقة تذهب إلى المراجعة.",
  "set.neg": "حد المشاعر السلبية جداً", "set.negHint": "يُدمج مع مؤشرات الغضب اللفظية للتصعيد.",
  "set.lowRisk": "الفئات منخفضة المخاطر (مؤهلة للإرسال التلقائي)", "set.lowRiskHint": "الفوترة والاسترداد تخضع دائماً لمراجعة بشرية.",
  "set.autoSend": "تفعيل الإرسال التلقائي", "set.autoSendHint": "مفتاح إيقاف: عند التعطيل تذهب كل المسودات إلى المراجعة البشرية.",
  "set.triageModel": "نموذج التصنيف", "set.agentModel": "نموذج الوكيل", "set.default": "الافتراضي",
  "form.groupEnglish": "تذاكر بالإنجليزية", "form.groupArabic": "تذاكر بالعربية", "form.groupArabizi": "تذاكر بالعربيزي",
  "form.examplePlaceholder": "ابحث في 66 تذكرة تجريبية…",
  "queue.review.hint": "صاغها الذكاء الاصطناعي · تنتظر قرارك", "queue.escalated.hint": "عاجلة · وُجّهت إلى مختص",
  "queue.ready.hint": "آمنة للإرسال كما صيغت", "queue.processing.hint": "قيد المعالجة الآلية",
  "queue.done": "منجزة", "queue.done.hint": "معتمدة أو مرفوضة", "queue.all": "كل التذاكر", "queue.all.hint": "كل ما يمكنك رؤيته",
  "inbox.searchList": "ابحث بالموضوع أو البريد أو الرقم…", "inbox.avgTime": "متوسط زمن المعالجة الآلية",
  "nav.roles": "الأدوار والصلاحيات", "nav.teams": "الفرق", "nav.routing": "قواعد التوجيه",
  "admin.title": "الإدارة",
  "roles.subtitle": "حدّد ما يمكن لكل دور القيام به. تُطبَّق التغييرات خلال ثوانٍ دون إعادة تشغيل.",
  "roles.locked": "لمدير النظام صلاحيات كاملة دائماً", "roles.users": "مستخدمين نشطين", "roles.reset": "استعادة الافتراضي",
  "roles.unsaved": "تغييرات غير محفوظة", "roles.custom": "مُعدّل",
  "teams.subtitle": "قوائم العمل التي تُوجَّه إليها التذاكر.", "teams.new": "فريق جديد", "teams.nameEn": "الاسم (بالإنجليزية)",
  "teams.nameAr": "الاسم (بالعربية)", "teams.description": "الوصف", "teams.members": "الأعضاء",
  "teams.open": "تذاكر مفتوحة", "teams.inactive": "غير نشط",
  "routing.subtitle": "أي فريق يستلم كل نوع من التذاكر. تُفحص القواعد من الأعلى إلى الأسفل ويُعتمد أول تطابق.",
  "routing.signals": "١ · إشارات عاجلة", "routing.signalsHint": "تُكتشف في نص التذكرة، وتُصعَّد هذه التذاكر دائماً.",
  "routing.rules": "٢ · قواعد التصعيد", "routing.rulesHint": "بناءً على العميل والمشاعر ومبلغ الاسترداد.",
  "routing.categories": "٣ · باقي التذاكر حسب الفئة", "routing.categoriesHint": "الفريق الافتراضي عندما لا ينطبق شيء مما سبق.",
  "routing.thresholds": "تعديل الحدود من الإعدادات",
  "users.search": "ابحث عن مستخدم…", "users.allRoles": "كل الأدوار", "users.allTeams": "كل الفرق", "users.you": "أنت",
  "users.subtitle": "الأشخاص الذين يمكنهم الدخول، وأدوارهم وفرقهم.",
  "nav.monitor": "المراقبة", "ticket.tab.workflow": "مسار العمل",
  "wf.received": "الاستلام", "wf.triage": "التصنيف الآلي", "wf.routing": "التوجيه", "wf.draft": "المسودة الآلية",
  "wf.review": "المراجعة البشرية", "wf.resolved": "الحل", "wf.escalated": "التصعيد", "wf.skipped": "تم تخطيها",
  "ev.received": "استُلمت التذكرة", "ev.picked_up": "التقطها معالج الذكاء الاصطناعي", "ev.failed": "فشلت المعالجة",
  "ev.ai_triage": "صنّف الذكاء الاصطناعي التذكرة", "ev.ai_retrieve": "البحث في قاعدة المعرفة", "ev.ai_route": "تطبيق قواعد التوجيه",
  "ev.ai_agent": "صاغ الوكيل الآلي رداً", "ev.ai_hitl": "قرار بوابة المراجعة", "ev.ai_escalate": "تجهيز ملخص التصعيد",
  "ev.escalated": "صُعِّدت", "ev.assigned": "أُعيد إسنادها", "ev.reviewed": "رُوجعت",
  "actor.ai": "الذكاء الاصطناعي", "actor.rules": "القواعد", "actor.human": "موظف", "actor.system": "النظام", "actor.customer": "العميل",
  "sla.on_track": "ضمن الوقت", "sla.at_risk": "معرّضة للتأخر", "sla.breached": "متأخرة", "sla.met": "ضمن الالتزام", "sla.missed": "تجاوزت الالتزام",
  "sla.left": "متبقٍ", "sla.over": "تأخير", "sla.target": "المستهدف", "sla.title": "الالتزام الزمني",
  "mon.subtitle": "عرض مباشر لمسار التذاكر والالتزام الزمني ومنظومة الذكاء الاصطناعي.",
  "mon.open": "تذاكر مفتوحة", "mon.atRisk": "معرّضة للتأخر", "mon.breached": "متأخرة", "mon.queue": "بانتظار المعالجة",
  "mon.failed": "مهام فاشلة", "mon.flow": "تدفق التذاكر", "mon.flowHint": "إلى أين أرسل الذكاء الاصطناعي كل تذكرة، وكيف انتهت",
  "mon.slaByPriority": "الالتزام حسب الأولوية", "mon.atRiskList": "تحتاج انتباهاً الآن", "mon.pipeline": "صحة منظومة الذكاء الاصطناعي",
  "mon.stages": "متوسط الوقت لكل مرحلة", "mon.workload": "عبء عمل الفرق", "mon.activity": "النشاط المباشر",
  "mon.worker": "المعالج", "mon.workerIdle": "خامل", "mon.workerBusy": "يعالج", "mon.oldestWait": "أقدم تذكرة منتظرة",
  "mon.lastDone": "آخر إنجاز", "mon.allGood": "لا توجد تذاكر معرّضة للتأخر حالياً", "mon.oldest": "الأقدم",
  "mon.stage.triage": "التصنيف", "mon.stage.retrieve": "الاسترجاع", "mon.stage.route": "التوجيه", "mon.stage.agent": "الوكيل الآلي",
  "mon.stage.hitl": "بوابة المراجعة", "mon.stage.escalate": "التصعيد",
  "flow.received": "المستلمة", "flow.processing": "قيد المعالجة", "flow.escalated": "مُصعَّدة", "flow.in_review": "بحاجة لمراجعة",
  "flow.ready_to_send": "جاهزة آلياً", "flow.approved": "معتمدة", "flow.edited": "معدّلة", "flow.rejected": "مرفوضة", "flow.open": "ما زالت مفتوحة",
  "act.received": "تذكرة جديدة", "act.ai_done": "أنهى الذكاء الاصطناعي", "act.reviewed": "راجع",
  "set.sla": "أهداف زمن الحل (بالساعات)", "set.slaHint": "لكل أولوية. تُعتبر التذكرة «معرّضة للتأخر» بعد مرور 75% من الوقت.",
} satisfies Record<TKey, string>;

const DICTS: Record<Lang, Record<TKey, string>> = { en, ar };

// Team names are data (stored in English); translate for display only.
const TEAM_AR: Record<string, string> = {
  "Product Safety": "سلامة المنتجات", "Legal & Compliance": "الشؤون القانونية والامتثال",
  "Account Security": "أمن الحسابات", "Billing Disputes": "نزاعات الفوترة", "VIP Care": "رعاية كبار العملاء",
  "Customer Care (Senior)": "خدمة العملاء (كبار الموظفين)", "Returns & Refunds": "الإرجاع والاسترداد",
  Billing: "الفوترة", Logistics: "الشحن والتوصيل", "Technical Support": "الدعم الفني",
  Accounts: "الحسابات", "Customer Care": "خدمة العملاء",
};

type Ctx = { lang: Lang; dir: "ltr" | "rtl"; t: (k: TKey) => string; team: (name?: string | null) => string;
  setLang: (l: Lang) => void };
const I18nContext = createContext<Ctx | null>(null);

export function I18nProvider({ initialLang, children }: { initialLang: Lang; children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    document.cookie = `lang=${l}; path=/; max-age=31536000; samesite=lax`; // server renders the right dir next time
    document.documentElement.lang = l;
    document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
  }, []);
  const value = useMemo<Ctx>(() => ({
    lang, dir: lang === "ar" ? "rtl" : "ltr", setLang,
    t: (k) => DICTS[lang][k] ?? k,
    team: (name) => (name ? (lang === "ar" ? TEAM_AR[name] ?? name : name) : "—"),
  }), [lang, setLang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}

export function timeAgo(iso: string, lang: Lang): string {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  const sec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto", style: "short" });
  if (sec < 60) return rtf.format(0, "second");
  if (sec < 3600) return rtf.format(-Math.floor(sec / 60), "minute");
  if (sec < 86400) return rtf.format(-Math.floor(sec / 3600), "hour");
  return rtf.format(-Math.floor(sec / 86400), "day");
}
