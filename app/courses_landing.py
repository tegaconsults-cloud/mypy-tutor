"""
Dynamic Jinja2 SSR course landing pages for all 17 MyPy Tutor courses.
"""

from jinja2 import Environment
from app.courses import COURSE_CATALOG, COURSES, TIER_PLANS

# ---------------------------------------------------------------------------
# Human-readable titles for each course slug
# ---------------------------------------------------------------------------
SLUG_TO_TITLE: dict[str, str] = {
    "python-fundamentals":       "Python Fundamentals",
    "python-strings":            "Python Strings & Text Processing",
    "python-collections":        "Python Collections",
    "python-control-flow":       "Python Control Flow",
    "python-functions-advanced": "Advanced Python Functions",
    "python-oop":                "Object-Oriented Python",
    "python-modules-stdlib":     "Python Modules & Standard Library",
    "python-dsa":                "Data Structures & Algorithms",
    "numpy-mastery":             "NumPy Mastery",
    "pandas-mastery":            "Pandas Mastery",
    "data-science-python":       "Data Science with Python",
    "python-databases":          "Python Databases",
    "web-apis":                  "Web APIs with Python",
    "prompt-engineering":        "Prompt Engineering",
    "ai-prompt-engineering":     "AI & Prompt Engineering",
    "machine-learning":          "Machine Learning with Python",
    "ai-automation":             "AI Automation with Python",
}

# ---------------------------------------------------------------------------
# Jinja2 HTML template — fully self-contained (CSS + JS embedded)
# All JS template literals replaced with string concatenation to avoid
# conflict with Jinja2 {{ }} delimiters.
# ---------------------------------------------------------------------------
COURSE_LANDING_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{ course_title }} Course — MyPy Tutor</title>
<meta name="description" content="{{ course_title }} — {{ category }}. {{ step_count }} lessons. By Teamsamikoko Global Academy."/>
<link rel="icon" type="image/jpeg" href="https://mypytutor.onrender.com/static/icons/mypytutor_logo.jpg"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{
  --bg:#07090f;--surface:#0d1120;--card:#111827;--elevated:#1a2235;
  --border:rgba(255,255,255,0.07);
  --accent:#3b82f6;--accent2:#8b5cf6;--gold:#f59e0b;--green:#10b981;
  --text:#f1f5f9;--muted:#64748b;--sub:#94a3b8;
  --radius:14px;--font:'Inter',-apple-system,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:var(--font);background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased;line-height:1.6}

/* ── Backgrounds ── */
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background:radial-gradient(ellipse 80% 60% at 50% -15%,rgba(59,130,246,.12),transparent),
             radial-gradient(ellipse 60% 50% at 85% 80%,rgba(139,92,246,.08),transparent),
             radial-gradient(ellipse 40% 30% at 10% 60%,rgba(16,185,129,.05),transparent);}
body::after{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:radial-gradient(rgba(255,255,255,.018) 1px,transparent 1px);
  background-size:28px 28px;}

/* ── Layout ── */
.wrap{position:relative;z-index:1;max-width:1080px;margin:0 auto;padding:0 20px}

/* ── Nav ── */
nav{position:sticky;top:0;z-index:100;background:rgba(7,9,15,.92);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);padding:14px 0}
.nav-inner{display:flex;align-items:center;justify-content:space-between;gap:12px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none}
.brand-logo{width:38px;height:38px;border-radius:50%;overflow:hidden;
  border:2px solid rgba(59,130,246,.5);box-shadow:0 0 14px rgba(59,130,246,.3);flex-shrink:0}
.brand-logo img{width:100%;height:100%;object-fit:cover;display:block}
.brand-name{font-weight:800;font-size:1rem;letter-spacing:-.02em;
  background:linear-gradient(135deg,#60a5fa,#a78bfa);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.nav-cta{display:flex;gap:8px;align-items:center}
.btn{display:inline-block;padding:9px 22px;border-radius:var(--radius);font-size:.85rem;
  font-weight:700;cursor:pointer;text-decoration:none;transition:all .15s;border:none;font-family:var(--font)}
.btn-primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;
  box-shadow:0 4px 14px rgba(59,130,246,.35)}
.btn-primary:hover{transform:translateY(-1px);filter:brightness(1.08)}
.btn-outline{background:transparent;color:var(--sub);border:1px solid var(--border)}
.btn-outline:hover{border-color:rgba(59,130,246,.5);color:#93c5fd}

/* ── Hero ── */
.hero{padding:96px 0 72px;text-align:center}
.hero-badge{display:inline-flex;align-items:center;gap:6px;
  background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.25);
  color:#93c5fd;border-radius:999px;padding:5px 14px;font-size:.75rem;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;margin-bottom:24px}
.hero h1{font-size:clamp(2.2rem,5vw,3.6rem);font-weight:900;letter-spacing:-.04em;line-height:1.1;
  margin-bottom:20px}
.hero h1 span{background:linear-gradient(135deg,#60a5fa,#a78bfa,#34d399);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:1.05rem;color:var(--sub);max-width:640px;margin:0 auto 32px;line-height:1.7}
.hero-stats{display:flex;justify-content:center;gap:32px;flex-wrap:wrap;margin-top:40px}
.stat{text-align:center}
.stat-v{font-size:1.6rem;font-weight:800;color:var(--accent);letter-spacing:-.03em}
.stat-l{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;font-weight:600;margin-top:2px}

/* ── Section titles ── */
.section{padding:72px 0}
.section-tag{display:inline-block;font-size:.72rem;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--accent);margin-bottom:10px}
.section-title{font-size:clamp(1.5rem,3vw,2rem);font-weight:800;letter-spacing:-.03em;margin-bottom:10px}
.section-sub{color:var(--sub);max-width:580px;line-height:1.7;font-size:.95rem}
.section-divider{border:none;border-top:1px solid var(--border);margin:0}

/* ── Modules ── */
.modules{margin-top:40px;display:flex;flex-direction:column;gap:14px}
.module{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  overflow:hidden;transition:border-color .15s}
.module:hover{border-color:rgba(59,130,246,.3)}
.module-header{display:flex;align-items:flex-start;gap:16px;padding:20px 22px;cursor:pointer;
  user-select:none}
.module-num{flex-shrink:0;width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:flex;align-items:center;justify-content:center;
  font-size:.75rem;font-weight:800;color:#fff}
.module-info{flex:1;min-width:0}
.module-title{font-size:.95rem;font-weight:700;color:var(--text);margin-bottom:4px}
.module-meta{font-size:.74rem;color:var(--muted);display:flex;gap:12px;flex-wrap:wrap}
.module-meta span{display:flex;align-items:center;gap:4px}
.module-chevron{flex-shrink:0;color:var(--muted);font-size:.8rem;transition:transform .2s;margin-top:2px}
.module.open .module-chevron{transform:rotate(180deg)}
.module-body{display:none;padding:0 22px 20px;border-top:1px solid var(--border)}
.module.open .module-body{display:block}
.lesson-list{margin-top:14px;display:flex;flex-direction:column;gap:6px}
.lesson{display:flex;align-items:flex-start;gap:10px;padding:8px 0;
  border-bottom:1px solid rgba(255,255,255,.04)}
.lesson:last-child{border-bottom:none}
.lesson-type{flex-shrink:0;padding:2px 8px;border-radius:999px;font-size:.64rem;font-weight:700;
  letter-spacing:.04em;text-transform:uppercase;min-width:62px;text-align:center}
.lt-concept{background:rgba(59,130,246,.12);color:#93c5fd;border:1px solid rgba(59,130,246,.25)}
.lt-exercise{background:rgba(245,158,11,.1);color:#fcd34d;border:1px solid rgba(245,158,11,.25)}
.lt-project{background:rgba(16,185,129,.1);color:#6ee7b7;border:1px solid rgba(16,185,129,.25)}
.lt-quiz{background:rgba(139,92,246,.1);color:#c4b5fd;border:1px solid rgba(139,92,246,.25)}
.lesson-text{flex:1;font-size:.8rem;color:var(--sub);line-height:1.55}
.lesson-text strong{color:var(--text);font-weight:600}

/* ── Pricing ── */
.pricing-box{background:var(--card);border:1px solid var(--border);border-radius:20px;
  padding:36px;margin-top:36px;position:relative;overflow:hidden}
.pricing-box::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--accent),var(--accent2))}
.pricing-badge{display:inline-block;background:linear-gradient(135deg,rgba(245,158,11,.15),rgba(245,158,11,.05));
  border:1px solid rgba(245,158,11,.3);color:#fcd34d;
  border-radius:999px;padding:4px 14px;font-size:.72rem;font-weight:700;margin-bottom:20px}
.price-row{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}
.price-main{font-size:2.4rem;font-weight:900;color:var(--text);letter-spacing:-.04em}
.price-label{font-size:.85rem;color:var(--muted)}
.price-note{font-size:.8rem;color:var(--sub);margin-bottom:24px;line-height:1.6}
.features{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:28px}
@media(max-width:520px){.features{grid-template-columns:1fr}}
.feature{display:flex;align-items:flex-start;gap:8px;font-size:.82rem;color:var(--sub)}
.feature-check{color:var(--green);flex-shrink:0;margin-top:1px}
.pricing-also{font-size:.8rem;color:var(--muted);text-align:center;margin-top:16px}
.pricing-also a{color:var(--accent);text-decoration:none}

/* ── Instructor ── */
.instructor{display:flex;align-items:flex-start;gap:24px;background:var(--card);
  border:1px solid var(--border);border-radius:var(--radius);padding:28px;margin-top:36px}
.instructor-avatar{width:72px;height:72px;border-radius:50%;overflow:hidden;flex-shrink:0;
  border:2px solid rgba(59,130,246,.4);box-shadow:0 0 18px rgba(59,130,246,.2)}
.instructor-avatar img{width:100%;height:100%;object-fit:cover;display:block}
.instructor-name{font-size:1rem;font-weight:800;color:var(--text);margin-bottom:4px}
.instructor-title{font-size:.78rem;color:var(--accent);margin-bottom:10px;font-weight:600}
.instructor-bio{font-size:.82rem;color:var(--sub);line-height:1.65}

/* ── FAQ ── */
.faq{margin-top:36px;display:flex;flex-direction:column;gap:10px}
.faq-item{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  overflow:hidden}
.faq-q{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:16px 20px;cursor:pointer;font-size:.88rem;font-weight:600;color:var(--text);user-select:none}
.faq-q:hover{background:rgba(255,255,255,.02)}
.faq-chevron{flex-shrink:0;color:var(--muted);transition:transform .2s}
.faq-item.open .faq-chevron{transform:rotate(180deg)}
.faq-a{display:none;padding:0 20px 16px;font-size:.82rem;color:var(--sub);line-height:1.7;
  border-top:1px solid var(--border)}
.faq-item.open .faq-a{display:block}

/* ── CTA band ── */
.cta-band{padding:80px 0;text-align:center}
.cta-band h2{font-size:clamp(1.6rem,3vw,2.2rem);font-weight:900;letter-spacing:-.03em;margin-bottom:14px}
.cta-band p{color:var(--sub);max-width:500px;margin:0 auto 32px;line-height:1.7}
.cta-buttons{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}

/* ── Footer ── */
footer{border-top:1px solid var(--border);padding:28px 0;text-align:center}
footer p{font-size:.76rem;color:var(--muted);line-height:1.8}
footer a{color:var(--sub);text-decoration:none}
footer a:hover{color:var(--accent)}

@media(max-width:640px){
  .hero{padding:72px 0 48px}
  .hero-stats{gap:20px}
  .stat-v{font-size:1.3rem}
  .instructor{flex-direction:column}
  .module-meta{gap:8px}
  .nav-cta .btn-outline{display:none}
}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="wrap">
    <div class="nav-inner">
      <a class="brand" href="https://mypytutor.com.ng">
        <div class="brand-logo">
          <img src="https://mypytutor.onrender.com/static/icons/mypytutor_logo.jpg"
               alt="MyPy Tutor" onerror="this.src='https://mypytutor.onrender.com/static/icons/mypytutor_logo.png'"/>
        </div>
        <span class="brand-name">MyPy Tutor</span>
      </a>
      <div class="nav-cta">
        <a class="btn btn-outline" href="https://mypytutor.com.ng">&#8592; All Courses</a>
        <a class="btn btn-primary" href="#" onclick="openCheckout(event)">Enrol Now &#8212; &#8358;{{ "{:,}".format(price_ngn) }}</a>
      </div>
    </div>
  </div>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="wrap">
    <div class="hero-badge">{{ badge }} &nbsp;&middot;&nbsp; {{ category }}</div>
    <h1>{{ course_title }} <span>Course</span></h1>
    <p class="hero-sub">
      Master <strong>{{ course_title }}</strong> with hands-on steps, real exercises,
      and AI-powered feedback from Sir. Tega &#8212; available 24/7 on the platform.
    </p>
    <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
      <a class="btn btn-primary" href="#" onclick="openCheckout(event)"
         style="font-size:.95rem;padding:12px 28px">&#128640; Enrol Now &#8212; &#8358;{{ "{:,}".format(price_ngn) }} one-time</a>
      <a class="btn btn-outline" href="#curriculum"
         style="font-size:.95rem;padding:12px 28px">&#128218; See Curriculum</a>
    </div>
    <div class="hero-stats">
      <div class="stat"><div class="stat-v">{{ step_count }}</div><div class="stat-l">Steps</div></div>
      <div class="stat"><div class="stat-v">{{ concept_count }}</div><div class="stat-l">Concepts</div></div>
      <div class="stat"><div class="stat-v">{{ exercise_count }}</div><div class="stat-l">Exercises</div></div>
      <div class="stat"><div class="stat-v">{{ quiz_count + codegen_count }}</div><div class="stat-l">Quizzes &amp; Projects</div></div>
      <div class="stat"><div class="stat-v">&#8734;</div><div class="stat-l">Lifetime Access</div></div>
    </div>
  </div>
</section>

<hr class="section-divider"/>

<!-- CURRICULUM -->
<section class="section" id="curriculum">
  <div class="wrap">
    <div class="section-tag">Curriculum</div>
    <h2 class="section-title">{{ step_count }} Steps &middot; {{ concept_count }} Concepts &middot; {{ exercise_count }} Exercises &middot; {{ quiz_count + codegen_count }} Projects</h2>
    <p class="section-sub">Every step has a clear explanation, hands-on practice, and instant AI feedback from Sir. Tega.</p>

    <div class="modules">
      <div class="module open">
        <div class="module-header" onclick="toggleModule(this)">
          <div class="module-num">&#9776;</div>
          <div class="module-info">
            <div class="module-title">{{ course_title }} &#8212; All {{ step_count }} Steps</div>
            <div class="module-meta">
              <span>&#128218; {{ concept_count }} concepts</span>
              <span>&#9998; {{ exercise_count }} exercises</span>
              <span>&#127890; {{ quiz_count }} quizzes</span>
              <span>&#127959; {{ codegen_count }} projects</span>
            </div>
          </div>
          <div class="module-chevron">&#9660;</div>
        </div>
        <div class="module-body">
          <div class="lesson-list">
            {% for step in steps %}
            {% if step.intent == "concept" %}
            <div class="lesson">
              <span class="lesson-type lt-concept">Concept</span>
              <div class="lesson-text"><strong>{{ step.title }}</strong> &#8212; {{ step.description }}</div>
            </div>
            {% elif step.intent == "exercise" %}
            <div class="lesson">
              <span class="lesson-type lt-exercise">Exercise</span>
              <div class="lesson-text"><strong>{{ step.title }}</strong> &#8212; {{ step.description }}</div>
            </div>
            {% elif step.intent == "quiz" %}
            <div class="lesson">
              <span class="lesson-type lt-quiz">Quiz</span>
              <div class="lesson-text"><strong>{{ step.title }}</strong> &#8212; {{ step.description }}</div>
            </div>
            {% else %}
            <div class="lesson">
              <span class="lesson-type lt-project">Project</span>
              <div class="lesson-text"><strong>{{ step.title }}</strong> &#8212; {{ step.description }}</div>
            </div>
            {% endif %}
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<hr class="section-divider"/>

<!-- PRICING -->
<section class="section">
  <div class="wrap">
    <div class="section-tag">Pricing</div>
    <h2 class="section-title">One payment. Lifetime access.</h2>
    <p class="section-sub">No monthly fees. Pay once and learn at your own pace forever &#8212; including all future updates to the course.</p>
    <div class="pricing-box">
      <div class="pricing-badge">&#11088; {{ tier_name }}</div>
      <div class="price-row">
        <span class="price-main">&#8358;{{ "{:,}".format(price_ngn) }}</span>
        <span class="price-label">one-time &middot; lifetime access</span>
      </div>
      <p class="price-note">
        {{ bundle_text }}
      </p>
      <div class="features">
        <div class="feature"><span class="feature-check">&#10003;</span><span>{{ step_count }} step-by-step lessons</span></div>
        <div class="feature"><span class="feature-check">&#10003;</span><span>Real-world exercises &amp; projects</span></div>
        <div class="feature"><span class="feature-check">&#10003;</span><span>{{ quiz_count + codegen_count }} quizzes &amp; capstone projects</span></div>
        <div class="feature"><span class="feature-check">&#10003;</span><span>Taught by Sir. Tega AI &#8212; always available</span></div>
        <div class="feature"><span class="feature-check">&#10003;</span><span>Ask Sir. Tega any question, any time</span></div>
        <div class="feature"><span class="feature-check">&#10003;</span><span>Progress tracking and XP badges</span></div>
        <div class="feature"><span class="feature-check">&#10003;</span><span>Verifiable certificate on completion</span></div>
        <div class="feature"><span class="feature-check">&#10003;</span><span>Free future course updates forever</span></div>
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <a class="btn btn-primary" href="#" onclick="openCheckout(event)"
           style="font-size:.95rem;padding:13px 32px;flex:1;min-width:200px;text-align:center">
          &#128640; Enrol Now &#8212; &#8358;{{ "{:,}".format(price_ngn) }}
        </a>
        <a class="btn btn-outline" href="https://mypytutor.com.ng"
           style="font-size:.88rem;padding:13px 20px;text-align:center">
          Start Free (10 prompts/day)
        </a>
      </div>
      <p class="pricing-also">
        Payment via Paystack or bank transfer &#8212; Zenith Bank &middot; Teamsamikoko Global Academy &middot; <strong>1228732577</strong><br/>
        Questions? Use the <a href="https://mypytutor.com.ng">Support/Enquiry form</a> on the platform.
      </p>
    </div>
  </div>
</section>

<hr class="section-divider"/>

<!-- INSTRUCTOR -->
<section class="section">
  <div class="wrap">
    <div class="section-tag">Your Instructor</div>
    <h2 class="section-title">Learn from Sir. Tega</h2>
    <div class="instructor">
      <div class="instructor-avatar">
        <img src="https://mypytutor.onrender.com/static/icons/mypytutor_logo.jpg"
             alt="Sir. Tega" onerror="this.src='https://mypytutor.onrender.com/static/icons/mypytutor_logo.png'"/>
      </div>
      <div>
        <div class="instructor-name">Amb. Samuel Atulegwu Nwosu (Sir. Tega)</div>
        <div class="instructor-title">Founder &amp; CEO &#8212; TeamTega Technologies Limited &amp; Teamsamikoko Global Academy</div>
        <p class="instructor-bio">
          Sir. Tega is a Nigerian technology entrepreneur, software developer, AI/ML engineer, and educationist.
          He designed and built the entire MyPy Tutor platform &#8212; including the AI tutoring engine, course curriculum,
          payment system, and certification infrastructure. His vision is to make world-class Python and AI education
          accessible and affordable to every learner in Africa.<br/><br/>
          As your AI-powered tutor, <strong>Sir. Tega is available 24/7</strong> on the platform &#8212; answering questions,
          grading exercises, reviewing your code, and guiding you through every single step of this course in real time.
        </p>
      </div>
    </div>
  </div>
</section>

<hr class="section-divider"/>

<!-- FAQ -->
<section class="section">
  <div class="wrap">
    <div class="section-tag">FAQ</div>
    <h2 class="section-title">Common questions</h2>
    <div class="faq">

      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">
          Do I need prior Python experience? <span class="faq-chevron">&#9660;</span>
        </div>
        <div class="faq-a">{{ faq_prereq_answer }}</div>
      </div>

      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">
          What tools will I need installed? <span class="faq-chevron">&#9660;</span>
        </div>
        <div class="faq-a">Python 3.10+, VS Code (or any editor), and a Groq API key (free tier available). Sir. Tega will walk you through every setup step at the start of the course.</div>
      </div>

      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">
          Can I get a certificate? <span class="faq-chevron">&#9660;</span>
        </div>
        <div class="faq-a">Yes. On completing the final quiz and capstone project, you earn a verifiable certificate issued by Teamsamikoko Global Academy (Reg No: 3508656). The certificate is available as a PDF and can be verified online at mypytutor.com.ng.</div>
      </div>

      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">
          Is there a monthly subscription? <span class="faq-chevron">&#9660;</span>
        </div>
        <div class="faq-a">No. MyPy Tutor uses a one-time payment model. Pay &#8358;{{ "{:,}".format(price_ngn) }} once and you have lifetime access to this course including all future updates. There is no monthly fee.</div>
      </div>

      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">
          What if I get stuck or have questions? <span class="faq-chevron">&#9660;</span>
        </div>
        <div class="faq-a">Sir. Tega is your AI tutor inside the platform &#8212; available 24/7. Ask any question about the course content and get a detailed, personalised answer instantly. You can also submit an enquiry through the Support form on the platform.</div>
      </div>

      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">
          Is this course included in a bundle? <span class="faq-chevron">&#9660;</span>
        </div>
        <div class="faq-a">Yes. {{ bundle_text }}</div>
      </div>

    </div>
  </div>
</section>

<!-- CTA BAND -->
<section class="cta-band">
  <div class="wrap">
    <h2>Ready to master {{ course_title }}?</h2>
    <p>Join learners across Africa building real Python skills with AI-powered guidance. Pay once. Learn forever. Build things that matter.</p>
    <div class="cta-buttons">
      <a class="btn btn-primary" href="#" onclick="openCheckout(event)"
         style="font-size:1rem;padding:14px 36px">&#128640; Enrol Now &#8212; &#8358;{{ "{:,}".format(price_ngn) }}</a>
      <a class="btn btn-outline" href="https://mypytutor.com.ng"
         style="font-size:1rem;padding:14px 28px">Try Free First</a>
    </div>
  </div>
</section>

<!-- FOOTER -->
<footer>
  <div class="wrap">
    <p>
      <strong>MyPy Tutor</strong> &#8212; Africa's AI-Powered Python &amp; Machine Learning Tutor<br/>
      Built by <a href="https://mypytutor.com.ng">TeamTega Technologies Limited</a> &middot;
      Certificates issued by <strong>Teamsamikoko Global Academy</strong> (Reg No: 3508656)<br/>
      <a href="https://mypytutor.com.ng">mypytutor.com.ng</a> &middot;
      Payment via Paystack or bank transfer &#8212; Zenith Bank &middot; 1228732577
    </p>
  </div>
</footer>

<script>
function toggleModule(header) {
  var mod = header.parentElement;
  mod.classList.toggle('open');
}
function toggleFaq(qEl) {
  var item = qEl.parentElement;
  item.classList.toggle('open');
}
</script>

<!-- ── Checkout Modal ──────────────────────────────────────────────────── -->
<div id="checkout-overlay" style="display:none;position:fixed;inset:0;z-index:2000;
  background:rgba(0,0,0,.72);backdrop-filter:blur(6px);
  align-items:center;justify-content:center;padding:16px;">
  <div style="background:#0d1120;border:1px solid rgba(245,158,11,.25);border-radius:18px;
    max-width:480px;width:100%;padding:32px 28px;position:relative;
    box-shadow:0 24px 80px rgba(0,0,0,.7);animation:ciSlideUp .35s ease both;">
    <button onclick="closeCheckout()" style="position:absolute;top:14px;right:16px;
      background:none;border:none;color:#64748b;font-size:1.3rem;cursor:pointer;line-height:1;">&#10005;</button>

    <div style="text-align:center;margin-bottom:18px;">
      <div style="font-size:2rem;margin-bottom:6px;">{{ badge }}</div>
      <h3 style="color:#fcd34d;font-size:1.1rem;font-weight:800;margin:0 0 4px;">{{ course_title }} Course</h3>
      <p style="color:#64748b;font-size:.82rem;margin:0;">&#8358;{{ "{:,}".format(price_ngn) }} &middot; Lifetime access &middot; {{ tier_name }}</p>
    </div>

    <!-- Tabs -->
    <div style="display:flex;gap:8px;margin-bottom:18px;">
      <button id="ci-tab-ps" onclick="ciTab('paystack')"
        style="flex:1;padding:8px;border-radius:8px;border:1px solid rgba(59,130,246,.4);
          background:rgba(59,130,246,.15);color:#93c5fd;font-size:.8rem;font-weight:600;cursor:pointer;">
        &#128179; Paystack
      </button>
      <button id="ci-tab-bt" onclick="ciTab('bank')"
        style="flex:1;padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,.1);
          background:rgba(255,255,255,.04);color:#94a3b8;font-size:.8rem;font-weight:600;cursor:pointer;">
        &#127974; Bank Transfer
      </button>
    </div>

    <!-- Paystack panel -->
    <div id="ci-panel-ps">
      <p style="font-size:.82rem;color:#94a3b8;line-height:1.6;margin-bottom:14px;">
        A secure Paystack checkout page will open with the course name,
        amount (&#8358;{{ "{:,}".format(price_ngn) }}), and your account pre-filled.
      </p>
      <button id="ci-ps-btn" onclick="ciPaystack()"
        style="width:100%;padding:13px;background:linear-gradient(135deg,#d97706,#f59e0b);
          color:#07090f;border:none;border-radius:10px;font-size:.95rem;font-weight:800;
          cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;">
        <span id="ci-ps-spin" style="display:none;width:15px;height:15px;border:2px solid rgba(0,0,0,.2);
          border-top-color:#07090f;border-radius:50%;animation:ciSpin .7s linear infinite;"></span>
        <span id="ci-ps-lbl">&#128640; Pay &#8358;{{ "{:,}".format(price_ngn) }} via Paystack</span>
      </button>
      <p id="ci-ps-err" style="display:none;color:#fca5a5;font-size:.78rem;margin-top:8px;text-align:center;"></p>
      <p style="font-size:.72rem;color:#4a5568;margin-top:8px;text-align:center;">
        Card &middot; Bank transfer &middot; USSD &middot; Secured by Paystack
      </p>
    </div>

    <!-- Bank Transfer panel -->
    <div id="ci-panel-bt" style="display:none;">
      <div style="background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);
        border-radius:8px;padding:12px 14px;margin-bottom:12px;">
        <div style="font-size:.7rem;color:#64748b;">Bank &middot; Account Name &middot; Account Number</div>
        <div style="font-weight:700;color:#93c5fd;font-size:.95rem;margin-top:4px;" id="ci-bank-info">
          Zenith Bank &middot; Teamsamikoko Global Academy &middot; 1228732577
        </div>
        <button onclick="ciCopyAcct()" style="margin-top:5px;background:rgba(59,130,246,.15);
          border:1px solid rgba(59,130,246,.3);color:#93c5fd;border-radius:5px;
          padding:2px 10px;font-size:.72rem;cursor:pointer;">&#128203; Copy number</button>
      </div>
      <p style="font-size:.8rem;color:#94a3b8;line-height:1.6;margin-bottom:10px;">
        Transfer exactly <strong style="color:#fcd34d;">&#8358;{{ "{:,}".format(price_ngn) }}</strong> and upload your receipt below.
        Your account will be upgraded within 24 hours.
      </p>

      <input id="ci-ref" placeholder="Payment reference / your email (optional)"
        style="width:100%;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);
          border-radius:7px;padding:8px 11px;color:#e2e8f0;font-size:.83rem;margin-bottom:8px;
          outline:none;font-family:inherit;"/>

      <div id="ci-upload" onclick="document.getElementById('ci-file').click()"
        style="border:2px dashed rgba(255,255,255,.1);border-radius:8px;padding:14px;
          text-align:center;cursor:pointer;font-size:.8rem;color:#64748b;transition:.18s;"
        ondragover="event.preventDefault();this.style.borderColor='rgba(59,130,246,.5)'"
        ondragleave="this.style.borderColor='rgba(255,255,255,.1)'"
        ondrop="ciHandleDrop(event)">
        &#128206; Click or drag receipt image here (PNG/JPG &middot; max 3.5 MB)
        <input type="file" id="ci-file" accept="image/*" style="display:none"
          onchange="ciHandleFile(this)"/>
        <img id="ci-preview" style="display:none;max-width:100%;border-radius:6px;margin-top:8px;" alt="preview"/>
      </div>

      <button id="ci-bt-btn" onclick="ciBankSubmit()"
        style="width:100%;margin-top:10px;padding:11px;
          background:linear-gradient(135deg,#1d4ed8,#3b82f6);color:#fff;
          border:none;border-radius:9px;font-size:.88rem;font-weight:700;cursor:pointer;">
        &#128228; Submit Receipt
      </button>
      <div id="ci-bt-msg" style="display:none;font-size:.78rem;margin-top:8px;
        border-radius:7px;padding:9px 12px;line-height:1.55;"></div>
    </div>
  </div>
</div>

<style>
@keyframes ciSlideUp { from{opacity:0;transform:translateY(28px)} to{opacity:1;transform:translateY(0)} }
@keyframes ciSpin    { to{transform:rotate(360deg)} }
</style>

<script>
// Baked-in course constants (set at render time by Jinja2)
var COURSE_PRICE = {{ price_ngn }};
var COURSE_SLUG  = '{{ course_slug }}';
var COURSE_NAME  = '{{ course_title }}';
var TIER_NAME    = '{{ tier_name }}';

var CI_API   = 'https://mypytutor.onrender.com';
var CI_TOKEN = function() {
  return localStorage.getItem('mpt_token')
      || localStorage.getItem('token')
      || localStorage.getItem('auth_token')
      || sessionStorage.getItem('mpt_token')
      || '';
};
var CI_LID = function() {
  var lid = localStorage.getItem('mpt_learner_id')
      || localStorage.getItem('learner_id')
      || sessionStorage.getItem('mpt_learner_id')
      || '';
  if (lid) return lid;
  try {
    var tok = CI_TOKEN();
    if (!tok) return '';
    var p = JSON.parse(atob(tok.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
    return p.learner_id || p.sub || p.id || '';
  } catch(e) { return ''; }
};
var ciBankB64 = '';

function openCheckout(e) {
  if (e) e.preventDefault();
  var ov = document.getElementById('checkout-overlay');
  ov.style.display = 'flex';
  fetch(CI_API + '/payments/bank-details').then(function(r){ return r.json(); }).then(function(d){
    document.getElementById('ci-bank-info').textContent =
      (d.bank_name||'Zenith Bank') + ' \u00b7 ' +
      (d.account_name||'Teamsamikoko Global Academy') + ' \u00b7 ' +
      (d.account_number||'1228732577');
  }).catch(function(){});
}
function closeCheckout() {
  document.getElementById('checkout-overlay').style.display = 'none';
}
document.getElementById('checkout-overlay').addEventListener('click', function(e){
  if (e.target === this) closeCheckout();
});

function ciTab(name) {
  var isPs = name === 'paystack';
  document.getElementById('ci-panel-ps').style.display = isPs ? '' : 'none';
  document.getElementById('ci-panel-bt').style.display = isPs ? 'none' : '';
  document.getElementById('ci-tab-ps').style.background = isPs ? 'rgba(59,130,246,.15)' : 'rgba(255,255,255,.04)';
  document.getElementById('ci-tab-ps').style.borderColor = isPs ? 'rgba(59,130,246,.4)' : 'rgba(255,255,255,.1)';
  document.getElementById('ci-tab-ps').style.color = isPs ? '#93c5fd' : '#94a3b8';
  document.getElementById('ci-tab-bt').style.background = !isPs ? 'rgba(59,130,246,.15)' : 'rgba(255,255,255,.04)';
  document.getElementById('ci-tab-bt').style.borderColor = !isPs ? 'rgba(59,130,246,.4)' : 'rgba(255,255,255,.1)';
  document.getElementById('ci-tab-bt').style.color = !isPs ? '#93c5fd' : '#94a3b8';
}

async function ciPaystack() {
  var btn  = document.getElementById('ci-ps-btn');
  var spin = document.getElementById('ci-ps-spin');
  var lbl  = document.getElementById('ci-ps-lbl');
  var err  = document.getElementById('ci-ps-err');
  if (!CI_TOKEN()) {
    err.textContent = 'Please sign in to MyPy Tutor first, then return here to pay.';
    err.style.display = 'block'; return;
  }
  btn.disabled = true; spin.style.display = 'inline-block'; lbl.textContent = 'Opening checkout\u2026'; err.style.display = 'none';
  try {
    var r = await fetch(CI_API + '/payments/paystack/initialize', {
      method: 'POST',
      headers: {'Content-Type':'application/json','Authorization':'Bearer ' + CI_TOKEN()},
      body: JSON.stringify({
        learner_id:  CI_LID(),
        amount_ngn:  COURSE_PRICE,
        plan:        TIER_NAME,
        course_name: COURSE_SLUG,
        coupon_code: '',
      }),
    });
    var d = await r.json();
    if (!r.ok || !d.authorization_url) throw new Error(d.error || d.detail || 'Checkout failed.');
    window.location.href = d.authorization_url;
  } catch(e) {
    err.textContent = e.message || 'Could not open checkout. Try bank transfer instead.';
    err.style.display = 'block';
    btn.disabled = false; spin.style.display = 'none'; lbl.textContent = '\u{1F680} Pay \u20A6{{ "{:,}".format(price_ngn) }} via Paystack';
  }
}

function ciCopyAcct() {
  var txt = document.getElementById('ci-bank-info').textContent;
  var num = txt.split('\u00b7').pop().trim();
  navigator.clipboard.writeText(num).then(function(){
    document.querySelector('#ci-panel-bt button').textContent = '\u2705 Copied!';
    setTimeout(function(){ document.querySelector('#ci-panel-bt button').innerHTML='\u{1F4CB} Copy number'; }, 2000);
  });
}

function ciHandleDrop(e) {
  e.preventDefault();
  document.getElementById('ci-upload').style.borderColor='rgba(255,255,255,.1)';
  if (e.dataTransfer.files[0]) ciProcessFile(e.dataTransfer.files[0]);
}
function ciHandleFile(inp) { if (inp.files[0]) ciProcessFile(inp.files[0]); }
function ciProcessFile(file) {
  if (file.size > 3.8*1024*1024) { alert('File too large. Max 3.5 MB.'); return; }
  var reader = new FileReader();
  reader.onload = function(e) {
    ciBankB64 = e.target.result;
    var p = document.getElementById('ci-preview');
    p.src = ciBankB64; p.style.display = 'block';
    document.getElementById('ci-upload').childNodes[0].textContent = '\u2705 ' + file.name;
  };
  reader.readAsDataURL(file);
}

async function ciBankSubmit() {
  var ref = document.getElementById('ci-ref').value.trim();
  var btn = document.getElementById('ci-bt-btn');
  var msg = document.getElementById('ci-bt-msg');
  if (!ciBankB64)  { showCiMsg('Please upload your receipt image.', false); return; }
  if (!CI_TOKEN()) { showCiMsg('Please sign in to MyPy Tutor first, then come back to submit.', false); return; }
  btn.disabled = true; btn.textContent = '\u23F3 Submitting\u2026'; msg.style.display = 'none';
  try {
    var r = await fetch(CI_API + '/payments/bank-transfer/submit', {
      method: 'POST',
      headers: {'Content-Type':'application/json','Authorization':'Bearer ' + CI_TOKEN()},
      body: JSON.stringify({
        plan:               TIER_NAME,
        amount:             COURSE_PRICE,
        reference:          ref,
        proof_image_base64: ciBankB64,
        course_name:        COURSE_SLUG,
      }),
    });
    var d = await r.json();
    if (!r.ok) throw new Error(d.error || d.detail || 'Submission failed.');
    showCiMsg('\u2705 Receipt submitted! (ID: ' + d.proof_id + '). Your account will be upgraded within 24 hours.', true);
    btn.textContent = '\u2705 Submitted';
  } catch(e) {
    showCiMsg('\u274C ' + (e.message || 'Could not submit. Please try again.'), false);
    btn.disabled = false; btn.textContent = '\u{1F4E4} Submit Receipt';
  }
}

function showCiMsg(txt, ok) {
  var el = document.getElementById('ci-bt-msg');
  el.textContent = txt;
  el.style.display = 'block';
  el.style.background = ok ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)';
  el.style.border = '1px solid ' + (ok ? 'rgba(16,185,129,.3)' : 'rgba(239,68,68,.3)');
  el.style.color = ok ? '#6ee7b7' : '#fca5a5';
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Render function — builds context and invokes the Jinja2 template
# ---------------------------------------------------------------------------

def render_course_landing(course_slug: str) -> str:
    """Render a dynamic landing page HTML string for any of the 17 courses."""
    catalog = COURSE_CATALOG.get(course_slug)
    if not catalog:
        raise ValueError(f"Unknown course: {course_slug!r}")

    course = COURSES.get(course_slug)
    if not course:
        raise ValueError(f"Course data not found for: {course_slug!r}")

    # Build step list as plain dicts for Jinja2 (avoid passing dataclass objects)
    steps = [
        {
            "step":        s.step,
            "title":       s.title,
            "description": s.description,
            "intent":      s.intent,
        }
        for s in course.steps
    ]

    # Count by intent
    concept_count  = sum(1 for s in steps if s["intent"] == "concept")
    exercise_count = sum(1 for s in steps if s["intent"] == "exercise")
    quiz_count     = sum(1 for s in steps if s["intent"] == "quiz")
    codegen_count  = sum(1 for s in steps if s["intent"] == "codegen")

    # Determine cheapest tier that unlocks this course
    tier_unlocks = catalog.get("tier_unlocks", ["tier4"])
    tier_key     = tier_unlocks[0]  # already sorted cheapest-first in COURSE_CATALOG
    tier_info    = TIER_PLANS.get(tier_key, TIER_PLANS["tier4"])
    tier_name    = tier_info["name"]
    tier_price   = tier_info["price_ngn"]

    price_ngn = catalog["price_ngn"]

    def _fmt(n: int) -> str:
        return "\u20a6{:,}".format(n)  # ₦ + comma-formatted number

    _unlocks_count = tier_info.get("unlocks_count")
    if _unlocks_count is None:
        # Tier is missing the unlocks_count key — log and use a safe fallback rather
        # than silently emitting "1" which would be factually wrong.
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "TIER_PLANS[%r] is missing 'unlocks_count' key — bundle text will be approximate.", tier_key
        )
        _unlocks_count = "several"
    bundle_text = (
        "The {} ({} one-time) unlocks this course plus {} total courses.".format(
            tier_name, _fmt(tier_price), _unlocks_count
        )
    )

    # FAQ prerequisite answer based on course level
    level = course.level
    if level == "beginner":
        faq_prereq = (
            "No prior experience needed \u2014 this course starts from zero. "
            "A computer and curiosity are all you need."
        )
    elif level == "intermediate":
        faq_prereq = (
            "Yes \u2014 you should be comfortable with Python basics: variables, loops, "
            "functions, and basic data types. Complete the Beginner Bundle first if needed."
        )
    else:
        faq_prereq = (
            "Yes \u2014 this is an advanced course. You should be comfortable with Python basics "
            "(variables, functions, loops, classes, and working with APIs). "
            "If you are new to Python, start with the Beginner or Intermediate Bundle first."
        )

    course_title = SLUG_TO_TITLE.get(course_slug, course_slug.replace("-", " ").title())

    context = {
        "course_slug":      course_slug,
        "course_title":     course_title,
        "badge":            catalog.get("badge", "\U0001f4d8"),
        "category":         catalog.get("category", "Python"),
        "price_ngn":        price_ngn,
        "tier_name":        tier_name,
        "tier_price":       tier_price,
        "bundle_text":      bundle_text,
        "step_count":       len(steps),
        "concept_count":    concept_count,
        "exercise_count":   exercise_count,
        "quiz_count":       quiz_count,
        "codegen_count":    codegen_count,
        "steps":            steps,
        "level":            level,
        "faq_prereq_answer": faq_prereq,
    }

    t = Environment(autoescape=True).from_string(COURSE_LANDING_TEMPLATE)
    return t.render(**context)
