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

st.set_page_config(
    page_title="Continuity Intelligence | استمرارية التقنية",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# DESIGN SYSTEM
# ============================================================
THEMES = {
    "Dark": {
        "bg": "#050812", "surface": "#091120", "surface2": "#0D1628", "text": "#F5F8FF",
        "muted": "#91A0BD", "line": "#1C2E4B", "cyan": "#12D7D1", "blue": "#3487FF",
        "purple": "#7C4DFF", "red": "#FF5068", "orange": "#FFAA36", "green": "#20D8A4",
    },
    "Light": {
        "bg": "#F5F7FB", "surface": "#FFFFFF", "surface2": "#EEF3FA", "text": "#10172A",
        "muted": "#65718B", "line": "#DCE4F0", "cyan": "#00AFA7", "blue": "#3178F6",
        "purple": "#7045EE", "red": "#E6425A", "orange": "#E88A16", "green": "#0AA77E",
    },
}

COPY = {
    "en": {
        "brand": "CONTINUITY INTELLIGENCE",
        "start": "TEST MY CONTINUITY",
        "hero_title": "YOUR PROVIDER IS OFFLINE.",
        "hero_sub": "Is your business still online?",
        "hero_body": "The real risk isn't when technology fails. It's discovering who controls your critical assets after it does.",
        "journey": "What happens next depends on what you control today.",
        "journey_sub": "Walk through a short incident story and discover your continuity profile in under two minutes.",
        "language": "Language", "theme": "Theme", "back": "Back", "next": "Next",
        "result_title": "Your continuity journey is complete",
        "result_sub": "Your answers reveal where control is strong, where dependency rises, and what deserves attention first.",
        "score": "Technology Continuity Readiness Score", "persona": "Your continuity persona",
        "priorities": "Your priorities to improve", "recommend": "Recommended for you",
        "cta": "Start your journey toward technology independence", "cta_sub": "Request a focused continuity consultation based on your profile.",
        "consult": "REQUEST A CONSULTATION", "save": "SAVE MY DETAILS", "saved": "Your assessment has been saved.",
        "name": "Name (optional)", "org": "Organization (optional)", "email": "Work email (optional)", "phone": "Mobile (optional)",
        "consent": "I agree to be contacted about this assessment and related continuity services.",
        "new": "START A NEW VISITOR", "team": "Team analytics", "password": "Dashboard password", "open": "OPEN DASHBOARD",
        "explorer_title": "The Explorer", "explorer_body": "You are exploring the topic rather than representing a current organizational continuity need.",
    },
    "ar": {
        "brand": "CONTINUITY INTELLIGENCE",
        "start": "اختبر استمراريتك",
        "hero_title": "المورّد خارج الخدمة.",
        "hero_sub": "هل أعمالك ما زالت تعمل؟",
        "hero_body": "الخطر الحقيقي ليس في تعطل التقنية، بل في اكتشاف من يملك السيطرة على أصولك الحرجة بعد حدوثه.",
        "journey": "ما سيحدث بعد ذلك يعتمد على ما تملكه وتسيطر عليه اليوم.",
        "journey_sub": "عِش قصة حادث تقني قصيرة واكتشف ملف استمراريتك خلال أقل من دقيقتين.",
        "language": "اللغة", "theme": "المظهر", "back": "رجوع", "next": "التالي",
        "result_title": "اكتملت رحلة تقييم جاهزيتك لاستمرارية التقنية",
        "result_sub": "إجاباتك تكشف أين تملك السيطرة، وأين يرتفع الاعتماد، وما الذي يستحق اهتمامك أولًا.",
        "score": "درجة جاهزية استمرارية التقنية", "persona": "شخصية الاستمرارية لديك",
        "priorities": "أولوياتك للتحسين", "recommend": "توصيتنا لك",
        "cta": "ابدأ رحلتك نحو الاستقلال التقني", "cta_sub": "احصل على جلسة استشارية مركزة مبنية على ملف استمراريتك.",
        "consult": "احجز استشارة", "save": "احفظ بياناتي", "saved": "تم حفظ تقييمك بنجاح.",
        "name": "الاسم (اختياري)", "org": "الجهة (اختياري)", "email": "البريد المهني (اختياري)", "phone": "رقم الجوال (اختياري)",
        "consent": "أوافق على التواصل معي بشأن هذا التقييم وخدمات الاستمرارية ذات الصلة.",
        "new": "زائر جديد", "team": "لوحة فريق العمل", "password": "كلمة مرور لوحة المؤشرات", "open": "فتح اللوحة",
        "explorer_title": "المستكشف", "explorer_body": "أنت تستكشف الموضوع حاليًا أكثر من تمثيل احتياج مؤسسي مباشر لاستمرارية التقنية.",
    },
}

# ============================================================
# MODEL
# Readiness: 100 = stronger resilience. Commercial scores stay hidden.
# ============================================================
QUESTIONS = [
    {
        "id": "representation", "paths": ["all"], "time": "WELCOME", "icon": "badge",
        "en": "What best describes your place in the technology ecosystem today?",
        "ar": "ما الدور الأقرب لك اليوم في المنظومة التقنية؟",
        "helper_en": "Choose the card that best represents why you are here.",
        "helper_ar": "اختر البطاقة الأقرب لما تمثله اليوم.",
        "options": [
            {"id":"org","en":"I represent an organization","ar":"أمثل جهة","sub_en":"We use or procure technology solutions.","sub_ar":"نستخدم أو نتعاقد على حلول تقنية.","eligibility":30,"route":"client","icon":"apartment"},
            {"id":"provider","en":"We provide technology solutions","ar":"نقدم حلولًا تقنية","sub_en":"We build, operate or deliver technology to clients.","sub_ar":"نطور أو نشغل أو نقدم حلولًا لجهات أخرى.","eligibility":26,"route":"provider","icon":"code"},
            {"id":"both","en":"We do both","ar":"نقوم بالدورين","sub_en":"We consume technology and also provide it.","sub_ar":"نستخدم التقنية ونقدمها للآخرين.","eligibility":30,"route":"hybrid","icon":"hub"},
            {"id":"advisor","en":"Advisor / specialist","ar":"مستشار / خبير","sub_en":"I advise on technology, contracts or risk.","sub_ar":"أعمل مع الجهات في التقنية أو العقود أو المخاطر.","eligibility":20,"route":"advisor","icon":"explore"},
            {"id":"self","en":"I'm exploring","ar":"أنا مستكشف","sub_en":"General interest; I am not representing an organization.","sub_ar":"اهتمام عام ولا أمثل جهة في هذا السياق.","eligibility":0,"route":"explorer","icon":"person_search"},
        ],
    },
    {
        "id":"influence", "paths":["client","provider","hybrid","advisor"], "time":"PROFILE", "icon":"hub",
        "en":"When an important technology decision is made, where do you usually enter the picture?",
        "ar":"عندما يُتخذ قرار تقني مهم، أين يكون دورك عادة؟",
        "helper_en":"We are mapping your position in the decision journey — not your job title.",
        "helper_ar":"نحدد موقعك في رحلة القرار، وليس مجرد المسمى الوظيفي.",
        "options":[
            {"id":"approve","en":"I approve or sponsor the decision","ar":"أعتمد القرار أو أرعاه","influence":25,"icon":"verified"},
            {"id":"evaluate","en":"I evaluate options and shape the decision","ar":"أقيّم الخيارات وأؤثر في القرار","influence":20,"icon":"search"},
            {"id":"manage","en":"I manage implementation, operations or vendors","ar":"أدير التنفيذ أو التشغيل أو الموردين","influence":16,"icon":"settings"},
            {"id":"use","en":"I mainly use the systems","ar":"أستخدم الأنظمة بشكل أساسي","influence":5,"icon":"computer"},
            {"id":"indirect","en":"I am not directly involved","ar":"لست مشاركًا بشكل مباشر","influence":0,"icon":"visibility_off"},
        ],
    },
    {
        "id":"org_scale", "paths":["client","provider","hybrid","advisor"], "time":"PROFILE", "icon":"domain",
        "en":"Which environment is closest to the organization you represent?",
        "ar":"أي بيئة هي الأقرب للجهة التي تمثلها؟",
        "helper_en":"This helps calibrate the complexity of continuity risk.",
        "helper_ar":"يساعدنا ذلك على تقدير تعقيد مخاطر الاستمرارية.",
        "options":[
            {"id":"gov","en":"Government / public sector","ar":"جهة حكومية / قطاع عام","fit":20,"icon":"account_balance"},
            {"id":"large","en":"Large private enterprise","ar":"منشأة خاصة كبيرة","fit":20,"icon":"business"},
            {"id":"mid","en":"Mid-sized organization","ar":"منشأة متوسطة","fit":14,"icon":"domain"},
            {"id":"startup","en":"Startup / small business","ar":"شركة ناشئة / منشأة صغيرة","fit":7,"icon":"rocket_launch"},
            {"id":"individual","en":"I am not representing an organization","ar":"لا أمثل جهة","fit":0,"icon":"person"},
        ],
    },
    {
        "id":"provider_disruption", "paths":["client","hybrid","advisor"], "time":"09:24 AM", "icon":"cloud_off",
        "en":"Your critical service is unavailable. Your provider isn't responding. What's the most likely next move for your team?",
        "ar":"خدمة حرجة توقفت، والمورد لا يستجيب. ما الخطوة الأقرب التي سيتخذها فريقك؟",
        "helper_en":"There is no right or wrong answer. We are measuring preparedness, not performance.",
        "helper_ar":"لا توجد إجابة صحيحة أو خاطئة؛ نحن نقيس الجاهزية لا الأداء.",
        "options":[
            {"id":"internal","en":"We continue with assets and procedures already under our control","ar":"نستمر باستخدام الأصول والإجراءات الموجودة تحت سيطرتنا","continuity":95,"asset_control":90,"need":2,"icon":"shield"},
            {"id":"arrangement","en":"We activate a predefined continuity arrangement","ar":"نفعّل ترتيب استمرارية محدد مسبقًا","continuity":85,"asset_control":80,"need":5,"icon":"task_alt"},
            {"id":"alternate","en":"We coordinate with another provider to restore operations","ar":"نتواصل مع مزود بديل لاستعادة التشغيل","continuity":65,"asset_control":60,"need":10,"icon":"sync_alt"},
            {"id":"wait","en":"We need the existing provider before we can fully recover","ar":"نحتاج المورد الحالي قبل أن نستعيد التشغيل بالكامل","continuity":30,"asset_control":35,"need":20,"icon":"link_off"},
            {"id":"unknown","en":"I am not sure what would happen","ar":"لست متأكدًا مما سيحدث","continuity":20,"asset_control":25,"need":22,"icon":"help"},
        ],
    },
    {
        "id":"handover", "paths":["client","hybrid","advisor"], "time":"10:05 AM", "icon":"move_down",
        "en":"A replacement technical team is ready. What could your organization confidently hand them today?",
        "ar":"فريق تقني بديل جاهز الآن. ما الذي تستطيع جهتك تسليمه بثقة اليوم؟",
        "helper_en":"Think about code, data, documentation, access, architecture and deployment details as one handover package.",
        "helper_ar":"فكر في الكود والبيانات والتوثيق والصلاحيات والمعمارية وتفاصيل النشر كحزمة تسليم واحدة.",
        "options":[
            {"id":"complete","en":"A complete, independently accessible handover package","ar":"حزمة تسليم مكتملة ويمكن الوصول لها باستقلالية","asset_control":100,"exit_readiness":95,"need":1,"icon":"inventory_2"},
            {"id":"mostly","en":"Most assets are ready, with a few provider dependencies","ar":"معظم الأصول جاهزة مع بعض الاعتماد على المورد","asset_control":75,"exit_readiness":75,"need":7,"icon":"folder"},
            {"id":"partial","en":"A partial package; significant coordination is still needed","ar":"حزمة جزئية وما زلنا نحتاج تنسيقًا كبيرًا","asset_control":50,"exit_readiness":45,"need":14,"icon":"folder_open"},
            {"id":"obtain","en":"Key assets must first be obtained from the current provider","ar":"نحتاج أولًا الحصول على أصول أساسية من المورد الحالي","asset_control":25,"exit_readiness":25,"need":21,"icon":"lock"},
            {"id":"unknown","en":"I am not sure what is actually available","ar":"لست متأكدًا مما هو متوفر فعليًا","asset_control":20,"exit_readiness":20,"need":22,"icon":"help"},
        ],
    },
    {
        "id":"exit", "paths":["client","hybrid","advisor"], "time":"11:40 AM", "icon":"logout",
        "en":"Your organization decides to end the relationship with this provider. Which statement best describes what happens next?",
        "ar":"قررت جهتك إنهاء العلاقة مع هذا المورد. أي وصف هو الأقرب لما سيحدث بعد ذلك؟",
        "helper_en":"Exit readiness becomes visible when roles, rights and handover duties are tested.",
        "helper_ar":"تظهر جاهزية الخروج عندما تُختبر الأدوار والحقوق والتزامات التسليم.",
        "options":[
            {"id":"predefined","en":"Transition steps, responsibilities and access rights are predefined","ar":"خطوات الانتقال والمسؤوليات وحقوق الوصول محددة مسبقًا","exit_readiness":100,"contract_clarity":95,"need":1,"icon":"fact_check"},
            {"id":"general","en":"The agreement provides general transition guidance","ar":"الاتفاقية توفر توجيهًا عامًا للانتقال","exit_readiness":70,"contract_clarity":70,"need":7,"icon":"description"},
            {"id":"negotiate","en":"The parties agree on transition arrangements when needed","ar":"يتم الاتفاق على ترتيبات الانتقال عند الحاجة","exit_readiness":45,"contract_clarity":45,"need":14,"icon":"handshake"},
            {"id":"provider","en":"The transition depends heavily on the provider","ar":"يعتمد الانتقال بدرجة كبيرة على المورد","exit_readiness":25,"contract_clarity":30,"need":21,"icon":"link"},
            {"id":"unknown","en":"I am not sure","ar":"لست متأكدًا","exit_readiness":20,"contract_clarity":20,"need":22,"icon":"help"},
        ],
    },
    {
        "id":"assurance", "paths":["provider","hybrid"], "time":"01:30 PM", "icon":"verified_user",
        "en":"A client asks: “How do you ensure continuity if your company becomes unavailable?” How confidently can you prove it?",
        "ar":"سألك عميل: «كيف تضمنون الاستمرارية إذا تعذر توفر شركتكم؟» ما مدى قدرتكم على إثبات ذلك؟",
        "helper_en":"Confidence matters; independent evidence matters more.",
        "helper_ar":"الثقة مهمة، لكن الدليل المستقل أهم.",
        "options":[
            {"id":"independent","en":"Very confidently — independent safeguards and evidence are ready","ar":"بثقة عالية جدًا — ضمانات مستقلة وأدلة جاهزة","continuity":95,"asset_control":95,"provider_assurance":100,"need":2,"icon":"workspace_premium"},
            {"id":"internal","en":"Confidently — strong internal processes and evidence exist","ar":"بثقة — لدينا إجراءات داخلية وأدلة قوية","continuity":75,"asset_control":75,"provider_assurance":75,"need":7,"icon":"verified"},
            {"id":"description","en":"Somewhat confidently — evidence is mostly contractual","ar":"بثقة جزئية — أغلب الإثباتات تعاقدية","continuity":55,"asset_control":55,"provider_assurance":50,"need":13,"icon":"description"},
            {"id":"ad_hoc","en":"Not confidently — we would arrange it if the incident occurs","ar":"بثقة منخفضة — سنرتب الأمر إذا حدثت المشكلة","continuity":35,"asset_control":35,"provider_assurance":30,"need":19,"icon":"warning"},
            {"id":"unsure","en":"I am not sure how we would prove it","ar":"لست متأكدًا كيف سنثبت ذلك","continuity":25,"asset_control":25,"provider_assurance":20,"need":21,"icon":"help"},
        ],
    },
    {
        "id":"client_request", "paths":["provider","hybrid"], "time":"02:10 PM", "icon":"policy",
        "en":"When enterprise clients ask about code, data, backups and continuity protections, what usually happens?",
        "ar":"عندما يسأل عملاء المؤسسات عن حماية الكود والبيانات والنسخ الاحتياطية والاستمرارية، ماذا يحدث عادة؟",
        "helper_en":"This reveals whether continuity accelerates trust or becomes part of the sales friction.",
        "helper_ar":"يكشف ذلك هل الاستمرارية تعزز الثقة أم تتحول إلى عائق في التعاقد.",
        "options":[
            {"id":"standard","en":"We have a standard, ready-to-share assurance package","ar":"لدينا حزمة ضمان قياسية وجاهزة للمشاركة","provider_assurance":100,"contract_clarity":90,"need":2,"icon":"inventory"},
            {"id":"custom","en":"We prepare evidence separately for each client","ar":"نجهز الإثباتات بشكل منفصل لكل عميل","provider_assurance":70,"contract_clarity":70,"need":8,"icon":"tune"},
            {"id":"legal","en":"It becomes a contract or legal negotiation","ar":"يتحول الأمر إلى تفاوض تعاقدي أو قانوني","provider_assurance":50,"contract_clarity":55,"need":13,"icon":"gavel"},
            {"id":"friction","en":"It often slows down the deal or creates concern","ar":"غالبًا يؤخر الصفقة أو يخلق قلقًا لدى العميل","provider_assurance":30,"contract_clarity":40,"need":20,"icon":"hourglass_empty"},
            {"id":"rare","en":"Clients rarely ask about it","ar":"نادرًا ما يسأل العملاء عنه","provider_assurance":45,"contract_clarity":45,"need":12,"icon":"forum"},
        ],
    },
    {
        "id":"change_test", "paths":["client","provider","hybrid","advisor"], "time":"FINAL CHECK", "icon":"plagiarism",
        "en":"If leadership, a regulator or a client asked for continuity evidence tomorrow, how quickly could you provide it?",
        "ar":"لو طلبت الإدارة أو جهة تنظيمية أو عميل غدًا أدلة على جاهزية الاستمرارية، كم ستحتاجون لتقديمها؟",
        "helper_en":"Evidence turns confidence into assurance.",
        "helper_ar":"الدليل يحول الثقة إلى ضمان.",
        "options":[
            {"id":"immediate","en":"Immediately — evidence is organized and current","ar":"فورًا — الأدلة منظمة ومحدثة","governance":100,"need":1,"icon":"bolt"},
            {"id":"day","en":"Within a day","ar":"خلال يوم","governance":80,"need":5,"icon":"today"},
            {"id":"week","en":"Within a week","ar":"خلال أسبوع","governance":60,"need":10,"icon":"calendar_month"},
            {"id":"effort","en":"It would require significant effort","ar":"سيتطلب جهدًا كبيرًا","governance":35,"need":17,"icon":"construction"},
            {"id":"unknown","en":"I would not know where to start","ar":"لن أعرف من أين أبدأ","governance":20,"need":21,"icon":"help"},
        ],
    },
]

PERSONAS = {
    "resilient": {"en":"The Resilient Guardian","ar":"الحارس المرن","en_desc":"Strong control and transition readiness. Your priority is to validate and sustain resilience.","ar_desc":"سيطرة قوية وجاهزية مرتفعة للانتقال. أولويتك هي التحقق المستمر والمحافظة على المرونة.","service_en":"Resilience Validation & Independent Assurance","service_ar":"التحقق من المرونة والضمان المستقل"},
    "managed": {"en":"The Managed Dependency","ar":"الاعتماد المُدار","en_desc":"Your environment is prepared, with selected dependencies that deserve stronger safeguards.","ar_desc":"بيئتكم مستعدة بشكل جيد، مع بعض نقاط الاعتماد التي تستحق ضمانات أقوى.","service_en":"Dependency & Continuity Review","service_ar":"مراجعة الاعتماد واستمرارية التقنية"},
    "exposed": {"en":"The Exposed Operator","ar":"المشغّل المعرّض","en_desc":"Operations work today, but disruption or transition could expose material gaps in access, handover or agreements.","ar_desc":"التشغيل يعمل اليوم، لكن التعطل أو الانتقال قد يكشف فجوات مهمة في الوصول أو التسليم أو الاتفاقيات.","service_en":"Technology Continuity Assessment","service_ar":"تقييم استمرارية التقنية"},
    "critical": {"en":"The Critical Dependency","ar":"الاعتماد الحرج","en_desc":"Critical relationships show high dependency and limited recovery or exit readiness.","ar_desc":"العلاقات التقنية الحرجة تظهر اعتمادًا مرتفعًا وجاهزية محدودة للتعافي أو الانتقال.","service_en":"Priority Continuity, Escrow & Contract Risk Assessment","service_ar":"تقييم عاجل للاستمرارية وحفظ الأصول ومخاطر العقود"},
    "provider_ready": {"en":"The Trusted Provider","ar":"المزوّد الموثوق","en_desc":"You can demonstrate continuity and client assurance with strong evidence and controls.","ar_desc":"لديكم قدرة قوية على إثبات الاستمرارية وضمان العملاء بأدلة وضوابط واضحة.","service_en":"Independent Assurance & Trust Validation","service_ar":"الضمان المستقل والتحقق من الثقة"},
    "provider_growth": {"en":"The Trust Builder","ar":"باني الثقة","en_desc":"Your solution is viable, while stronger independent safeguards could reduce enterprise buying friction.","ar_desc":"حلولكم قوية، لكن تعزيز ضمانات الاستمرارية المستقلة قد يقلل تردد عملاء المؤسسات ويسرّع التعاقد.","service_en":"Provider Assurance & Escrow Readiness","service_ar":"جاهزية ضمان المزوّد وحفظ الأصول"},
}

# ============================================================
# HELPERS
# ============================================================
def tr(key):
    return COPY[st.session_state.lang][key]


def inject_css(theme_name, lang):
    c = THEMES[theme_name]
    direction = "rtl" if lang == "ar" else "ltr"
    align = "right" if lang == "ar" else "left"
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');
    :root {{ --bg:{c['bg']};--surface:{c['surface']};--surface2:{c['surface2']};--text:{c['text']};--muted:{c['muted']};--line:{c['line']};--cyan:{c['cyan']};--blue:{c['blue']};--purple:{c['purple']};--red:{c['red']};--orange:{c['orange']};--green:{c['green']}; }}
    .stApp {{ background: radial-gradient(circle at 80% 0%, rgba(124,77,255,.08), transparent 26%), var(--bg); color:var(--text); }}
    html, body, [class*="st-"] {{ font-family: {'IBM Plex Sans Arabic' if lang=='ar' else 'Inter'}, sans-serif; direction:{direction}; }}
    .block-container {{ max-width: 1240px; padding-top:1.15rem; padding-bottom:4rem; }}
    #MainMenu, footer, header {{ visibility:hidden; }}
    section[data-testid="stSidebar"] {{ display:none; }}
    h1,h2,h3,p,label {{ text-align:{align}; color:var(--text); }}
    /* Contact form: keep fields readable in dark mode */
    div[data-testid="stTextInput"] input {{
        background:#0B1526 !important;
        color:#F5F8FF !important;
        -webkit-text-fill-color:#F5F8FF !important;
        border:1px solid #233755 !important;
        border-radius:10px !important;
        caret-color:var(--cyan) !important;
    }}
    div[data-testid="stTextInput"] input::placeholder {{ color:#71809B !important; opacity:1 !important; }}
    div[data-testid="stTextInput"] label, div[data-testid="stCheckbox"] label {{ color:var(--text) !important; }}
    div[data-testid="stTextInput"] [data-baseweb="input"] {{ background:#0B1526 !important; border-radius:10px !important; }}
    div[data-testid="stCheckbox"] p {{ color:var(--text) !important; }}
    .topbar {{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:4px 0 18px 0;}}
    .brand {{font-weight:800;letter-spacing:.11em;font-size:.76rem;color:var(--cyan);}}
    .brand span {{color:var(--purple);}}
    .langhint {{color:var(--muted);font-size:.78rem;}}
    .panel {{background:linear-gradient(145deg,rgba(13,22,40,.95),rgba(7,14,28,.96));border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 18px 55px rgba(0,0,0,.18);}}
    .eyebrow {{font-size:.74rem;font-weight:800;letter-spacing:.09em;color:var(--cyan);text-transform:uppercase;}}
    .hero-wrap {{border:1px solid var(--line);border-radius:30px;padding:34px;background:linear-gradient(135deg,rgba(9,17,32,.98),rgba(8,12,27,.98));position:relative;overflow:hidden;}}
    .hero-wrap:after {{content:"";position:absolute;width:360px;height:360px;border-radius:50%;background:radial-gradient(circle,rgba(255,80,104,.18),transparent 68%);right:-80px;top:-120px;pointer-events:none;}}
    .incident {{display:grid;grid-template-columns:1fr 1.15fr;gap:30px;align-items:center;}}
    .statusbox {{border:1px solid rgba(255,80,104,.38);background:rgba(255,80,104,.055);border-radius:18px;padding:18px;box-shadow:inset 0 0 35px rgba(255,80,104,.03);}}
    .statusrow {{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:10px 2px;font-size:.85rem;}}
    .statusrow:last-child {{border-bottom:0;}}
    .bad {{color:var(--red);font-weight:800;letter-spacing:.04em;}}
    .warning-symbol {{font-size:4.6rem;color:var(--red);filter:drop-shadow(0 0 24px rgba(255,80,104,.35));text-align:center;line-height:1.2;}}
    .hero-title {{font-size:clamp(2rem,4vw,3.5rem);font-weight:850;line-height:1.05;margin:.5rem 0;color:var(--text);}}
    .hero-sub {{font-size:1.55rem;font-weight:750;color:var(--text);margin-bottom:12px;}}
    .muted {{color:var(--muted);line-height:1.8;}}
    .mini-grid {{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:20px;}}
    .mini {{background:rgba(255,255,255,.018);border:1px solid var(--line);border-radius:15px;padding:14px;text-align:center;}}
    .mini b {{display:block;color:var(--cyan);font-size:1.15rem;}}
    .timeline {{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:20px 0;}}
    .time-card {{border:1px solid var(--line);background:var(--surface);border-radius:18px;padding:18px;}}
    .time-card strong {{color:var(--cyan);font-size:.8rem;}}
    .terminal {{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#02050B;border:1px solid #17243A;border-radius:18px;padding:18px;color:#8BA0C2;line-height:1.75;box-shadow:inset 0 0 30px rgba(0,0,0,.4);}}
    .terminal .err {{color:var(--red);}} .terminal .ok {{color:var(--cyan);}}
    .progress-shell {{height:7px;background:#101A2B;border-radius:999px;overflow:hidden;margin:6px 0 24px;}}
    .progress-fill {{height:100%;background:linear-gradient(90deg,var(--cyan),var(--purple));border-radius:999px;}}
    .scenario-head {{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:16px;}}
    .time-chip {{color:var(--cyan);font-size:.8rem;font-weight:800;letter-spacing:.05em;}}
    .question-title {{font-size:clamp(1.55rem,2.5vw,2.15rem);font-weight:800;line-height:1.35;margin:.35rem 0 .65rem;}}
    .helper {{color:var(--muted);font-size:.92rem;margin-bottom:16px;}}
    .persona-visual {{min-height:142px;border:1px solid var(--line);border-radius:20px;padding:20px;background:linear-gradient(145deg,var(--surface),var(--surface2));margin-bottom:10px;transition:.2s;}}
    .persona-visual:hover {{border-color:var(--cyan);transform:translateY(-2px);box-shadow:0 10px 30px rgba(18,215,209,.08);}}
    .picon {{font-size:2rem;color:var(--cyan);margin-bottom:14px;}}
    .ptitle {{font-weight:800;font-size:1rem;margin-bottom:5px;}}
    .psub {{font-size:.82rem;color:var(--muted);line-height:1.5;}}
    div[data-testid="stButton"] button {{min-height:51px;border-radius:14px;border:1px solid var(--line);background:linear-gradient(135deg,rgba(124,77,255,.96),rgba(18,215,209,.92));color:white;font-weight:800;box-shadow:none;}}
    div[data-testid="stButton"] button:hover {{border-color:var(--cyan);filter:brightness(1.06);transform:translateY(-1px);}}
    div[data-testid="stButton"] button[kind="secondary"] {{background:var(--surface);color:var(--text);}}
    .option-note {{padding:12px 15px;border:1px solid var(--line);border-radius:14px;background:var(--surface);color:var(--muted);font-size:.84rem;margin-top:10px;}}
    .result-header {{text-align:center;margin:4px 0 24px;}}
    .result-header h1 {{text-align:center;font-size:2.25rem;margin:.45rem 0;}}
    .result-header p {{text-align:center;color:var(--muted);}}
    .score-panel {{height:100%;border:1px solid var(--line);border-radius:22px;background:var(--surface);padding:22px;}}
    .persona-name {{font-size:1.6rem;font-weight:850;margin-top:8px;}}
    .persona-eng {{display:inline-block;border:1px solid rgba(18,215,209,.35);border-radius:999px;padding:6px 12px;color:var(--cyan);font-size:.78rem;margin-top:8px;}}
    .priority-card {{display:grid;grid-template-columns:58px 1fr auto;align-items:center;gap:14px;padding:17px;border-radius:18px;border:1px solid var(--line);background:var(--surface);margin-bottom:12px;}}
    .priority-card.red {{border-color:rgba(255,80,104,.42);background:linear-gradient(90deg,rgba(255,80,104,.075),transparent);}}
    .priority-card.orange {{border-color:rgba(255,170,54,.42);background:linear-gradient(90deg,rgba(255,170,54,.07),transparent);}}
    .priority-card .ico {{width:48px;height:48px;border:1px solid currentColor;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.35rem;}}
    .priority-card h4 {{margin:0 0 4px;font-size:1.04rem;}} .priority-card p {{margin:0;color:var(--muted);font-size:.82rem;}}
    .risk-pill {{border:1px solid currentColor;border-radius:999px;padding:5px 11px;font-size:.72rem;font-weight:800;white-space:nowrap;}}
    .recommend-box {{border:1px solid transparent;border-radius:24px;padding:25px;background:linear-gradient(var(--surface),var(--surface)) padding-box,linear-gradient(90deg,var(--purple),var(--cyan)) border-box;margin-top:18px;}}
    .recommend-grid {{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px;}}
    .rec-item {{border:1px solid var(--line);border-radius:16px;padding:14px;background:rgba(255,255,255,.012);}}
    .rec-item b {{display:block;color:var(--text);font-size:.88rem;margin:7px 0 4px;}} .rec-item span {{font-size:.77rem;color:var(--muted);line-height:1.5;}}
    .cta-box {{border:1px solid var(--line);border-radius:22px;background:linear-gradient(135deg,rgba(124,77,255,.16),rgba(18,215,209,.08));padding:24px;height:100%;}}
    .metric-strip {{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px;}}
    .metric-card {{border:1px solid var(--line);background:var(--surface);border-radius:16px;padding:16px;}}
    .metric-card b {{font-size:1.55rem;color:var(--cyan);display:block;}} .metric-card span {{font-size:.76rem;color:var(--muted);}}
    div[data-testid="stMetric"] {{border:1px solid var(--line);background:var(--surface);border-radius:18px;padding:14px;}}
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {{background:var(--surface)!important;border-color:var(--line)!important;}}
    .stTextInput input {{color:var(--text)!important;}}
    .small {{font-size:.76rem;color:var(--muted);}}
    .journey-stepper {{display:grid;grid-template-columns:repeat(6,1fr);gap:0;align-items:start;margin:2px 0 26px;}}
    .journey-step {{position:relative;text-align:center;color:var(--muted);font-size:.72rem;}}
    .journey-step:before {{content:"";position:absolute;top:16px;left:-50%;width:100%;height:2px;background:var(--line);z-index:0;}}
    .journey-step:first-child:before {{display:none;}}
    .journey-dot {{position:relative;z-index:1;width:34px;height:34px;border-radius:50%;margin:0 auto 7px;display:flex;align-items:center;justify-content:center;border:1px solid var(--cyan);background:var(--bg);color:var(--cyan);font-weight:800;box-shadow:0 0 0 5px rgba(18,215,209,.035);}}
    .journey-step.done .journey-dot {{background:rgba(18,215,209,.13);}}
    .journey-step.active .journey-dot {{border-color:var(--purple);color:#fff;background:linear-gradient(135deg,var(--purple),#4E23C8);box-shadow:0 0 22px rgba(124,77,255,.42);}}
    .journey-step.active {{color:#CDBEFF;font-weight:800;}}
    .completion-title {{text-align:center;margin:4px 0 22px;}}
    .completion-title h1 {{text-align:center;font-size:2.15rem;margin:.3rem 0 .35rem;}}
    .completion-title p {{text-align:center;color:var(--muted);margin:0;}}
    .result-main-panel {{border:1px solid var(--line);border-radius:22px;padding:18px;background:linear-gradient(145deg,rgba(9,17,32,.96),rgba(6,12,25,.98));height:100%;}}
    .result-section-title {{font-size:1.08rem;font-weight:850;margin-bottom:10px;color:var(--text);}}
    .priority-wrap {{border:1px solid var(--line);border-radius:22px;padding:18px;background:linear-gradient(145deg,rgba(9,17,32,.96),rgba(6,12,25,.98));height:100%;}}
    .priority-card.red {{box-shadow:inset 0 0 28px rgba(255,80,104,.045);}}
    .priority-card.orange {{box-shadow:inset 0 0 28px rgba(255,170,54,.04);}}
    .recommend-mega {{border:1px solid transparent;border-radius:24px;padding:22px;background:linear-gradient(var(--surface),var(--surface)) padding-box,linear-gradient(90deg,var(--purple),var(--cyan)) border-box;box-shadow:0 0 42px rgba(64,91,255,.08);}}
    .shield-orb {{height:220px;border-radius:20px;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle at center,rgba(18,215,209,.16),transparent 35%),radial-gradient(circle at center,rgba(52,135,255,.09),transparent 62%);font-size:6.2rem;color:var(--cyan);text-shadow:0 0 28px rgba(18,215,209,.5);border:1px solid rgba(18,215,209,.10);}}
    .recommend-title {{font-size:2rem;font-weight:900;line-height:1.2;background:linear-gradient(90deg,var(--cyan),#92F7F3);-webkit-background-clip:text;color:transparent;margin:.2rem 0 .65rem;}}
    .safe-strip {{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;}}
    .safe-metric {{border:1px solid var(--line);border-radius:16px;padding:14px;background:var(--surface);}}
    .safe-metric b {{display:block;font-size:1.45rem;color:var(--cyan);}}
    .safe-metric span {{font-size:.76rem;color:var(--muted);}}
    .cta-banner {{border:1px solid rgba(124,77,255,.55);border-radius:20px;padding:22px;background:linear-gradient(135deg,rgba(124,77,255,.22),rgba(18,215,209,.10));height:100%;}}
    .cta-banner h3 {{font-size:1.45rem;margin:.2rem 0 .55rem;}}
    /* V3 reference-inspired screens */
    .hero-center {{max-width:760px;margin:20px auto 0;text-align:center;border:1px solid var(--line);border-radius:30px;padding:34px 40px 28px;background:
      radial-gradient(circle at 50% 24%,rgba(255,80,104,.10),transparent 33%),
      linear-gradient(180deg,rgba(7,13,26,.99),rgba(4,8,18,.99));box-shadow:0 28px 90px rgba(0,0,0,.38);position:relative;overflow:hidden;}}
    .hero-center:before {{content:"";position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent 0 42px,rgba(255,255,255,.012) 43px),repeating-linear-gradient(0deg,transparent 0 42px,rgba(255,255,255,.009) 43px);pointer-events:none;}}
    .hero-center > * {{position:relative;z-index:1;}}
    .hero-status {{max-width:390px;margin:0 auto 18px;border:1px solid rgba(255,80,104,.28);border-radius:14px;padding:13px 18px;background:rgba(255,80,104,.035);box-shadow:0 0 35px rgba(255,80,104,.06);}}
    .hero-status-title {{font-size:.68rem;color:var(--cyan);font-weight:900;letter-spacing:.12em;margin-bottom:5px;}}
    .hero-status-row {{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:.72rem;color:#B8C3D9;}}
    .hero-status-row:last-child {{border-bottom:0}}.hero-status-row b{{color:var(--red);font-weight:900;}}
    .incident-triangle {{width:72px;height:72px;margin:10px auto 12px;display:flex;align-items:center;justify-content:center;font-size:3rem;color:#FFD6D9;filter:drop-shadow(0 0 18px rgba(255,80,104,.65));}}
    .hero-main-title {{font-size:clamp(2rem,4vw,3.25rem);font-weight:950;letter-spacing:-.035em;line-height:1.03;text-align:center;margin:8px 0 5px;color:#F8FAFF;}}
    .hero-main-sub {{font-size:1.25rem;font-weight:800;text-align:center;margin-bottom:13px;color:#F4F7FF;}}
    .hero-copy {{max-width:610px;margin:0 auto;color:var(--muted);text-align:center;line-height:1.7;font-size:.94rem;}}
    .hero-kpis {{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;max-width:570px;margin:22px auto 18px;}}
    .hero-kpi {{border:1px solid var(--line);border-radius:13px;padding:11px 8px;background:rgba(10,18,34,.88)}}
    .hero-kpi b {{display:block;color:var(--cyan);font-size:1rem}}.hero-kpi span{{font-size:.62rem;color:#8F9CB7;text-transform:uppercase;letter-spacing:.06em}}
    .privacy-note {{text-align:center;color:#71809B;font-size:.68rem;margin-top:10px;}}
    .scene-shell {{max-width:930px;margin:0 auto;}}
    .scene-top {{display:flex;align-items:center;gap:14px;margin:2px 0 12px;}}
    .scene-num {{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--purple),#4C25B8);color:white;font-size:.68rem;font-weight:900;box-shadow:0 0 15px rgba(124,77,255,.35)}}
    .scene-label {{font-size:.68rem;font-weight:900;color:#BDAEFF;letter-spacing:.08em;}}
    .seg-progress {{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:6px;flex:1;}}
    .seg {{height:4px;border-radius:999px;background:#1A2942}}.seg.on{{background:linear-gradient(90deg,var(--cyan),#2CC7FF);box-shadow:0 0 10px rgba(18,215,209,.3)}}
    .scenario-time {{color:#6BD9FF;font-size:.78rem;font-weight:800;margin:15px 0 7px;}}
    .scenario-copy {{font-size:1.06rem;color:#76D9FF;font-weight:650;line-height:1.5;max-width:650px;}}
    .scenario-question {{font-size:clamp(1.4rem,2.4vw,2rem);font-weight:900;line-height:1.2;margin:12px 0 6px;color:#F7F9FF;}}
    .scenario-helper {{color:#8392AE;font-size:.78rem;margin-bottom:17px;}}
    div[data-testid="stButton"] > button {{border-radius:12px!important;border:1px solid var(--line)!important;background:linear-gradient(180deg,#0B1425,#08111F)!important;color:#F5F8FF!important;min-height:48px;transition:.18s ease!important;}}
    div[data-testid="stButton"] > button:hover {{border-color:var(--cyan)!important;box-shadow:0 0 0 1px rgba(18,215,209,.25),0 0 24px rgba(18,215,209,.08)!important;transform:translateY(-1px);}}
    div[data-testid="stButton"] > button[kind="primary"] {{background:linear-gradient(90deg,var(--purple),#4D8BEF,var(--cyan))!important;border:0!important;font-weight:900!important;box-shadow:0 10px 30px rgba(55,108,255,.18)!important;}}
    .choice-note {{margin-top:16px;border-top:1px solid var(--line);padding-top:13px;color:#7E8CA8;font-size:.72rem;}}
    .asset-card {{border:1px solid var(--line);border-radius:14px;padding:16px 10px;text-align:center;background:#091323;min-height:105px;margin-bottom:8px;}}
    .asset-icon {{font-size:1.75rem;color:var(--cyan);margin-bottom:7px}}.asset-title{{font-size:.78rem;font-weight:750;color:#EEF3FF;}}
    .dash-head {{display:flex;justify-content:space-between;align-items:end;margin:4px 0 18px}}.dash-head h1{{margin:0}}.dash-sub{{color:var(--muted);font-size:.85rem;}}
    .dash-kpis {{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0 16px}}.dash-kpi{{border:1px solid var(--line);border-radius:16px;padding:16px;background:linear-gradient(180deg,#0B1527,#08111F)}}
    .dash-kpi span{{font-size:.70rem;color:#91A0BD}}.dash-kpi b{{display:block;font-size:1.65rem;color:#F7FAFF;margin-top:4px}}.dash-kpi em{{font-style:normal;color:var(--green);font-size:.68rem;}}
    .chart-card {{border:1px solid var(--line);border-radius:18px;padding:8px 12px;background:#08111F;}}
    .gap-grid {{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:8px 0 18px}}.gap-card{{border:1px solid var(--line);border-radius:16px;padding:12px;background:#08111F;text-align:center}}.gap-card b{{display:block;font-size:1.35rem;color:#F7FAFF}}.gap-card span{{font-size:.66rem;color:#98A5BD;}}
    @media(max-width:900px) {{.incident,.recommend-grid,.timeline,.metric-strip,.safe-strip,.journey-stepper{{grid-template-columns:1fr;}} .journey-step:before{{display:none;}} .mini-grid{{grid-template-columns:1fr 1fr 1fr;}}}}
    </style>
    """, unsafe_allow_html=True)


def top_controls():
    a,b,c = st.columns([6,1.1,1.1])
    with a:
        st.markdown(f"<div class='brand'>◈ {tr('brand')}</div>", unsafe_allow_html=True)
    with b:
        new_lang = st.selectbox("Language", ["en","ar"], index=0 if st.session_state.lang=="en" else 1, format_func=lambda x:"EN" if x=="en" else "عربي", label_visibility="collapsed", key="top_lang")
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang; st.rerun()
    with c:
        new_theme = st.selectbox("Theme", ["Dark","Light"], index=0 if st.session_state.theme=="Dark" else 1, label_visibility="collapsed", key="top_theme")
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme; st.rerun()


def get_option(q, oid):
    return next((o for o in q["options"] if o["id"]==oid), None)


def visible_questions(route):
    return [q for q in QUESTIONS if "all" in q["paths"] or route in q["paths"]]


def average_metric(selected, metric, default=55):
    vals = [o[metric] for o in selected if metric in o]
    return round(sum(vals)/len(vals),1) if vals else default


def calculate_scores(answers):
    selected=[]
    for q in QUESTIONS:
        if q["id"] in answers:
            opt=get_option(q,answers[q["id"]])
            if opt: selected.append(opt)
    route=next((o.get("route") for o in selected if o.get("route")),"explorer")
    eligibility=min(100,sum(o.get("eligibility",0) for o in selected)+sum(o.get("fit",0) for o in selected)+sum(o.get("influence",0) for o in selected))
    influence=min(100,sum(o.get("influence",0) for o in selected)*4)
    fit=min(100,sum(o.get("fit",0) for o in selected)*5)
    need_opts=[o.get("need") for o in selected if "need" in o]
    need=min(100,round((sum(need_opts)/max(1,len(need_opts)))*(100/22))) if need_opts else 0
    dims={
        "asset_control":average_metric(selected,"asset_control"),"continuity":average_metric(selected,"continuity"),
        "exit_readiness":average_metric(selected,"exit_readiness"),"contract_clarity":average_metric(selected,"contract_clarity"),
        "governance":average_metric(selected,"governance"),"provider_assurance":average_metric(selected,"provider_assurance",55),
    }
    if route=="provider":
        readiness=dims["provider_assurance"]*.30+dims["asset_control"]*.20+dims["continuity"]*.20+dims["contract_clarity"]*.15+dims["governance"]*.15
    else:
        readiness=dims["asset_control"]*.27+dims["continuity"]*.24+dims["exit_readiness"]*.20+dims["contract_clarity"]*.15+dims["governance"]*.14
    readiness=max(0,min(100,round(readiness)))
    commercial=max(0,min(100,round(.36*need+.20*eligibility+.16*influence+.13*fit+.15*(100-readiness))))
    if route=="explorer" or eligibility<20: opportunity="General Visitor"
    elif route in ["provider","advisor"] and commercial<65: opportunity="Ecosystem Opportunity"
    elif commercial>=75: opportunity="Priority Opportunity"
    elif commercial>=55: opportunity="Qualified Opportunity"
    else: opportunity="Nurture"
    if route=="provider": persona_key="provider_ready" if readiness>=75 else "provider_growth"
    else:
        persona_key="resilient" if readiness>=80 else "managed" if readiness>=65 else "exposed" if readiness>=45 else "critical"
    priority_map={
        "asset_control":("Critical Asset Access","الوصول إلى الأصول الحرجة"),"continuity":("Recovery Readiness","جاهزية التعافي"),
        "exit_readiness":("Exit & Transition Readiness","جاهزية الخروج والانتقال"),"contract_clarity":("Contract Continuity Clarity","وضوح شروط العقد"),
        "governance":("Evidence & Governance","الحوكمة والأدلة"),"provider_assurance":("Client Assurance","ضمان العملاء"),
    }
    keys=["provider_assurance","asset_control","continuity","contract_clarity","governance"] if route=="provider" else ["asset_control","exit_readiness","contract_clarity","continuity","governance"]
    ranked=sorted(keys,key=lambda k:dims[k])
    return {"route":route,"readiness":readiness,"need":need,"eligibility":eligibility,"influence":influence,"fit":fit,"commercial":commercial,
            "opportunity":opportunity,"persona_key":persona_key,"priority_key":ranked[0],"priority_keys":ranked[:3],"dimensions":dims,
            "priority_en":priority_map[ranked[0]][0],"priority_ar":priority_map[ranked[0]][1],"priority_map":priority_map}


def google_client():
    if gspread is None: return None
    try:
        creds_info=st.secrets.get("gcp_service_account",None)
        if not creds_info: return None
        sheet_name=st.secrets.get("GOOGLE_SHEET_NAME","Technology Continuity Leads")
        scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds=Credentials.from_service_account_info(dict(creds_info),scopes=scopes)
        return gspread.authorize(creds).open(sheet_name)
    except Exception:
        return None


def flatten_record(scores, answers, contact):
    d=scores["dimensions"]
    return {
        "timestamp":datetime.now(timezone.utc).isoformat(),"session_id":st.session_state.session_id,"language":st.session_state.lang,"theme":st.session_state.theme,
        "route":scores["route"],"representation":answers.get("representation",""),"org_scale":answers.get("org_scale",""),"persona":scores["persona_key"],
        "readiness_score":scores["readiness"],"service_need_pct":scores["need"],"eligibility_score":scores["eligibility"],"decision_influence_score":scores["influence"],
        "organization_fit_score":scores["fit"],"commercial_opportunity_score":scores["commercial"],"opportunity_class":scores["opportunity"],"priority_area":scores["priority_key"],
        "asset_control":d["asset_control"],"continuity":d["continuity"],"exit_readiness":d["exit_readiness"],"contract_clarity":d["contract_clarity"],"governance":d["governance"],
        "provider_assurance":d["provider_assurance"],"name":contact.get("name",""),"organization":contact.get("organization",""),"email":contact.get("email",""),"phone":contact.get("phone",""),
        "consent":bool(contact.get("consent",False)),"answers_json":json.dumps(answers,ensure_ascii=False),
    }


def save_record(record):
    sh=google_client()
    if sh:
        try: ws=sh.worksheet("Responses")
        except Exception: ws=sh.add_worksheet(title="Responses",rows=3000,cols=40)
        values=ws.get_all_values(); headers=list(record.keys())
        if not values:
            ws.append_row(headers); values=[headers]
        current=values[0]
        for h in headers:
            if h not in current: current.append(h)
        if current!=values[0]: ws.update("1:1",[current])
        # upsert by session_id
        sid_col=current.index("session_id")+1
        found=None
        if len(values)>1:
            for i,row in enumerate(values[1:],start=2):
                if len(row)>=sid_col and row[sid_col-1]==record["session_id"]: found=i; break
        row=[record.get(h,"") for h in current]
        if found: ws.update(f"A{found}:{chr(64+min(len(current),26))}{found}",[row[:26]]) if len(current)<=26 else ws.update(f"A{found}",[row])
        else: ws.append_row(row,value_input_option="USER_ENTERED")
        return "google"
    path="responses_local.csv"; new=pd.DataFrame([record])
    if os.path.exists(path):
        old=pd.read_csv(path)
        if "session_id" in old.columns and record["session_id"] in old["session_id"].astype(str).values:
            old=old[old["session_id"].astype(str)!=record["session_id"]]
        pd.concat([old,new],ignore_index=True).to_csv(path,index=False)
    else: new.to_csv(path,index=False)
    return "local"


def load_data():
    sh=google_client()
    if sh:
        try: return pd.DataFrame(sh.worksheet("Responses").get_all_records())
        except Exception: pass
    return pd.read_csv("responses_local.csv") if os.path.exists("responses_local.csv") else pd.DataFrame()


def reset_assessment():
    lang,theme=st.session_state.lang,st.session_state.theme
    st.session_state.clear(); st.session_state.lang=lang; st.session_state.theme=theme
    st.session_state.page="intro"; st.session_state.answers={}; st.session_state.q_index=0; st.session_state.session_id=str(uuid.uuid4())


def risk_label(value, lang):
    # readiness dimension value: lower means higher exposure
    if value<40: return ("HIGH","مرتفعة","red")
    if value<65: return ("MEDIUM","متوسطة","orange")
    return ("CONTROLLED","تحت السيطرة","green")


def priority_card(key, value, scores, lang):
    en,ar=scores["priority_map"][key]; label=ar if lang=="ar" else en
    risk_en,risk_ar,cls=risk_label(value,lang); risk=risk_ar if lang=="ar" else risk_en
    descs={
        "asset_control":("Independent access to critical code, data and credentials is not fully assured.","الوصول المستقل إلى الكود والبيانات والصلاحيات الحرجة غير مضمون بالكامل."),
        "exit_readiness":("A practical, testable exit and transition path may need strengthening.","مسار الخروج والانتقال العملي والقابل للاختبار يحتاج إلى تعزيز."),
        "contract_clarity":("Continuity, access and handover obligations may need clearer contractual protection.","التزامات الاستمرارية والوصول والتسليم تحتاج إلى حماية تعاقدية أوضح."),
        "continuity":("Recovery may still depend on external availability when disruption occurs.","التعافي قد يظل معتمدًا على توفر طرف خارجي وقت التعطل."),
        "governance":("Continuity evidence may not be immediately organized and audit-ready.","أدلة الاستمرارية قد لا تكون منظمة وجاهزة للتدقيق فورًا."),
        "provider_assurance":("Enterprise clients may need stronger independent evidence of continuity protection.","عملاء المؤسسات قد يحتاجون إلى أدلة مستقلة أقوى على حماية الاستمرارية."),
    }
    icon={"asset_control":"⌾","exit_readiness":"⇄","contract_clarity":"▤","continuity":"↻","governance":"✓","provider_assurance":"◇"}[key]
    return f"""<div class='priority-card {'red' if cls=='red' else 'orange' if cls=='orange' else ''}'>
      <div class='ico'>{icon}</div><div><h4>{label}</h4><p>{descs[key][1] if lang=='ar' else descs[key][0]}</p></div><div class='risk-pill'>{risk}</div></div>"""

# ============================================================
# STATE
# ============================================================
for k,v in {"lang":"ar","theme":"Dark","page":"intro","answers":{},"q_index":0,"session_id":str(uuid.uuid4())}.items():
    if k not in st.session_state: st.session_state[k]=v

inject_css(st.session_state.theme,st.session_state.lang)
lang=st.session_state.lang

# Hidden team dashboard route: append ?admin=1 to app URL.
admin_mode = str(st.query_params.get("admin", "0")) == "1"
if admin_mode and st.session_state.page not in ["dashboard_login","dashboard"]:
    st.session_state.page="dashboard_login"

top_controls()

# ============================================================
# INTRO / INCIDENT HERO
# ============================================================
if st.session_state.page=="intro":
    st.markdown(f"""
    <div class='hero-center'>
      <div class='hero-status'>
        <div class='hero-status-title'>{'SYSTEM STATUS' if lang=='en' else 'حالة النظام'}</div>
        <div class='hero-status-row'><span>PRODUCTION</span><b>{'DOWN' if lang=='en' else 'متوقف'}</b></div>
        <div class='hero-status-row'><span>DATA ACCESS</span><b>{'NO ACCESS' if lang=='en' else 'لا يوجد وصول'}</b></div>
        <div class='hero-status-row'><span>PROVIDER</span><b>{'UNREACHABLE' if lang=='en' else 'غير متاح'}</b></div>
      </div>
      <div class='incident-triangle'>⚠</div>
      <div class='hero-main-title'>{tr('hero_title')}</div>
      <div class='hero-main-sub'>{tr('hero_sub')}</div>
      <div class='hero-copy'>{tr('hero_body')}</div>
      <div class='hero-kpis'>
        <div class='hero-kpi'><b>2 MIN</b><span>{'ASSESSMENT' if lang=='en' else 'تقييم سريع'}</span></div>
        <div class='hero-kpi'><b>100</b><span>{'READINESS SCORE' if lang=='en' else 'درجة الجاهزية'}</span></div>
        <div class='hero-kpi'><b>{'PERSONALIZED' if lang=='en' else 'مخصص'}</b><span>{'RECOMMENDATION' if lang=='en' else 'توصية'}</span></div>
      </div>
    </div>
    """,unsafe_allow_html=True)
    st.write("")
    c1,c2,c3=st.columns([1.2,3,1.2])
    with c2:
        if st.button(tr("start")+"  →",use_container_width=True,type="primary"):
            st.session_state.page="assessment"; st.rerun()
        st.markdown(f"<div class='privacy-note'>🔒 {'Your responses are confidential and used only to generate your continuity profile.' if lang=='en' else 'إجاباتك سرية وتستخدم فقط لإنشاء ملف جاهزية الاستمرارية الخاص بك.'}</div>",unsafe_allow_html=True)

# ============================================================
# ASSESSMENT
# ============================================================
elif st.session_state.page=="assessment":
    route="all"
    rep=st.session_state.answers.get("representation")
    if rep:
        route=get_option(QUESTIONS[0],rep).get("route","explorer")
        if route=="explorer": st.session_state.page="explorer_result"; st.rerun()
    qs=visible_questions(route); idx=min(st.session_state.q_index,len(qs)-1); q=qs[idx]

    # segmented progress inspired by the reference screens
    segs="".join([f"<div class='seg {'on' if i<=idx else ''}'></div>" for i in range(len(qs))])
    label=("WELCOME" if idx==0 else f"SCENARIO {idx:02d}") if lang=="en" else ("مرحبًا بك" if idx==0 else f"سيناريو {idx:02d}")
    st.markdown(f"<div class='scene-shell'><div class='scene-top'><div class='scene-num'>{idx+1:02d}</div><div class='scene-label'>{label}</div><div class='seg-progress'>{segs}</div></div></div>",unsafe_allow_html=True)
    st.markdown("<div class='scene-shell'>",unsafe_allow_html=True)

    if q["id"]=="representation":
        st.markdown(f"<div class='scenario-time'>{'PROFILE START' if lang=='en' else 'بداية ملفك'}</div><div class='scenario-question'>{q[lang]}</div><div class='scenario-helper'>{q.get('helper_'+lang,'')}</div>",unsafe_allow_html=True)
        opts=q["options"]
        rows=[opts[:3],opts[3:]]
        for row in rows:
            cols=st.columns(len(row),gap="medium")
            for col,opt in zip(cols,row):
                with col:
                    icon_map={"org":"🏢","provider":"⌘","both":"⟲","advisor":"◇","self":"◌"}
                    st.markdown(f"<div class='asset-card'><div class='asset-icon'>{icon_map.get(opt['id'],'◇')}</div><div class='asset-title'>{opt[lang]}</div><div class='small' style='margin-top:5px'>{opt.get('sub_'+lang,'')}</div></div>",unsafe_allow_html=True)
                    if st.button(("Choose" if lang=="en" else "اختيار")+"  →",key=f"choose_{opt['id']}",use_container_width=True):
                        st.session_state.answers[q["id"]]=opt["id"]; st.session_state.q_index+=1; st.rerun()
    else:
        # Story copy first, then the diagnostic question
        if q['id']=='provider_disruption':
            scene_en="Your critical service is unavailable. Your provider isn't responding."; scene_ar="خدمة تقنية حرجة توقفت، والمورد لا يستجيب."
        elif q['id']=='handover':
            scene_en="A replacement technical team is ready. They need everything required to restore the service."; scene_ar="فريق تقني بديل جاهز، ويحتاج كل ما يلزم لاستعادة الخدمة."
        elif q['id']=='exit':
            scene_en="Your organization decides to end the relationship with this provider."; scene_ar="قررت جهتك إنهاء العلاقة مع هذا المورد."
        elif q['id']=='assurance':
            scene_en="A client or regulator asks you to prove continuity if your company becomes unavailable."; scene_ar="طلب منك عميل أو جهة تنظيمية إثبات الاستمرارية إذا تعذر توفر شركتك."
        elif q['id']=='client_request':
            scene_en="An enterprise client is reviewing your continuity protections before signing."; scene_ar="عميل مؤسسي يراجع ضمانات الاستمرارية لديك قبل التعاقد."
        else:
            scene_en="The incident lasts longer than expected. Business impact is increasing."; scene_ar="استمر الحادث أكثر من المتوقع، وبدأ أثره على الأعمال يتصاعد."
        st.markdown(f"<div class='scenario-time'>{q['time']}</div><div class='scenario-copy'>{scene_ar if lang=='ar' else scene_en}</div><div class='scenario-question'>{q[lang]}</div><div class='scenario-helper'>{q.get('helper_'+lang,'')}</div>",unsafe_allow_html=True)

        # Handover is rendered as compact icon cards to visually break the flow like the reference
        if q['id']=='handover':
            icon_map={"complete":"▣","mostly":"▤","partial":"◫","obtain":"⌑","unknown":"?"}
            opts=q['options']
            cols=st.columns(len(opts),gap="small")
            for col,opt in zip(cols,opts):
                with col:
                    st.markdown(f"<div class='asset-card'><div class='asset-icon'>{icon_map.get(opt['id'],'◇')}</div><div class='asset-title'>{opt[lang]}</div></div>",unsafe_allow_html=True)
                    if st.button("✓" if lang=='ar' else "Select",key=f"opt_{q['id']}_{opt['id']}",use_container_width=True):
                        st.session_state.answers[q['id']]=opt['id']; st.session_state.q_index+=1; st.rerun()
        else:
            for n,opt in enumerate(q["options"],start=1):
                if st.button(f"{chr(64+n)}   {opt[lang]}",key=f"opt_{q['id']}_{opt['id']}",use_container_width=True):
                    st.session_state.answers[q["id"]]=opt["id"]
                    if idx==len(qs)-1: st.session_state.page="result"
                    else: st.session_state.q_index+=1
                    st.rerun()
        st.markdown(f"<div class='choice-note'>◈ {'There is no right or wrong answer — we are measuring preparedness, not performance.' if lang=='en' else 'لا توجد إجابة صحيحة أو خاطئة — نحن نقيس الجاهزية، لا الأداء.'}</div>",unsafe_allow_html=True)

    if idx>0:
        st.write("")
        if st.button("← "+tr("back"),key="back_q",type="secondary"):
            st.session_state.q_index=max(0,st.session_state.q_index-1); st.rerun()
    st.markdown("</div>",unsafe_allow_html=True)

# ============================================================
# EXPLORER
# ============================================================
elif st.session_state.page=="explorer_result":
    st.markdown(f"""<div class='hero-wrap'><div class='eyebrow'>DISCOVERY PROFILE</div><div class='hero-title'>{tr('explorer_title')}</div><div class='muted'>{tr('explorer_body')}</div><div class='recommend-box' style='margin-top:24px'><h2>{'Technology continuity starts with one question: who keeps control when a dependency fails?' if lang=='en' else 'تبدأ استمرارية التقنية بسؤال واحد: من يحتفظ بالسيطرة عندما يتعطل أحد الاعتمادات؟'}</h2></div></div>""",unsafe_allow_html=True)
    if not st.session_state.get("explorer_saved"):
        scores={"route":"explorer","readiness":0,"need":0,"eligibility":0,"influence":0,"fit":0,"commercial":0,"opportunity":"General Visitor","persona_key":"explorer","priority_key":"none","dimensions":{"asset_control":0,"continuity":0,"exit_readiness":0,"contract_clarity":0,"governance":0,"provider_assurance":0}}
        try: save_record(flatten_record(scores,st.session_state.answers,{})); st.session_state.explorer_saved=True
        except Exception: pass
    if st.button(tr("new"),use_container_width=True): reset_assessment(); st.rerun()

# ============================================================
# RESULTS
# ============================================================
elif st.session_state.page=="result":
    scores=calculate_scores(st.session_state.answers)
    p=PERSONAS[scores["persona_key"]]
    persona=p[lang]
    desc=p[f"{lang}_desc"]
    service=p[f"service_{lang}"]
    dims=scores["dimensions"]

    # Save anonymous analytics once immediately.
    if not st.session_state.get("result_saved"):
        try:
            save_record(flatten_record(scores,st.session_state.answers,{}))
            st.session_state.result_saved=True
        except Exception:
            pass

    # Journey stepper: visitor-safe only (no hidden commercial metrics).
    steps_ar=["مرحبًا بك","سيناريو 01","سيناريو 02","سيناريو 03","فحص أخير","النتيجة"]
    steps_en=["Welcome","Scenario 01","Scenario 02","Scenario 03","Final check","Result"]
    steps=steps_ar if lang=="ar" else steps_en
    step_html="".join([
        f"<div class='journey-step {'active' if i==5 else 'done'}'><div class='journey-dot'>{'✓' if i<5 else '6'}</div><div>{label}</div></div>"
        for i,label in enumerate(steps)
    ])
    st.markdown(f"<div class='journey-stepper'>{step_html}</div>",unsafe_allow_html=True)

    st.markdown(
        f"<div class='completion-title'><div class='eyebrow'>✓ {'ASSESSMENT COMPLETE' if lang=='en' else 'اكتملت رحلتك'}</div>"
        f"<h1>{'Your technology continuity profile is ready' if lang=='en' else 'اكتمل تقييم جاهزيتك لاستمرارية التقنية'}</h1>"
        f"<p>{'A clear view of your current control, dependencies and first improvement priority.' if lang=='en' else 'هذه نظرة واضحة على مستوى السيطرة الحالي، ونقاط الاعتماد، وما يحتاج اهتمامك أولًا.'}</p></div>",
        unsafe_allow_html=True,
    )

    radar_keys=["provider_assurance","asset_control","continuity","contract_clarity","governance"] if scores["route"]=="provider" else ["asset_control","exit_readiness","contract_clarity","continuity","governance"]
    lab_en={"asset_control":"Asset Control","continuity":"Recovery","exit_readiness":"Exit Readiness","contract_clarity":"Contract Clarity","governance":"Governance","provider_assurance":"Client Assurance"}
    lab_ar={"asset_control":"السيطرة على الأصول","continuity":"التعافي","exit_readiness":"جاهزية الخروج","contract_clarity":"وضوح العقود","governance":"الحوكمة","provider_assurance":"ضمان العملاء"}
    labs=lab_ar if lang=="ar" else lab_en

    left,right=st.columns([1.15,1.0],gap="large")
    with left:
        st.markdown(f"<div class='result-section-title'>{'A complete view of your readiness' if lang=='en' else 'نظرة شاملة على جاهزيتك'}</div>",unsafe_allow_html=True)
        rc1,rc2=st.columns([1,1.08])
        with rc1:
            fig=go.Figure(go.Scatterpolar(
                r=[dims[k] for k in radar_keys]+[dims[radar_keys[0]]],
                theta=[labs[k] for k in radar_keys]+[labs[radar_keys[0]]],
                fill="toself",
                line=dict(color="#7C4DFF",width=2),
                fillcolor="rgba(124,77,255,.34)",
            ))
            fig.update_layout(
                height=300,showlegend=False,margin=dict(l=30,r=30,t=20,b=20),
                paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#A8B4CD",size=11),
                polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(range=[0,100],showticklabels=False,gridcolor="#1C2E4B"),angularaxis=dict(gridcolor="#1C2E4B")),
            )
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        with rc2:
            gauge=go.Figure(go.Indicator(
                mode="gauge+number",value=scores["readiness"],
                number={"suffix":" /100","font":{"size":56,"color":"#F5F8FF"}},
                title={"text":tr("score"),"font":{"size":14,"color":"#F5F8FF"}},
                gauge={
                    "axis":{"range":[0,100],"visible":False},
                    "bar":{"color":"#12D7D1","thickness":.24},"bgcolor":"#101A2B","borderwidth":0,
                    "steps":[{"range":[0,45],"color":"rgba(255,80,104,.20)"},{"range":[45,65],"color":"rgba(255,170,54,.14)"},{"range":[65,100],"color":"rgba(18,215,209,.08)"}],
                },
            ))
            gauge.update_layout(height=230,margin=dict(l=12,r=12,t=45,b=5),paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(gauge,use_container_width=True,config={"displayModeBar":False})
            st.markdown(
                f"<div style='text-align:center;margin-top:-6px'><div class='persona-name' style='text-align:center'>{persona}</div>"
                f"<div class='persona-eng'>{p['en']}</div><div class='muted' style='margin-top:10px;text-align:center;font-size:.85rem'>{desc}</div></div>",
                unsafe_allow_html=True,
            )

    with right:
        st.markdown(f"<div class='result-section-title'>{tr('priorities')}</div>",unsafe_allow_html=True)
        for key in scores["priority_keys"]:
            st.markdown(priority_card(key,dims[key],scores,lang),unsafe_allow_html=True)
        st.markdown(
            f"<div class='option-note' style='margin-top:14px'>⌄ {'These are the first areas to strengthen based on your responses.' if lang=='en' else 'هذه أول المناطق التي تستحق التعزيز بناءً على إجاباتك.'}</div>",
            unsafe_allow_html=True,
        )

    st.write("")
    rec_left,rec_mid,rec_cta=st.columns([.72,1.35,.82],gap="large")
    with rec_left:
        st.markdown("<div class='shield-orb'>◈</div>",unsafe_allow_html=True)
    with rec_mid:
        service_items_ar=[
            ("تحديد الفجوات","نحدد أين تعتمد على جهات خارجية بشكل مفرط."),
            ("تعزيز الوصول والملكية","نرفع جاهزية الوصول إلى أصولك وبياناتك الحرجة."),
            ("خطة خروج وتجربة واقعية","نصمم مسار انتقال قابلًا للاختبار والتنفيذ."),
            ("حوكمة واستمرارية مستدامة","نضع ضوابط وأدلة تساعد على استمرارية التشغيل."),
        ]
        service_items_en=[
            ("Identify hidden gaps","Find where external dependency is highest."),
            ("Strengthen access & ownership","Improve control over critical assets and data."),
            ("Build a tested exit path","Create a practical, executable transition route."),
            ("Sustain governance","Create controls and evidence for continuous resilience."),
        ]
        items=service_items_ar if lang=="ar" else service_items_en
        cards="".join([f"<div class='rec-item'><div style='color:var(--cyan);font-size:1.25rem'>◇</div><b>{a}</b><span>{b}</span></div>" for a,b in items])
        st.markdown(
            f"<div class='eyebrow'>{tr('recommend')}</div><div class='recommend-title'>{service}</div>"
            f"<p class='muted'>{'A focused assessment that turns hidden continuity exposure into a practical protection roadmap.' if lang=='en' else 'تقييم مركز يحول مخاطر الاستمرارية الخفية إلى خارطة حماية عملية وقابلة للتنفيذ.'}</p>"
            f"<div class='recommend-grid'>{cards}</div>",
            unsafe_allow_html=True,
        )
    with rec_cta:
        st.markdown(
            f"<div class='cta-banner'><div class='eyebrow'>{'NEXT STEP' if lang=='en' else 'خطوتك التالية'}</div>"
            f"<h3>{tr('cta')}</h3><p class='muted'>{tr('cta_sub')}</p>"
            f"<div style='margin-top:18px;color:var(--cyan);font-weight:850'>{'Your tailored recommendation is ready.' if lang=='en' else 'توصيتك المخصصة جاهزة.'}</div></div>",
            unsafe_allow_html=True,
        )

    # Visitor-safe summary strip. Hidden lead qualification remains internal only.
    controlled=sum(1 for k in radar_keys if dims[k]>=65)
    attention=sum(1 for k in radar_keys if dims[k]<50)
    st.markdown(
        f"<div class='safe-strip'>"
        f"<div class='safe-metric'><b>{scores['readiness']}/100</b><span>{tr('score')}</span></div>"
        f"<div class='safe-metric'><b>{controlled}/{len(radar_keys)}</b><span>{'Dimensions under stronger control' if lang=='en' else 'أبعاد تحت سيطرة أقوى'}</span></div>"
        f"<div class='safe-metric'><b>{attention}</b><span>{'Priority areas needing attention' if lang=='en' else 'أولويات تحتاج اهتمامًا'}</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    st.markdown(f"### {tr('consult')}")
    x1,x2=st.columns(2)
    with x1:
        name=st.text_input(tr("name"))
        org=st.text_input(tr("org"))
    with x2:
        email=st.text_input(tr("email"))
        phone=st.text_input(tr("phone"))
    consent=st.checkbox(tr("consent"))
    if st.button("🔒  "+tr("save"),use_container_width=True):
        contact={"name":name,"organization":org,"email":email,"phone":phone,"consent":consent} if consent else {"name":"","organization":"","email":"","phone":"","consent":False}
        try:
            target=save_record(flatten_record(scores,st.session_state.answers,contact))
            st.success(tr("saved")+("  • Google Sheets ✓" if target=="google" else "  • Local demo ✓"))
        except Exception as e:
            st.error(str(e))
    if st.button("↻  "+tr("new"),use_container_width=True,type="secondary"):
        reset_assessment()
        st.rerun()

# ============================================================
# TEAM DASHBOARD (hidden from visitor navigation; use ?admin=1)
# ============================================================
elif st.session_state.page=="dashboard_login":
    st.markdown(f"<div class='hero-wrap'><div class='eyebrow'>INTERNAL ACCESS</div><div class='hero-title'>{tr('team')}</div><div class='muted'>{'This area is for the event team and commercial follow-up only.' if lang=='en' else 'هذه المنطقة مخصصة لفريق المؤتمر والمتابعة التجارية فقط.'}</div></div>",unsafe_allow_html=True)
    configured=st.secrets.get("DASHBOARD_PASSWORD","")
    pwd=st.text_input(tr("password"),type="password")
    if st.button("▣  "+tr("open"),use_container_width=True):
        if not configured or pwd==configured: st.session_state.page="dashboard"; st.rerun()
        else: st.error("Incorrect password / كلمة المرور غير صحيحة")

elif st.session_state.page=="dashboard":
    df=load_data()
    st.markdown(f"<div class='dash-head'><div><div class='eyebrow'>LIVE EVENT INTELLIGENCE</div><h1>{tr('team')}</h1><div class='dash-sub'>{'Persona, service-need and opportunity intelligence from visitor interactions.' if lang=='en' else 'ذكاء الشخصيات والاحتياج والفرص من تفاعلات زوار المؤتمر.'}</div></div><div class='small'>INTERNAL • LIVE</div></div>",unsafe_allow_html=True)
    if df.empty:
        st.info("No response data yet / لا توجد بيانات حتى الآن")
    else:
        for col in ["readiness_score","service_need_pct","eligibility_score","commercial_opportunity_score","asset_control","exit_readiness","contract_clarity","continuity","governance"]:
            if col in df.columns: df[col]=pd.to_numeric(df[col],errors="coerce")
        f1,f2=st.columns(2)
        with f1:
            classes=sorted(df["opportunity_class"].dropna().astype(str).unique()) if "opportunity_class" in df else []
            chosen=st.multiselect("Opportunity / الفرصة",classes,default=classes)
        with f2:
            routes=sorted(df["route"].dropna().astype(str).unique()) if "route" in df else []
            chosen_routes=st.multiselect("Route / المسار",routes,default=routes)
        dff=df.copy()
        if chosen: dff=dff[dff["opportunity_class"].isin(chosen)]
        if chosen_routes: dff=dff[dff["route"].isin(chosen_routes)]
        total=len(dff)
        qualified=int(dff["opportunity_class"].isin(["Priority Opportunity","Qualified Opportunity"]).sum()) if total else 0
        priority=int((dff["opportunity_class"]=="Priority Opportunity").sum()) if total else 0
        avg_need=round(dff["service_need_pct"].mean(),1) if total else 0
        avg_ready=round(dff["readiness_score"].mean(),1) if total else 0
        ecosystem=int((dff["opportunity_class"]=="Ecosystem Opportunity").sum()) if total else 0
        st.markdown(f"<div class='dash-kpis'><div class='dash-kpi'><span>{'TOTAL VISITORS' if lang=='en' else 'إجمالي الزوار'}</span><b>{total}</b><em>LIVE</em></div><div class='dash-kpi'><span>{'QUALIFIED ORGANIZATIONS' if lang=='en' else 'الجهات المؤهلة'}</span><b>{qualified}</b><em>{round(qualified/max(total,1)*100)}%</em></div><div class='dash-kpi'><span>{'PRIORITY OPPORTUNITIES' if lang=='en' else 'فرص عالية الأولوية'}</span><b>{priority}</b><em>{round(priority/max(total,1)*100)}%</em></div><div class='dash-kpi'><span>{'AVG. SERVICE NEED' if lang=='en' else 'متوسط الاحتياج للخدمة'}</span><b>{avg_need}%</b><em>Need</em></div></div>",unsafe_allow_html=True)

        c1,c2,c3=st.columns([1.05,1.25,1.05],gap="medium")
        with c1:
            if "persona" in dff and total:
                p=dff.groupby("persona").size().reset_index(name="count"); p["label"]=p["persona"].map(lambda x:PERSONAS.get(str(x),{}).get(lang,str(x)))
                fig=px.pie(p,names="label",values="count",hole=.62,title="Visitors by Persona / الزوار حسب الشخصية",color_discrete_sequence=["#12D7D1","#7C4DFF","#3487FF","#FFAA36","#FF5068"]); fig.update_layout(height=330,paper_bgcolor="rgba(0,0,0,0)",font_color="#91A0BD",legend=dict(font=dict(size=9)),margin=dict(l=10,r=10,t=45,b=5)); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        with c2:
            if "persona" in dff and total:
                n=dff.groupby("persona",as_index=False)["service_need_pct"].mean(); n["label"]=n["persona"].map(lambda x:PERSONAS.get(str(x),{}).get(lang,str(x)))
                n=n.sort_values("service_need_pct")
                fig=px.bar(n,x="service_need_pct",y="label",orientation="h",range_x=[0,100],title="Service Need by Persona / الاحتياج حسب الشخصية",color="service_need_pct",color_continuous_scale=[[0,"#12D7D1"],[.6,"#FFAA36"],[1,"#FF5068"]]); fig.update_layout(height=330,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#91A0BD",coloraxis_showscale=False,margin=dict(l=10,r=10,t=45,b=20),xaxis=dict(gridcolor="#14233A")); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        with c3:
            if "opportunity_class" in dff and total:
                o=dff.groupby("opportunity_class").size().reset_index(name="count")
                fig=px.pie(o,names="opportunity_class",values="count",hole=.62,title="Opportunity Distribution / توزيع الفرص",color_discrete_sequence=["#FF5068","#FFAA36","#12D7D1","#7C4DFF","#3487FF"]); fig.update_layout(height=330,paper_bgcolor="rgba(0,0,0,0)",font_color="#91A0BD",legend=dict(font=dict(size=9)),margin=dict(l=10,r=10,t=45,b=5)); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

        st.markdown(f"### {'Gap Analysis — Top Findings' if lang=='en' else 'تحليل الفجوات — أبرز النتائج'}")
        gap_cols=[c for c in ["asset_control","exit_readiness","contract_clarity","continuity","governance"] if c in dff.columns]
        gap_names={"asset_control":("Asset Access Gaps","فجوات الوصول للأصول"),"exit_readiness":("Exit Readiness Gaps","فجوات جاهزية الخروج"),"contract_clarity":("Contract Clarity Gaps","فجوات وضوح العقود"),"continuity":("Recovery Readiness","فجوات التعافي"),"governance":("Evidence & Audit Gaps","فجوات الأدلة والتدقيق")}
        colors=["#7C4DFF","#FF5068","#FFAA36","#32A8FF","#20D8A4"]
        cols=st.columns(len(gap_cols),gap="small") if gap_cols else []
        for i,(col,k) in enumerate(zip(cols,gap_cols)):
            exposure=round((dff[k]<50).mean()*100) if total else 0
            with col:
                fig=go.Figure(go.Pie(values=[exposure,100-exposure],hole=.72,sort=False,textinfo="none",marker=dict(colors=[colors[i%len(colors)],"#132139"])))
                fig.update_layout(height=145,showlegend=False,margin=dict(l=3,r=3,t=4,b=3),paper_bgcolor="rgba(0,0,0,0)",annotations=[dict(text=f"<b>{exposure}%</b>",x=.5,y=.5,showarrow=False,font=dict(size=20,color="#F7FAFF"))])
                st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
                st.markdown(f"<div style='text-align:center;margin-top:-22px;font-size:.72rem;color:#A3AFC4'>{gap_names[k][1] if lang=='ar' else gap_names[k][0]}</div>",unsafe_allow_html=True)

        st.markdown(f"### {'Lead & Follow-up Table' if lang=='en' else 'جدول الفرص والمتابعة'}")
        show=[c for c in ["timestamp","organization","name","route","persona","readiness_score","service_need_pct","commercial_opportunity_score","opportunity_class","priority_area","email","phone"] if c in dff.columns]
        if "commercial_opportunity_score" in dff: dff=dff.sort_values("commercial_opportunity_score",ascending=False)
        st.dataframe(dff[show],use_container_width=True,hide_index=True,height=310)
        st.download_button("Download CSV / تحميل CSV",dff.to_csv(index=False).encode("utf-8-sig"),"continuity_leads.csv","text/csv",use_container_width=True)

