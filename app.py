import os
import json
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

st.set_page_config(page_title="Continuity Persona | استمرارية التقنية", page_icon="◈", layout="wide")

# -----------------------------
# Theme / copy
# -----------------------------
THEMES = {
    "Dark": {
        "bg": "#070A12", "card": "#101526", "card2": "#151C32", "text": "#F7F9FF",
        "muted": "#9CA8C7", "accent": "#7C5CFF", "accent2": "#20D6C7", "border": "#26314F"
    },
    "Light": {
        "bg": "#F7F8FC", "card": "#FFFFFF", "card2": "#F0F2FA", "text": "#111526",
        "muted": "#66708C", "accent": "#6D4AFF", "accent2": "#00AFA7", "border": "#DDE2F0"
    }
}

COPY = {
    "en": {
        "title": "Technology Continuity Profile",
        "subtitle": "A short interactive story that reveals how much control your organization keeps when technology relationships are tested.",
        "start": "Start profile",
        "language": "Language",
        "theme": "Theme",
        "next": "Continue",
        "back": "Back",
        "finish": "Reveal my profile",
        "result": "Your Technology Continuity Readiness",
        "persona": "Your continuity persona",
        "priority": "Priority area",
        "recommendation": "Recommended next step",
        "lead_contact": "Receive the detailed assessment",
        "name": "Name (optional)",
        "email": "Work email (optional)",
        "phone": "Mobile (optional)",
        "org": "Organization (optional)",
        "consent": "I agree that my submitted information may be used to contact me about this assessment and related services.",
        "save": "Save my assessment",
        "saved": "Assessment saved successfully.",
        "dashboard": "Insights Dashboard",
        "admin": "Team dashboard",
        "password": "Dashboard password",
        "open_dashboard": "Open dashboard",
        "explorer_title": "The Explorer",
        "explorer_msg": "You are exploring the topic rather than representing an active organizational need today. Explore how technology continuity protects critical digital assets and relationships.",
        "explore_rec": "Explore Technology Continuity",
    },
    "ar": {
        "title": "ملف استمرارية التقنية",
        "subtitle": "قصة تفاعلية قصيرة تكشف مدى بقاء السيطرة بيد جهتك عندما تتعرض العلاقة التقنية للاختبار.",
        "start": "ابدأ التقييم",
        "language": "اللغة",
        "theme": "المظهر",
        "next": "متابعة",
        "back": "رجوع",
        "finish": "اعرض ملفي",
        "result": "درجة جاهزية استمرارية التقنية",
        "persona": "شخصية الاستمرارية لديك",
        "priority": "منطقة الأولوية",
        "recommendation": "الخطوة الموصى بها",
        "lead_contact": "احصل على التقييم التفصيلي",
        "name": "الاسم (اختياري)",
        "email": "البريد المهني (اختياري)",
        "phone": "رقم الجوال (اختياري)",
        "org": "اسم الجهة (اختياري)",
        "consent": "أوافق على استخدام البيانات التي أرسلتها للتواصل معي بشأن هذا التقييم والخدمات المرتبطة به.",
        "save": "احفظ تقييمي",
        "saved": "تم حفظ التقييم بنجاح.",
        "dashboard": "لوحة المؤشرات",
        "admin": "لوحة فريق العمل",
        "password": "كلمة مرور لوحة المؤشرات",
        "open_dashboard": "فتح اللوحة",
        "explorer_title": "المستكشف",
        "explorer_msg": "أنت تستكشف الموضوع حاليًا أكثر من تمثيل احتياج مؤسسي مباشر. يمكنك التعرف على كيفية حماية استمرارية التقنية للأصول والعلاقات الرقمية الحرجة.",
        "explore_rec": "استكشف استمرارية التقنية",
    }
}

# -----------------------------
# Question model
# score: readiness dimensions where 100 = strong readiness
# eligibility/need/influence/fit: hidden commercial scoring
# -----------------------------
QUESTIONS = [
    {
        "id": "representation", "paths": ["all"],
        "en": "What best describes what brings you here today?",
        "ar": "ما الذي يصف سبب زيارتك اليوم بشكل أفضل؟",
        "options": [
            {"id":"org", "en":"I represent an organization that uses or procures technology", "ar":"أمثل جهة تستخدم أو تشتري حلولًا تقنية", "eligibility":30, "route":"client"},
            {"id":"provider", "en":"We build or provide technology solutions to organizations", "ar":"نمثل شركة تطور أو تقدم حلولًا تقنية للجهات", "eligibility":26, "route":"provider"},
            {"id":"both", "en":"We both use and provide technology solutions", "ar":"نستخدم ونقدم حلولًا تقنية في الوقت نفسه", "eligibility":30, "route":"hybrid"},
            {"id":"advisor", "en":"I advise organizations on technology, contracts or risk", "ar":"أقدم استشارات للجهات في التقنية أو العقود أو المخاطر", "eligibility":20, "route":"advisor"},
            {"id":"self", "en":"I am exploring for myself / general interest", "ar":"أستكشف الموضوع لنفسي / اهتمام عام", "eligibility":0, "route":"explorer"},
        ]
    },
    {
        "id":"influence", "paths":["client","provider","hybrid","advisor"],
        "en":"When an important technology decision is being made, where are you usually involved?",
        "ar":"عند اتخاذ قرار تقني مهم، أين يكون دورك عادة؟",
        "options":[
            {"id":"approve","en":"I approve or sponsor the decision","ar":"أعتمد القرار أو أرعاه", "influence":25},
            {"id":"evaluate","en":"I evaluate options and shape the decision","ar":"أقيّم الخيارات وأؤثر في القرار", "influence":20},
            {"id":"manage","en":"I manage implementation, operations or vendors","ar":"أدير التنفيذ أو التشغيل أو الموردين", "influence":16},
            {"id":"use","en":"I mainly use the systems","ar":"أستخدم الأنظمة بشكل أساسي", "influence":5},
            {"id":"indirect","en":"I am not directly involved","ar":"لست مشاركًا بشكل مباشر", "influence":0},
        ]
    },
    {
        "id":"org_scale", "paths":["client","provider","hybrid","advisor"],
        "en":"Which environment is closest to the organization you are representing?",
        "ar":"أي بيئة هي الأقرب للجهة التي تمثلها؟",
        "options":[
            {"id":"gov","en":"Government / public sector","ar":"جهة حكومية / قطاع عام", "fit":20},
            {"id":"large","en":"Large private enterprise","ar":"منشأة خاصة كبيرة", "fit":20},
            {"id":"mid","en":"Mid-sized organization","ar":"منشأة متوسطة", "fit":14},
            {"id":"startup","en":"Startup / small business","ar":"شركة ناشئة / منشأة صغيرة", "fit":7},
            {"id":"individual","en":"I am not representing an organization","ar":"لا أمثل جهة", "fit":0},
        ]
    },
    {
        "id":"criticality", "paths":["client","hybrid","advisor"],
        "en":"A critical digital service becomes unavailable at 9:00 AM. When does it become a serious business issue?",
        "ar":"توقفت خدمة رقمية حرجة الساعة 9 صباحًا. متى يصبح التوقف مشكلة فعلية للأعمال؟",
        "options":[
            {"id":"minutes","en":"Within minutes","ar":"خلال دقائق", "business_criticality":100, "need":22},
            {"id":"hours","en":"Within a few hours","ar":"خلال ساعات قليلة", "business_criticality":85, "need":18},
            {"id":"day","en":"By the end of the day","ar":"بنهاية اليوم", "business_criticality":65, "need":13},
            {"id":"days","en":"After several days","ar":"بعد عدة أيام", "business_criticality":35, "need":6},
            {"id":"minimal","en":"The impact would be limited","ar":"التأثير سيكون محدودًا", "business_criticality":10, "need":1},
        ]
    },
    {
        "id":"provider_disruption", "paths":["client","hybrid","advisor"],
        "en":"Tomorrow morning, one of your key technology providers is unreachable. What is most likely to happen first?",
        "ar":"صباح الغد تعذر الوصول إلى أحد الموردين التقنيين الرئيسيين. ما السيناريو الأقرب لما سيحدث أولًا؟",
        "options":[
            {"id":"internal","en":"Our team continues using assets and procedures already under our control","ar":"يستمر فريقنا باستخدام الأصول والإجراءات الموجودة تحت سيطرتنا", "continuity":95, "asset_control":90, "need":2},
            {"id":"arrangement","en":"We activate a predefined continuity arrangement","ar":"نفعّل ترتيب استمرارية محدد مسبقًا", "continuity":85, "asset_control":80, "need":5},
            {"id":"alternate","en":"We coordinate with another provider to restore operations","ar":"نتواصل مع مزود بديل لاستعادة التشغيل", "continuity":65, "asset_control":60, "need":10},
            {"id":"wait","en":"We need the existing provider before we can fully recover","ar":"نحتاج المورد الحالي قبل أن نستعيد التشغيل بالكامل", "continuity":30, "asset_control":35, "need":20},
            {"id":"unknown","en":"I am not sure what would happen","ar":"لست متأكدًا مما سيحدث", "continuity":20, "asset_control":25, "need":22},
        ]
    },
    {
        "id":"handover", "paths":["client","hybrid","advisor"],
        "en":"A new technical team takes over a critical system next week. How complete would the handover package be today?",
        "ar":"سيتولى فريق تقني جديد نظامًا حرجًا الأسبوع القادم. ما مدى اكتمال حزمة التسليم المتوفرة اليوم؟",
        "options":[
            {"id":"complete","en":"Complete: code, data, documentation, access and deployment details are available","ar":"مكتملة: الكود والبيانات والتوثيق والصلاحيات وتفاصيل النشر متوفرة", "asset_control":100, "exit_readiness":95, "need":1},
            {"id":"mostly","en":"Mostly complete, with a few provider dependencies","ar":"مكتملة إلى حد كبير مع بعض الاعتماد على المورد", "asset_control":75, "exit_readiness":75, "need":7},
            {"id":"partial","en":"Partial; significant coordination would still be required","ar":"جزئية؛ وسنحتاج تنسيقًا كبيرًا لاستكمالها", "asset_control":50, "exit_readiness":45, "need":14},
            {"id":"obtain","en":"Key assets would need to be obtained from the current provider","ar":"سنحتاج الحصول على أصول أساسية من المورد الحالي", "asset_control":25, "exit_readiness":25, "need":21},
            {"id":"unknown","en":"I am not sure what is available","ar":"لست متأكدًا مما هو متوفر", "asset_control":20, "exit_readiness":20, "need":22},
        ]
    },
    {
        "id":"exit", "paths":["client","hybrid","advisor"],
        "en":"If a technology relationship ends, which outcome is closest to your current reality?",
        "ar":"إذا انتهت العلاقة مع مورد تقني، أي نتيجة هي الأقرب لواقعكم الحالي؟",
        "options":[
            {"id":"predefined","en":"Transition steps, responsibilities and access rights are predefined","ar":"خطوات الانتقال والمسؤوليات وحقوق الوصول محددة مسبقًا", "exit_readiness":100, "contract_clarity":95, "need":1},
            {"id":"general","en":"The agreement provides general transition guidance","ar":"الاتفاقية توفر توجيهًا عامًا للانتقال", "exit_readiness":70, "contract_clarity":70, "need":7},
            {"id":"negotiate","en":"The parties would agree on transition arrangements when needed","ar":"سيتم الاتفاق على ترتيبات الانتقال عند الحاجة", "exit_readiness":45, "contract_clarity":45, "need":14},
            {"id":"provider","en":"The transition depends heavily on the provider","ar":"يعتمد الانتقال بدرجة كبيرة على المورد", "exit_readiness":25, "contract_clarity":30, "need":21},
            {"id":"unknown","en":"I am not sure","ar":"لست متأكدًا", "exit_readiness":20, "contract_clarity":20, "need":22},
        ]
    },
    {
        "id":"assurance", "paths":["provider","hybrid"],
        "en":"A prospective client asks, “How do we stay protected if your company cannot support the system?” What can you demonstrate today?",
        "ar":"سألك عميل محتمل: «كيف نبقى محميين إذا تعذر على شركتكم دعم النظام؟» ماذا تستطيعون إثباته اليوم؟",
        "options":[
            {"id":"independent","en":"Independent safeguards, documented handover and controlled asset access","ar":"ضمانات مستقلة وتسليم موثق ووصول منضبط للأصول", "continuity":95, "asset_control":95, "provider_assurance":100, "need":2},
            {"id":"internal","en":"Strong internal processes and documented commitments","ar":"إجراءات داخلية قوية والتزامات موثقة", "continuity":75, "asset_control":75, "provider_assurance":75, "need":7},
            {"id":"contract","en":"Mainly contractual commitments","ar":"نعتمد بشكل أساسي على الالتزامات التعاقدية", "continuity":55, "asset_control":55, "provider_assurance":50, "need":13},
            {"id":"ad_hoc","en":"We would arrange the handover if the situation occurs","ar":"سنرتب التسليم إذا حدث الموقف", "continuity":35, "asset_control":35, "provider_assurance":30, "need":19},
            {"id":"unsure","en":"I am not sure how we would demonstrate this","ar":"لست متأكدًا كيف سنثبت ذلك", "continuity":25, "asset_control":25, "provider_assurance":20, "need":21},
        ]
    },
    {
        "id":"client_request", "paths":["provider","hybrid"],
        "en":"When enterprise clients ask about code, data, backups or continuity protections, what usually happens?",
        "ar":"عندما يسأل عملاء المؤسسات عن حماية الكود أو البيانات أو النسخ الاحتياطية أو الاستمرارية، ما الذي يحدث عادة؟",
        "options":[
            {"id":"standard","en":"We have a standard, ready-to-share assurance package","ar":"لدينا حزمة ضمان قياسية وجاهزة للمشاركة", "provider_assurance":100, "contract_clarity":90, "need":2},
            {"id":"custom","en":"We prepare the evidence for each client","ar":"نجهز الإثباتات حسب كل عميل", "provider_assurance":70, "contract_clarity":70, "need":8},
            {"id":"legal","en":"It becomes a contract/legal negotiation","ar":"يتحول الأمر إلى تفاوض تعاقدي/قانوني", "provider_assurance":50, "contract_clarity":55, "need":13},
            {"id":"friction","en":"It often slows down the deal or creates concern","ar":"غالبًا يؤخر الصفقة أو يسبب قلقًا للعميل", "provider_assurance":30, "contract_clarity":40, "need":20},
            {"id":"rare","en":"Clients rarely ask about it","ar":"نادرًا ما يسأل العملاء عنه", "provider_assurance":45, "contract_clarity":45, "need":12},
        ]
    },
    {
        "id":"change_test", "paths":["client","provider","hybrid","advisor"],
        "en":"If you had to prove continuity readiness to leadership or a client tomorrow, how quickly could you do it?",
        "ar":"لو طُلب منكم غدًا إثبات جاهزية الاستمرارية للإدارة أو لأحد العملاء، كم ستحتاجون؟",
        "options":[
            {"id":"immediate","en":"Immediately — evidence is organized and current","ar":"فورًا — الأدلة منظمة ومحدثة", "governance":100, "need":1},
            {"id":"day","en":"Within a day","ar":"خلال يوم", "governance":80, "need":5},
            {"id":"week","en":"Within a week","ar":"خلال أسبوع", "governance":60, "need":10},
            {"id":"effort","en":"It would require a significant effort","ar":"سيتطلب جهدًا كبيرًا", "governance":35, "need":17},
            {"id":"unknown","en":"I do not know where to start","ar":"لا أعرف من أين أبدأ", "governance":20, "need":21},
        ]
    },
]

DIMENSION_WEIGHTS_CLIENT = {
    "asset_control": 0.25,
    "continuity": 0.23,
    "exit_readiness": 0.18,
    "contract_clarity": 0.14,
    "governance": 0.10,
    "business_criticality_inverse": 0.10,
}
DIMENSION_WEIGHTS_PROVIDER = {
    "provider_assurance": 0.30,
    "asset_control": 0.20,
    "continuity": 0.20,
    "contract_clarity": 0.15,
    "governance": 0.15,
}

PERSONAS = {
    "resilient": {
        "en":"The Resilient Guardian", "ar":"الحارس المرن",
        "en_desc":"Strong control, continuity and transition readiness. Your priority is validating and sustaining resilience.",
        "ar_desc":"سيطرة قوية وجاهزية مرتفعة للاستمرارية والانتقال. الأولوية هي التحقق المستمر والمحافظة على المرونة.",
        "service_en":"Resilience Validation & Independent Assurance", "service_ar":"التحقق من المرونة والضمان المستقل"
    },
    "managed": {
        "en":"The Managed Dependency", "ar":"الاعتماد المُدار",
        "en_desc":"Your environment is generally prepared, with selected dependencies that deserve stronger safeguards.",
        "ar_desc":"بيئتكم مستعدة بشكل جيد عمومًا، مع بعض نقاط الاعتماد التي تحتاج ضمانات أقوى.",
        "service_en":"Dependency & Continuity Review", "service_ar":"مراجعة الاعتماد واستمرارية التقنية"
    },
    "exposed": {
        "en":"The Exposed Operator", "ar":"المشغّل المعرّض",
        "en_desc":"Operations are functioning, but disruption or transition could expose material gaps in access, handover or agreements.",
        "ar_desc":"التشغيل قائم، لكن التعطل أو الانتقال قد يكشف فجوات مهمة في الوصول أو التسليم أو الاتفاقيات.",
        "service_en":"Technology Continuity Assessment", "service_ar":"تقييم استمرارية التقنية"
    },
    "critical": {
        "en":"The Critical Dependency", "ar":"الاعتماد الحرج",
        "en_desc":"Critical technology relationships show high dependency and limited recovery or exit readiness.",
        "ar_desc":"العلاقات التقنية الحرجة تظهر اعتمادًا مرتفعًا وجاهزية محدودة للتعافي أو الانتقال.",
        "service_en":"Priority Continuity, Escrow & Contract Risk Assessment", "service_ar":"تقييم عاجل للاستمرارية وحفظ الأصول ومخاطر العقود"
    },
    "provider_ready": {
        "en":"The Trusted Provider", "ar":"المزوّد الموثوق",
        "en_desc":"You can demonstrate continuity and client assurance with strong evidence and controls.",
        "ar_desc":"لديكم قدرة قوية على إثبات الاستمرارية وضمان العملاء بأدلة وضوابط واضحة.",
        "service_en":"Independent Assurance & Trust Validation", "service_ar":"الضمان المستقل والتحقق من الثقة"
    },
    "provider_growth": {
        "en":"The Trust Builder", "ar":"باني الثقة",
        "en_desc":"Your solution is viable, while stronger independent continuity safeguards could reduce enterprise buying friction.",
        "ar_desc":"حلولكم قوية، لكن تعزيز ضمانات الاستمرارية المستقلة قد يقلل تردد عملاء المؤسسات ويسرّع التعاقد.",
        "service_en":"Provider Assurance & Escrow Readiness", "service_ar":"جاهزية ضمان المزوّد وحفظ الأصول"
    },
}

# -----------------------------
# Helpers
# -----------------------------
def t(key):
    return COPY[st.session_state.lang][key]

def inject_css(theme_name, lang):
    c = THEMES[theme_name]
    direction = "rtl" if lang == "ar" else "ltr"
    align = "right" if lang == "ar" else "left"
    st.markdown(f"""
    <style>
    .stApp {{ background: {c['bg']}; color: {c['text']}; }}
    html, body, [class*="css"] {{ direction: {direction}; }}
    .block-container {{ max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem; }}
    h1,h2,h3,p,div,label {{ text-align: {align}; }}
    .hero {{ padding: 38px; border: 1px solid {c['border']}; border-radius: 28px;
             background: linear-gradient(135deg, {c['card']} 0%, {c['card2']} 100%); margin-bottom: 18px; }}
    .eyebrow {{ color: {c['accent2']}; font-weight: 800; letter-spacing: .08em; font-size: .78rem; text-transform: uppercase; }}
    .hero h1 {{ margin: .35rem 0 .45rem 0; font-size: 2.5rem; }}
    .muted {{ color: {c['muted']}; font-size: 1.05rem; }}
    .score-card {{ border: 1px solid {c['border']}; border-radius: 28px; background: {c['card']}; padding: 30px; }}
    .score {{ font-size: 5rem; line-height: 1; font-weight: 900; background: linear-gradient(90deg, {c['accent']}, {c['accent2']});
              -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .persona {{ font-size: 1.7rem; font-weight: 850; margin-top: 8px; }}
    .pill {{ display:inline-block; padding:7px 12px; border-radius:999px; border:1px solid {c['border']}; color:{c['accent2']}; margin:4px; }}
    div[data-testid="stMetric"] {{ background:{c['card']}; border:1px solid {c['border']}; padding:14px; border-radius:20px; }}
    div[data-baseweb="radio"] > div {{ gap: 10px; }}
    div[data-testid="stRadio"] label {{ border: 1px solid {c['border']}; border-radius: 16px; padding: 11px 14px; background:{c['card']}; }}
    .stButton > button {{ border-radius: 14px; min-height: 48px; font-weight: 750; border: 0;
                          background: linear-gradient(90deg, {c['accent']}, {c['accent2']}); color:white; }}
    .small-note {{ color:{c['muted']}; font-size:.82rem; }}
    </style>
    """, unsafe_allow_html=True)

def visible_questions(route):
    return [q for q in QUESTIONS if "all" in q["paths"] or route in q["paths"]]

def get_option(question, option_id):
    return next((o for o in question["options"] if o["id"] == option_id), None)

def average_metric(selected_options, metric, default=55):
    vals = [o[metric] for o in selected_options if metric in o]
    return round(sum(vals) / len(vals), 1) if vals else default

def calculate_scores(answers):
    selected = []
    for q in QUESTIONS:
        if q["id"] in answers:
            opt = get_option(q, answers[q["id"]])
            if opt:
                selected.append(opt)

    route = next((o.get("route") for o in selected if o.get("route")), "explorer")
    eligibility = min(100, sum(o.get("eligibility",0) for o in selected) + sum(o.get("fit",0) for o in selected) + sum(o.get("influence",0) for o in selected))
    influence = min(100, sum(o.get("influence",0) for o in selected) * 4)
    fit = min(100, sum(o.get("fit",0) for o in selected) * 5)
    raw_need = sum(o.get("need",0) for o in selected)
    need = min(100, round(raw_need / max(1, len([o for o in selected if "need" in o])) * (100/22)))

    dims = {
        "asset_control": average_metric(selected, "asset_control"),
        "continuity": average_metric(selected, "continuity"),
        "exit_readiness": average_metric(selected, "exit_readiness"),
        "contract_clarity": average_metric(selected, "contract_clarity"),
        "governance": average_metric(selected, "governance"),
        "business_criticality": average_metric(selected, "business_criticality", 50),
        "provider_assurance": average_metric(selected, "provider_assurance", 55),
    }

    if route in ["provider"]:
        readiness = sum(dims[k] * w for k,w in DIMENSION_WEIGHTS_PROVIDER.items())
    else:
        readiness = (
            dims["asset_control"]*0.25 + dims["continuity"]*0.23 + dims["exit_readiness"]*0.18 +
            dims["contract_clarity"]*0.14 + dims["governance"]*0.10 + (100-dims["business_criticality"])*0.10
        )
    readiness = max(0, min(100, round(readiness)))

    # Commercial score is deliberately distinct from visitor-facing readiness.
    commercial = round(
        0.36*need + 0.20*eligibility + 0.16*influence + 0.13*fit +
        0.15*(100-readiness)
    )
    commercial = max(0, min(100, commercial))

    if route == "explorer" or eligibility < 20:
        opportunity = "General Visitor"
    elif route in ["provider", "advisor"] and commercial < 65:
        opportunity = "Ecosystem Opportunity"
    elif commercial >= 75:
        opportunity = "Priority Opportunity"
    elif commercial >= 55:
        opportunity = "Qualified Opportunity"
    else:
        opportunity = "Nurture"

    if route == "provider":
        persona_key = "provider_ready" if readiness >= 75 else "provider_growth"
    else:
        if readiness >= 80: persona_key = "resilient"
        elif readiness >= 65: persona_key = "managed"
        elif readiness >= 45: persona_key = "exposed"
        else: persona_key = "critical"

    # Most vulnerable readiness dimension
    priority_map = {
        "asset_control": ("Technology Asset Control", "السيطرة على الأصول التقنية"),
        "continuity": ("Continuity Recovery", "التعافي واستمرارية التشغيل"),
        "exit_readiness": ("Exit & Transition Readiness", "جاهزية الخروج والانتقال"),
        "contract_clarity": ("Contract Continuity Clarity", "وضوح الاستمرارية في العقود"),
        "governance": ("Evidence & Governance", "الحوكمة والأدلة"),
        "provider_assurance": ("Client Assurance", "ضمان العملاء"),
    }
    priority_candidates = ["provider_assurance","asset_control","continuity","contract_clarity","governance"] if route == "provider" else ["asset_control","continuity","exit_readiness","contract_clarity","governance"]
    priority_key = min(priority_candidates, key=lambda k: dims[k])

    return {
        "route": route, "readiness": readiness, "need": need, "eligibility": eligibility,
        "influence": influence, "fit": fit, "commercial": commercial, "opportunity": opportunity,
        "persona_key": persona_key, "priority_key": priority_key, "dimensions": dims,
        "priority_en": priority_map[priority_key][0], "priority_ar": priority_map[priority_key][1],
    }

def google_client():
    if gspread is None:
        return None
    try:
        creds_info = st.secrets.get("gcp_service_account", None)
        sheet_name = st.secrets.get("GOOGLE_SHEET_NAME", "Technology Continuity Leads")
        if not creds_info:
            return None
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(dict(creds_info), scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open(sheet_name)
        return sh
    except Exception:
        return None

def flatten_record(scores, answers, contact):
    dims = scores["dimensions"]
    rep = answers.get("representation", "")
    orgscale = answers.get("org_scale", "")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.session_id,
        "language": st.session_state.lang,
        "theme": st.session_state.theme,
        "route": scores["route"],
        "representation": rep,
        "org_scale": orgscale,
        "persona": scores["persona_key"],
        "readiness_score": scores["readiness"],
        "service_need_pct": scores["need"],
        "eligibility_score": scores["eligibility"],
        "decision_influence_score": scores["influence"],
        "organization_fit_score": scores["fit"],
        "commercial_opportunity_score": scores["commercial"],
        "opportunity_class": scores["opportunity"],
        "priority_area": scores["priority_key"],
        "asset_control": dims["asset_control"],
        "continuity": dims["continuity"],
        "exit_readiness": dims["exit_readiness"],
        "contract_clarity": dims["contract_clarity"],
        "governance": dims["governance"],
        "business_criticality": dims["business_criticality"],
        "provider_assurance": dims["provider_assurance"],
        "name": contact.get("name", ""),
        "organization": contact.get("organization", ""),
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
        "consent": bool(contact.get("consent", False)),
        "answers_json": json.dumps(answers, ensure_ascii=False),
    }

def save_record(record):
    sh = google_client()
    if sh:
        try:
            ws = sh.worksheet("Responses")
        except Exception:
            ws = sh.add_worksheet(title="Responses", rows=2000, cols=40)
        existing = ws.get_all_values()
        headers = list(record.keys())
        if not existing:
            ws.append_row(headers)
        elif existing[0] != headers:
            # Preserve existing data, append any new headers.
            current = existing[0]
            for h in headers:
                if h not in current:
                    current.append(h)
            ws.update("1:1", [current])
            headers = current
        row = [record.get(h, "") for h in headers]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return "google"

    # Local fallback for development only
    path = "responses_local.csv"
    df = pd.DataFrame([record])
    if os.path.exists(path):
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, index=False)
    return "local"

def load_data():
    sh = google_client()
    if sh:
        try:
            ws = sh.worksheet("Responses")
            rows = ws.get_all_records()
            return pd.DataFrame(rows)
        except Exception:
            pass
    path = "responses_local.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def persona_label(key, lang="en"):
    if key in PERSONAS:
        return PERSONAS[key][lang]
    return key

def reset_assessment():
    keep = {"lang": st.session_state.lang, "theme": st.session_state.theme, "session_id": str(uuid.uuid4())}
    st.session_state.clear()
    for k,v in keep.items(): st.session_state[k] = v
    st.session_state.page = "intro"
    st.session_state.answers = {}
    st.session_state.q_index = 0

# -----------------------------
# State
# -----------------------------
if "lang" not in st.session_state: st.session_state.lang = "en"
if "theme" not in st.session_state: st.session_state.theme = "Dark"
if "page" not in st.session_state: st.session_state.page = "intro"
if "answers" not in st.session_state: st.session_state.answers = {}
if "q_index" not in st.session_state: st.session_state.q_index = 0
if "session_id" not in st.session_state: st.session_state.session_id = str(uuid.uuid4())

# Sidebar controls
with st.sidebar:
    st.session_state.lang = st.selectbox("Language / اللغة", ["en","ar"], index=0 if st.session_state.lang=="en" else 1, format_func=lambda x: "English" if x=="en" else "العربية")
    st.session_state.theme = st.selectbox("Theme / المظهر", ["Dark","Light"], index=0 if st.session_state.theme=="Dark" else 1)
    st.divider()
    if st.button(t("admin"), use_container_width=True):
        st.session_state.page = "dashboard_login"
        st.rerun()

inject_css(st.session_state.theme, st.session_state.lang)
lang = st.session_state.lang

# -----------------------------
# Intro
# -----------------------------
if st.session_state.page == "intro":
    st.markdown(f"""
    <div class="hero">
      <div class="eyebrow">CONTINUITY INTELLIGENCE</div>
      <h1>{t('title')}</h1>
      <div class="muted">{t('subtitle')}</div>
    </div>
    """, unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    labels = [
        ("2 MIN", "Smart diagnostic" if lang=="en" else "تشخيص ذكي"),
        ("100", "Readiness score" if lang=="en" else "درجة جاهزية"),
        ("1", "Personalized recommendation" if lang=="en" else "توصية مخصصة"),
    ]
    for c,(a,b) in zip([c1,c2,c3],labels):
        with c: st.metric(b, a)
    st.markdown(f"""
    <div class="score-card">
      <div class="eyebrow">{"THE STORY BEGINS" if lang=="en" else "تبدأ القصة"}</div>
      <div class="persona">{"Everything is working. Until one link suddenly isn't." if lang=="en" else "كل شيء يعمل... إلى أن تتوقف فجأة حلقة واحدة."}</div>
      <p class="muted">{"Your systems are live, your provider is responsive, and operations feel under control. Now imagine tomorrow changes one assumption. Walk through a few moments and discover what your organization can truly rely on." if lang=="en" else "أنظمتك تعمل، والمورد متجاوب، والتشغيل يبدو تحت السيطرة. تخيّل أن الغد غيّر افتراضًا واحدًا فقط. مرّ معنا عبر عدة مواقف واكتشف ما الذي تستطيع جهتك الاعتماد عليه فعلًا."}</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    if st.button(t("start"), use_container_width=True):
        st.session_state.page = "assessment"
        st.rerun()

# -----------------------------
# Assessment: one scenario per screen
# -----------------------------
elif st.session_state.page == "assessment":
    route = "all"
    rep = st.session_state.answers.get("representation")
    if rep:
        route = get_option(QUESTIONS[0], rep).get("route", "explorer")
        if route == "explorer":
            st.session_state.page = "explorer_result"
            st.rerun()

    qs = visible_questions(route)
    idx = min(st.session_state.q_index, len(qs)-1)
    q = qs[idx]
    progress = (idx+1)/len(qs)
    st.progress(progress)
    st.markdown(f"<div class='small-note'>{idx+1} / {len(qs)}</div>", unsafe_allow_html=True)
    story_en = ["Set the scene.", "Now the relationship is tested.", "Control becomes visible when access is needed.", "A handover reveals what is truly portable.", "Contracts matter most when the relationship changes.", "Continuity is measured by what happens next.", "Evidence turns confidence into assurance.", "Your profile is almost complete."]
    story_ar = ["لنحدد المشهد أولًا.", "الآن تبدأ العلاقة التقنية بالاختبار.", "تظهر السيطرة الحقيقية عندما نحتاج الوصول.", "لحظة التسليم تكشف ما يمكن نقله فعلًا.", "تظهر قيمة العقود عندما تتغير العلاقة.", "الاستمرارية تُقاس بما يحدث بعد التعطل.", "الدليل يحول الثقة إلى ضمان.", "اكتمل ملفك تقريبًا."]
    beat = (story_ar if lang=="ar" else story_en)[min(idx,7)]
    st.markdown(f"<div class='eyebrow'>{beat}</div>", unsafe_allow_html=True)
    st.markdown(f"### {q[lang]}")

    options = q["options"]
    option_ids = [o["id"] for o in options]
    current = st.session_state.answers.get(q["id"])
    current_idx = option_ids.index(current) if current in option_ids else None
    selected = st.radio("", option_ids, index=current_idx, format_func=lambda oid: next(o[lang] for o in options if o["id"]==oid), label_visibility="collapsed")
    if selected:
        st.session_state.answers[q["id"]] = selected

    c1,c2 = st.columns([1,2])
    with c1:
        if idx > 0 and st.button(t("back"), use_container_width=True):
            st.session_state.q_index -= 1
            st.rerun()
    with c2:
        btn_text = t("finish") if idx == len(qs)-1 else t("next")
        if st.button(btn_text, use_container_width=True, disabled=not bool(selected)):
            if idx == len(qs)-1:
                st.session_state.page = "result"
            else:
                # representation changes route and question list; retain natural progression
                st.session_state.q_index += 1
            st.rerun()

# -----------------------------
# Explorer
# -----------------------------
elif st.session_state.page == "explorer_result":
    st.markdown(f"""
    <div class="score-card">
      <div class="eyebrow">DISCOVERY PROFILE</div>
      <div class="persona">{t('explorer_title')}</div>
      <p class="muted">{t('explorer_msg')}</p>
      <div class="pill">{t('explore_rec')}</div>
    </div>
    """, unsafe_allow_html=True)
    # Store anonymous non-target visit automatically: no personal data.
    if not st.session_state.get("explorer_saved"):
        scores = {
            "route":"explorer","readiness":0,"need":0,"eligibility":0,"influence":0,"fit":0,"commercial":0,
            "opportunity":"General Visitor","persona_key":"explorer","priority_key":"none",
            "dimensions": {"asset_control":0,"continuity":0,"exit_readiness":0,"contract_clarity":0,"governance":0,"business_criticality":0,"provider_assurance":0}
        }
        try:
            save_record(flatten_record(scores, st.session_state.answers, {}))
            st.session_state.explorer_saved = True
        except Exception:
            pass
    if st.button("Start again / ابدأ من جديد", use_container_width=True):
        reset_assessment(); st.rerun()

# -----------------------------
# Result
# -----------------------------
elif st.session_state.page == "result":
    scores = calculate_scores(st.session_state.answers)
    p = PERSONAS[scores["persona_key"]]
    persona = p[lang]
    desc = p[f"{lang}_desc"]
    service = p[f"service_{lang}"]
    priority = scores[f"priority_{lang}"]

    reveal = ("Your story reveals where control is strong — and where one disruption could create pressure." if lang=="en" else "قصتك تكشف أين تملك جهتك السيطرة، وأين قد يتحول تعطل واحد إلى ضغط حقيقي.")
    st.markdown(f"<div class='hero'><div class='eyebrow'>{'YOUR CONTINUITY STORY' if lang=='en' else 'قصة استمراريتك'}</div><h2>{reveal}</h2></div>", unsafe_allow_html=True)
    left,right = st.columns([1.15,1])
    with left:
        st.markdown(f"""
        <div class="score-card">
          <div class="eyebrow">{t('result')}</div>
          <div class="score">{scores['readiness']}</div>
          <div class="persona">{persona}</div>
          <p class="muted">{desc}</p>
          <div class="pill">{t('priority')}: {priority}</div>
          <div class="pill">{t('recommendation')}: {service}</div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        dims = scores["dimensions"]
        radar_keys = ["asset_control","continuity","exit_readiness","contract_clarity","governance"] if scores["route"] != "provider" else ["provider_assurance","asset_control","continuity","contract_clarity","governance"]
        labels_en = {"asset_control":"Asset Control","continuity":"Continuity","exit_readiness":"Exit Readiness","contract_clarity":"Contract Clarity","governance":"Governance","provider_assurance":"Client Assurance"}
        labels_ar = {"asset_control":"السيطرة على الأصول","continuity":"الاستمرارية","exit_readiness":"جاهزية الانتقال","contract_clarity":"وضوح العقود","governance":"الحوكمة","provider_assurance":"ضمان العملاء"}
        labels = labels_ar if lang=="ar" else labels_en
        fig = go.Figure(go.Scatterpolar(r=[dims[k] for k in radar_keys], theta=[labels[k] for k in radar_keys], fill="toself"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])), showlegend=False, height=390,
                          margin=dict(l=40,r=40,t=30,b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    st.divider()
    st.markdown(f"### {t('lead_contact')}")
    c1,c2 = st.columns(2)
    with c1:
        name = st.text_input(t("name")); org = st.text_input(t("org"))
    with c2:
        email = st.text_input(t("email")); phone = st.text_input(t("phone"))
    consent = st.checkbox(t("consent"))
    if st.button(t("save"), use_container_width=True):
        contact = {"name":name,"organization":org,"email":email,"phone":phone,"consent":consent}
        # Personal contact data is only stored if consent is given. Scores may be stored anonymously.
        if not consent:
            contact = {"name":"","organization":"","email":"","phone":"","consent":False}
        record = flatten_record(scores, st.session_state.answers, contact)
        try:
            target = save_record(record)
            st.success(t("saved") + (" Google Sheets ✓" if target=="google" else " Local demo storage ✓"))
        except Exception as e:
            st.error(("Could not save the record. " if lang=="en" else "تعذر حفظ النتيجة. ") + str(e))

    if st.button("Start a new visitor / زائر جديد", use_container_width=True):
        reset_assessment(); st.rerun()

# -----------------------------
# Dashboard login + dashboard
# -----------------------------
elif st.session_state.page == "dashboard_login":
    st.markdown(f"## {t('dashboard')}")
    configured = st.secrets.get("DASHBOARD_PASSWORD", "")
    pwd = st.text_input(t("password"), type="password")
    if st.button(t("open_dashboard"), use_container_width=True):
        if not configured or pwd == configured:
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Incorrect password / كلمة المرور غير صحيحة")

elif st.session_state.page == "dashboard":
    st.markdown(f"## {t('dashboard')}")
    df = load_data()
    if df.empty:
        st.info("No response data yet / لا توجد بيانات حتى الآن")
    else:
        numeric_cols = ["readiness_score","service_need_pct","eligibility_score","commercial_opportunity_score"]
        for col in numeric_cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")

        # Filters
        f1,f2 = st.columns(2)
        with f1:
            classes = sorted(df["opportunity_class"].dropna().astype(str).unique()) if "opportunity_class" in df else []
            chosen = st.multiselect("Opportunity / الفرصة", classes, default=classes)
        with f2:
            routes = sorted(df["route"].dropna().astype(str).unique()) if "route" in df else []
            chosen_routes = st.multiselect("Route / المسار", routes, default=routes)
        dff = df.copy()
        if chosen: dff = dff[dff["opportunity_class"].isin(chosen)]
        if chosen_routes: dff = dff[dff["route"].isin(chosen_routes)]

        total = len(dff)
        qualified = int(dff["opportunity_class"].isin(["Priority Opportunity","Qualified Opportunity"]).sum()) if total else 0
        priority = int((dff["opportunity_class"]=="Priority Opportunity").sum()) if total else 0
        avg_need = round(dff["service_need_pct"].mean(),1) if total and "service_need_pct" in dff else 0
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Visitors / الزوار", total)
        k2.metric("Qualified / المؤهلون", qualified, f"{(qualified/total*100):.0f}%" if total else "0%")
        k3.metric("Priority / أولوية", priority)
        k4.metric("Avg. Need / متوسط الاحتياج", f"{avg_need}%")

        c1,c2 = st.columns(2)
        with c1:
            if "persona" in dff:
                persona_df = dff.groupby("persona", dropna=False).size().reset_index(name="count")
                persona_df["label"] = persona_df["persona"].map(lambda x: persona_label(str(x), lang))
                fig = px.bar(persona_df, x="label", y="count", title="Persona Distribution / توزيع الشخصيات")
                fig.update_layout(xaxis_title="", yaxis_title="Visitors", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            if "opportunity_class" in dff:
                opp_df = dff.groupby("opportunity_class").size().reset_index(name="count")
                fig = px.pie(opp_df, names="opportunity_class", values="count", hole=.55, title="Opportunity Mix / مزيج الفرص")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        c3,c4 = st.columns(2)
        with c3:
            if "persona" in dff and "service_need_pct" in dff:
                need_df = dff.groupby("persona", as_index=False)["service_need_pct"].mean()
                need_df["label"] = need_df["persona"].map(lambda x: persona_label(str(x), lang))
                fig = px.bar(need_df, x="label", y="service_need_pct", title="Service Need by Persona / الاحتياج حسب الشخصية", range_y=[0,100])
                fig.update_layout(xaxis_title="", yaxis_title="Need %", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        with c4:
            if "readiness_score" in dff and "commercial_opportunity_score" in dff:
                fig = px.scatter(dff, x="readiness_score", y="commercial_opportunity_score", color="opportunity_class",
                                 hover_data=[c for c in ["organization","name","route","service_need_pct"] if c in dff.columns],
                                 title="Readiness vs Opportunity / الجاهزية مقابل الفرصة")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        if "priority_area" in dff:
            pr = dff.groupby("priority_area").size().reset_index(name="count").sort_values("count", ascending=False)
            fig = px.bar(pr, x="count", y="priority_area", orientation="h", title="Most Common Priority Areas / أكثر مناطق الأولوية")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        # Lead table
        show_cols = [c for c in ["timestamp","name","organization","route","persona","readiness_score","service_need_pct","commercial_opportunity_score","opportunity_class","priority_area","email","phone"] if c in dff.columns]
        if "commercial_opportunity_score" in dff:
            dff = dff.sort_values("commercial_opportunity_score", ascending=False)
        st.dataframe(dff[show_cols], use_container_width=True, hide_index=True)

        csv = dff.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Download filtered CSV / تحميل CSV", data=csv, file_name="continuity_leads.csv", mime="text/csv", use_container_width=True)

    if st.button("Back to visitor experience / العودة للتجربة", use_container_width=True):
        reset_assessment(); st.rerun()
