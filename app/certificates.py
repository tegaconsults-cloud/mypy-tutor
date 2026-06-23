"""
Certificate generator for MyPy Tutor.
Produces self-contained HTML certificates that can be printed or saved as PDF.
Three levels: Basic, Advanced, Executive Masters
Certifying body: TEAMSAMIKOKO GLOBAL ACADEMY
No extra packages required — free tier safe.
"""

import html
from datetime import datetime

# ---------------------------------------------------------------------------
# Academy logo — recreated as inline SVG matching the circular seal
# ---------------------------------------------------------------------------

ACADEMY_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="120" height="120">
  <!-- Outer spiky border -->
  <circle cx="100" cy="100" r="96" fill="#1a3a8a" stroke="#1a3a8a" stroke-width="2"/>
  <!-- Spiky crown effect using polygon points around circumference -->
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(0,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(15,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(30,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(45,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(60,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(75,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(90,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(105,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(120,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(135,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(150,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(165,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(180,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(195,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(210,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(225,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(240,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(255,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(270,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(285,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(300,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(315,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(330,100,100)"/>
  <polygon points="100,4 105,14 100,10 95,14" fill="#fff" transform="rotate(345,100,100)"/>
  <!-- Blue band -->
  <circle cx="100" cy="100" r="88" fill="#1a3a8a"/>
  <!-- White inner circle -->
  <circle cx="100" cy="100" r="80" fill="#fff" stroke="#1a3a8a" stroke-width="2"/>
  <!-- Inner blue ring -->
  <circle cx="100" cy="100" r="76" fill="none" stroke="#1a3a8a" stroke-width="3"/>
  <!-- Curved top text: TEAMSAMIKOKO GLOBAL ACADEMY -->
  <path id="top-arc" d="M 22,100 A 78,78 0 0,1 178,100" fill="none"/>
  <text font-family="Arial,sans-serif" font-size="10.5" font-weight="bold" fill="#fff">
    <textPath href="#top-arc" startOffset="3%">TEAMSAMIKOKO GLOBAL ACADEMY</textPath>
  </text>
  <!-- Curved bottom text: Integrity is our identity -->
  <path id="bot-arc" d="M 22,100 A 78,78 0 0,0 178,100" fill="none"/>
  <text font-family="Arial,sans-serif" font-size="9" font-style="italic" fill="#1a3a8a">
    <textPath href="#bot-arc" startOffset="8%">Integrity is our identity</textPath>
  </text>
  <!-- SINCE / 2021 -->
  <text x="26" y="105" font-family="Arial,sans-serif" font-size="7.5" font-weight="bold" fill="#1a3a8a">SINCE</text>
  <text x="163" y="105" font-family="Arial,sans-serif" font-size="7.5" font-weight="bold" fill="#1a3a8a">2021</text>
  <!-- Globe (simplified) -->
  <circle cx="108" cy="72" r="18" fill="none" stroke="#333" stroke-width="1.5"/>
  <ellipse cx="108" cy="72" rx="9" ry="18" fill="none" stroke="#333" stroke-width="1"/>
  <line x1="90" y1="72" x2="126" y2="72" stroke="#333" stroke-width="1"/>
  <line x1="91" y1="64" x2="125" y2="64" stroke="#333" stroke-width="0.7"/>
  <line x1="91" y1="80" x2="125" y2="80" stroke="#333" stroke-width="0.7"/>
  <!-- Books (simplified stack) -->
  <rect x="74" y="88" width="42" height="8" rx="1" fill="none" stroke="#333" stroke-width="1.5"/>
  <rect x="72" y="93" width="46" height="7" rx="1" fill="none" stroke="#333" stroke-width="1.5"/>
  <rect x="78" y="82" width="30" height="8" rx="1" fill="none" stroke="#333" stroke-width="1.2" transform="rotate(-8,93,86)"/>
  <!-- Small text inside -->
  <text x="100" y="113" font-family="Arial,sans-serif" font-size="5.5" font-weight="bold" fill="#333" text-anchor="middle">EDUCATIONAL SERVICES AND</text>
  <text x="100" y="120" font-family="Arial,sans-serif" font-size="5.5" font-weight="bold" fill="#333" text-anchor="middle">CONSULTANCY, GENERAL CONTRACTS</text>
  <text x="100" y="129" font-family="Arial,sans-serif" font-size="6" font-weight="bold" fill="#1a3a8a" text-anchor="middle">REG NO: 3508656</text>
</svg>"""

# ---------------------------------------------------------------------------
# Certificate configs per level
# ---------------------------------------------------------------------------

CERT_CONFIGS = {
    "basic": {
        "title":       "Certificate of Completion",
        "subtitle":    "Basic Python Programming",
        "credential":  "MyPy Tutor Basic Certificate",
        "color_primary":   "#1a3a8a",
        "color_accent":    "#3182ce",
        "color_gold":      "#b8960c",
        "border_style":    "double",
        "ribbon_text":     "BASIC",
        "description": (
            "has successfully completed the <strong>Basic Python Programming</strong> course track, "
            "passed a 20-question proctored examination with a minimum score of 60%, "
            "and demonstrated foundational knowledge in Python syntax, data types, loops, "
            "functions, and exception handling through 3 practical coding assessments."
        ),
        "skills": ["Variables & Data Types", "Loops & Conditionals", "Functions",
                   "Exception Handling", "Basic Data Structures"],
        "exam_details": "20-question MCQ exam · 60% pass mark · 60 min · 3 coding problems",
    },
    "advanced": {
        "title":       "Certificate of Achievement",
        "subtitle":    "Advanced Python Programming",
        "credential":  "MyPy Tutor Advanced Certificate",
        "color_primary":   "#2d3748",
        "color_accent":    "#9f7aea",
        "color_gold":      "#d4a017",
        "border_style":    "solid",
        "ribbon_text":     "ADVANCED",
        "description": (
            "has successfully completed the <strong>Advanced Python Programming</strong> course track, "
            "passed a 35-question proctored examination (MCQ + short answer) with a minimum score of 65%, "
            "and demonstrated proficiency in OOP, data structures, algorithms, APIs, and "
            "software design through 5 intermediate-level coding assessments."
        ),
        "skills": ["OOP & Inheritance", "Data Structures & Algorithms",
                   "REST APIs", "File Handling", "Modules & Packages"],
        "exam_details": "35-question exam (MCQ + short answer) · 65% pass mark · 90 min · 5 coding problems",
    },
    "executive": {
        "title":       "Executive Masters Certificate",
        "subtitle":    "Python & AI Engineering",
        "credential":  "MyPy Tutor Executive Masters",
        "color_primary":   "#744210",
        "color_accent":    "#f6ad55",
        "color_gold":      "#c7972b",
        "border_style":    "solid",
        "ribbon_text":     "EXECUTIVE MASTERS",
        "description": (
            "has successfully completed the <strong>Executive Masters Programme in Python & AI Engineering</strong>, "
            "passed a comprehensive 50-question proctored examination (MCQ + code review + essay) "
            "with a minimum score of 70%, and demonstrated expert-level mastery through 8 advanced "
            "real-world coding challenges, prompt engineering, AI integration, and system design."
        ),
        "skills": ["Advanced Python Mastery", "Prompt Engineering",
                   "AI Integration & APIs", "System Design", "Professional Dev Practices",
                   "Coding Assessment — Distinction"],
        "exam_details": "50-question comprehensive exam · 70% pass mark · 3 hours · 8 advanced coding challenges",
    },
}


# ---------------------------------------------------------------------------
# HTML certificate generator
# ---------------------------------------------------------------------------

def generate_certificate_html(
    learner_name: str,
    level: str,           # "basic" | "advanced" | "executive"
    cert_id: str,
    issue_date: str | None = None,
) -> str:
    """
    Generate a self-contained printable HTML certificate.
    Returns a full HTML document as a string.
    """
    cfg = CERT_CONFIGS.get(level, CERT_CONFIGS["basic"])
    date_str = issue_date or datetime.utcnow().strftime("%B %d, %Y")
    name_safe = html.escape(learner_name)

    skills_html = "".join(
        f'<span style="display:inline-block;background:{cfg["color_accent"]}22;'
        f'color:{cfg["color_accent"]};border:1px solid {cfg["color_accent"]}44;'
        f'border-radius:999px;padding:3px 12px;margin:3px;font-size:0.78rem;">'
        f'{html.escape(s)}</span>'
        for s in cfg["skills"]
    )

    logo_b64_uri = f"data:image/svg+xml;charset=utf-8,{ACADEMY_LOGO_SVG.replace('#','%23').replace('<','%3C').replace('>','%3E').replace(' ','%20').replace(chr(10),'').replace(chr(13),'')}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{cfg['credential']} — {name_safe}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Lato',sans-serif;background:#f0ece4;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
  .page{{width:100%;max-width:900px;aspect-ratio:297/210;position:relative}}
  @media print{{
    body{{background:#fff;padding:0}}
    .page{{max-width:100%;width:297mm;height:210mm}}
    .no-print{{display:none!important}}
    @page{{size:A4 landscape;margin:0}}
  }}
  .cert{{
    width:100%;height:100%;
    background:linear-gradient(135deg,#fff 0%,#fdfaf4 60%,#f5f0e8 100%);
    border:{cfg['color_primary']} 12px {cfg['border_style']};
    box-shadow:0 8px 40px rgba(0,0,0,0.25);
    padding:28px 40px;
    display:flex;flex-direction:column;align-items:center;
    position:relative;overflow:hidden;
  }}
  /* Decorative corner ornaments */
  .cert::before,.cert::after{{
    content:'✦';font-size:2.5rem;color:{cfg['color_gold']};
    position:absolute;opacity:0.5;
  }}
  .cert::before{{top:12px;left:18px}}
  .cert::after{{bottom:12px;right:18px}}
  .corner-br{{position:absolute;top:12px;right:18px;font-size:2.5rem;color:{cfg['color_gold']};opacity:0.5}}
  .corner-bl{{position:absolute;bottom:12px;left:18px;font-size:2.5rem;color:{cfg['color_gold']};opacity:0.5}}
  /* Watermark */
  .watermark{{
    position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-30deg);
    font-size:5rem;font-weight:900;color:{cfg['color_primary']};opacity:0.04;
    white-space:nowrap;font-family:'Playfair Display',serif;pointer-events:none;
    user-select:none;
  }}
  /* Inner decorative border */
  .inner-border{{
    position:absolute;inset:18px;
    border:2px solid {cfg['color_gold']};
    opacity:0.4;pointer-events:none;
  }}
  /* Header */
  .header{{display:flex;align-items:center;gap:20px;width:100%;margin-bottom:10px}}
  .logo-wrap{{flex-shrink:0}}
  .logo-wrap svg,.logo-wrap img{{width:90px;height:90px;object-fit:contain}}
  .header-text{{flex:1;text-align:center}}
  .academy-name{{
    font-family:'Playfair Display',serif;
    font-size:0.85rem;font-weight:700;letter-spacing:0.18em;
    text-transform:uppercase;color:{cfg['color_primary']};
    margin-bottom:2px;
  }}
  .academy-tagline{{font-size:0.68rem;color:#718096;letter-spacing:0.08em;text-transform:uppercase}}
  /* Ribbon badge */
  .ribbon{{
    background:{cfg['color_primary']};color:#fff;
    font-size:0.62rem;font-weight:700;letter-spacing:0.16em;
    padding:3px 16px;border-radius:999px;text-transform:uppercase;
    margin-bottom:6px;display:inline-block;
  }}
  /* Certificate title */
  .cert-title{{
    font-family:'Playfair Display',serif;
    font-size:2rem;font-weight:700;
    color:{cfg['color_primary']};
    text-align:center;line-height:1.2;
    margin-bottom:2px;
  }}
  .cert-subtitle{{
    font-family:'Playfair Display',serif;
    font-size:1rem;font-weight:400;font-style:italic;
    color:{cfg['color_accent']};text-align:center;margin-bottom:10px;
  }}
  /* Divider */
  .divider{{
    width:60%;height:2px;
    background:linear-gradient(90deg,transparent,{cfg['color_gold']},transparent);
    margin:6px auto;
  }}
  /* Body text */
  .presented-to{{font-size:0.82rem;color:#666;text-align:center;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:4px}}
  .learner-name{{
    font-family:'Playfair Display',serif;
    font-size:2.4rem;font-weight:700;
    color:{cfg['color_primary']};text-align:center;
    border-bottom:2px solid {cfg['color_gold']};
    padding-bottom:4px;margin-bottom:10px;
    letter-spacing:0.03em;
  }}
  .description{{font-size:0.8rem;color:#444;text-align:center;line-height:1.6;max-width:620px;margin:0 auto 10px}}
  /* Skills */
  .skills{{text-align:center;margin-bottom:12px}}
  /* Footer */
  .footer{{display:flex;justify-content:space-between;align-items:flex-end;width:100%;margin-top:auto}}
  .sig-block{{text-align:center;min-width:140px}}
  .sig-line{{width:140px;height:1px;background:{cfg['color_primary']};margin:0 auto 4px}}
  .sig-name{{font-size:0.72rem;font-weight:700;color:{cfg['color_primary']};letter-spacing:0.05em}}
  .sig-title{{font-size:0.65rem;color:#718096}}
  .cert-meta{{text-align:center;font-size:0.65rem;color:#aaa;line-height:1.5}}
  .cert-meta strong{{color:{cfg['color_primary']}}}
  /* Print button */
  .print-bar{{
    position:fixed;bottom:20px;right:20px;display:flex;gap:10px;z-index:999;
  }}
  .btn{{
    padding:10px 22px;border-radius:8px;font-size:0.88rem;
    font-weight:700;cursor:pointer;border:none;
    transition:opacity 0.15s;
  }}
  .btn-print{{background:{cfg['color_primary']};color:#fff}}
  .btn-close{{background:#2d3748;color:#e2e8f0}}
  .btn:hover{{opacity:0.88}}
</style>
</head>
<body>

<div class="page">
  <div class="cert">
    <div class="watermark">TEAMSAMIKOKO</div>
    <div class="inner-border"></div>
    <span class="corner-br">✦</span>
    <span class="corner-bl">✦</span>

    <!-- Header -->
    <div class="header">
      <div class="logo-wrap">
        {ACADEMY_LOGO_SVG.replace('width="120"', 'width="90"').replace('height="120"', 'height="90"')}
      </div>
      <div class="header-text">
        <div class="academy-name">Teamsamikoko Global Academy</div>
        <div class="academy-tagline">Educational Services &amp; Consultancy · Est. 2021 · Reg No: 3508656</div>
        <div style="margin-top:6px">
          <span class="ribbon">{cfg['ribbon_text']}</span>
        </div>
      </div>
      <div class="logo-wrap" style="opacity:0.12">
        {ACADEMY_LOGO_SVG.replace('width="120"', 'width="90"').replace('height="120"', 'height="90"')}
      </div>
    </div>

    <div class="divider"></div>

    <!-- Title -->
    <div class="cert-title">{cfg['title']}</div>
    <div class="cert-subtitle">in {cfg['subtitle']}</div>

    <div class="divider"></div>

    <!-- Recipient -->
    <div class="presented-to">This is to certify that</div>
    <div class="learner-name">{name_safe}</div>

    <div class="description">
      {cfg['description']}
    </div>

    <!-- Skills -->
    <div class="skills">{skills_html}</div>

    <!-- Footer -->
    <div class="footer">
      <div class="sig-block">
        <div class="sig-line"></div>
        <div class="sig-name">Academy Director</div>
        <div class="sig-title">Teamsamikoko Global Academy</div>
      </div>

      <div class="cert-meta">
        <strong>Certificate ID:</strong> {cert_id}<br/>
        <strong>Issue Date:</strong> {date_str}<br/>
        <strong>MyPy Tutor</strong> · mypytutor.onrender.com<br/>
        <strong>Examination:</strong> {cfg.get('exam_details', cfg['ribbon_text'])}<br/>
        <strong>Level:</strong> {cfg['ribbon_text']}
      </div>

      <div class="sig-block">
        <div class="sig-line"></div>
        <div class="sig-name">Programme Lead</div>
        <div class="sig-title">MyPy Tutor Platform</div>
      </div>
    </div>

  </div>
</div>

<!-- Print / Close controls -->
<div class="print-bar no-print">
  <button class="btn btn-print" onclick="window.print()">🖨️ Print / Save PDF</button>
  <button class="btn btn-close" onclick="window.close()">✕ Close</button>
</div>

</body>
</html>"""


def get_cert_id(learner_id: str, level: str) -> str:
    """Generate a deterministic certificate ID."""
    import hashlib
    raw = f"{learner_id}:{level}:teamsamikoko"
    return "TGA-" + hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
