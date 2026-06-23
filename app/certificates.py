"""
Certificate generator for MyPy Tutor.
Produces self-contained HTML certificates that can be printed or saved as PDF.
Three levels: Basic, Advanced, Executive Masters
Certifying body: TEAMSAMIKOKO GLOBAL ACADEMY
No extra packages required — free tier safe.
"""

import html
from datetime import datetime

# Embedded logo data URIs (base64 PNG — works on Render without file paths)
ACADEMY_LOGO_URI = "data:image/png;base64,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"
MPT_LOGO_URI = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAASwAAAEsCAYAAAB5fY51AAALWElEQVR42u3dy3HsRBgGUGdAsbo7gnAQNwjSYENCZEAQzgqYhaumjMfWSP34H+er+lZwLzNy69CSW62XFxEREREREREREREREVmXt79e/5ldR1lEwoAENBEpBxPIRODUqn76IoA63F9+/QEwEVkD1A2c3QWYCKBCoRQFM6NLJBBSmXFajZhRJ7IQqQ44rULMaBQZDBWY5gNmdIpACl4iVaGCTCy8jGKBFKTgJZIJKmjkxctolxZQwaEWXka/gErBJQIqBZeAClLwApeASsElMhgrJzC4oCWgUnCJgErBJbBShZaASsElcgArJ57OhstZKKBScAmsVKEloFJwgUtgpdCSMlg5cTQyXM5eUMFKzbYEVqrQEpeACi5owUoVWuISUNUlophVKbigBStVaAmsVKElsFJoQQtWqtCSBVgZyAouaMFKFVoCK1VowUoVWtCClSq0BFaq0IKVKrSgBStVaAmsVKEFK1VoQQtWqtCCFaxUoQUsVWABC1aq0IKVqkILVqrQghasVKHVAiyDSHU/WnQyu1I1y4KVqkILVqrQ6o4WrFTdzzK7Uj3Y1z9//q+Oi1kWrDQ8VOCClktBPXJSvEXDClouDWFl4L89251YQas5Wi4FQXW2u7CCVuNLQ1iBaidcV8ACV7NZFqxAtROuEVhBqwlaLgVhtRutkWB1RqvFpSGsYLUbrdFgQasoWLCCVQS0ZoAFrYJoAQtWEdCaBVZXtEqCBStYdUDrt99foZUdLTfagdVpltURrVI34GEFq26zLGglBcvsCljdbsC/g9UNrRKzLFjBqhta92BBKxFYsAJWBrBGo/URLGglQQtYsOqG1mdYdUMrJViwAlY2sEbA9RVY0AKWAmvKrg4zsLq1y+LSVGDBCljZwXoWrSNYvYMFLWApsLbtm3UUK2AFBAtWwKoE1q330JyF6iNY0AKWwmoqWiPa7WHp0GDBCloVsRqJVsfdHcKiBSxgVQZrBFodt6QBlgJr4+vBRmIFLFgpsKaCdRatzhv/hUMLWMDqBNYzaNmpNBhYsAJWR7De12ldxarLpn9h0AIWtDpiNXKXB2BtBCvLAfz7j9c2rXgsngGr+883KlpmV8AC1iezK2CZZQELWMACVh6wst+7AlZdsLr9rN3LAhawgAUsYAELWHPB6vizBlaDpQzAqgdW15+1JQ7AAlYysDr/rIEFLGAlAqv7zxpYDVa27xpYwBoLlv85vVr5Dqy5gwpYtU7S7z6rN+oAC1jAKgNWpx1It4OV9YDtPrmABayOL6ZY+mxhpZ0ZIpxYwOoNVmeslsyygDX+pAJWbrBu8Hz3We/3zeq6iV8IsDIfLGABa9Suo0fA6r7r6JbLQmDNOaGABSxgDQar2s6i0U4mYOUC6/5e1FWwmu9YOwctYM0/kSKDZTvox3u5AysBWNkPFLD2gZUZwM9ePHEFLP8D+AGsXThk/Vwzv1ulR0zuXxoxAqwOL5/YAlbFN+NEvqdSAaxqz8Z9hOYKWO9/DlaTLguBtf4EywpWxbVWj8A5CtajhaOwAhawNoJV8beBjy7lroIFqoVgVThIGU6oTGDNfEQpElafofUsWJCafB8LWPtOpAxgrVhAu2Od1Qyw4DQZrKqvos90qZIVrJHfNRJWH9ECVqDLQmAB66u/Y+V6tJUr2I+A9Y7WUbDABKwtCFT7vKPBmvV9Vz1q8wxYtx4BC0qbwKpygDL+1ioaWDvWo63AajRYQFp4HwtYsQYesOZjBSxgAasBWCu+7wqsgJUUrKr3r86c+JU/e0ewjr7JBliJ7mMBK+6AA9bYB5iBBawSYHX4Dmf+jp2PKM14gPkKWsACFrCCg5VthnUGq6NoASsoWJUOTpVdNoF1fbeFq3ABK8iN985gdfoulcE6stvC1QILWMBKCFa0dVhHH16+0mpjCVjAAtYGsI4+uHwVK2AFAavyDXdg1X6W8JmdFq5iBawgN96BBayMuzU8u9PCVayABSxgJQIr0n5YZx6ruQIVsIAFrEJgrdxx9OxzgEfR6jKWgAWs8mBd/QxX/9tXHlz+Dq4jLzsFFrCAlQysETujjsDqClhn38wMLGABKyFYo9FasZfViNfIAwtYwEoK1qotqEftZXUFKmABC1hBwYrWUVvDXMUKWMACFrAug3UGLWMJWMAC1jawnkHLWAIWsIC1HawjaBlLBcGqdmCA1QesswtCgZXoAWgzLGBVB8tYckkILGClAMtYAhawgJUCLGMJWMACVgqwjCVgAQtYy3tmPytjCVjAAtY2sEZtD2MsAQtYwFoG1ldojVprBSxgAQtYw8CauTAUWMACFrCWgGUsAQtYwAIWsIAFLGCNBMtYAhawgJUCrNm/GQRWMLC8+RlYWcFaiRWwAjz4DCxgZQVrxborYAELWMB6+tGcr9ZgGUvAAhaw0jxLaCwBqxRawAKWsVTohjuwgJUVLMsagAUsYAELWMACFrBGgrVjeQOwgoBV+cY7sOqB5dGcxjfcgQWsLGDtXkQKLGAZZMAa8vCzDfyag1UFLWDVB8uOo83uXwELWFXAsqc7sIAFrFRgeWtOA7Cq3scCVv3tZR79JtFYKnr/CljAyrq9zMpFpcAKDlYFtIBVe3uZIwtLjaWCl4PAAlaF9xI+WrNlLAELWMAK+6r6GavhgRUMrIr3sYAFrFFoASvQ/asOm/lpnp6F6shjPI5vYbCgpdnQivSmHZ14OQgszY5WlOcOdRFYLgs1K1pHH5Re+fyhTrwcBJZG7dGFomfAglYxsKClUdAa1d0vtHA5CCyF1iWwoJUULJeFWhmtSK8OczlolqXQugQWtJLNroClVdF69jeOjjOwVLegdXY9l+OcACxoaSW0ri5AdZyDYwUszba4dARUu999CCxgqRXxIXZ7ANZksKClXdGy20NCrIClXdH67p6Y4wws1RTb09iiJjBY0FLb00ArDVbAUtvT2FcrFVieLdTqaF1dNe8YL3520CxLLTC1p1aJ2RWwFFr21EoFFrQUXPbUSoMVsBRa9tRKBRa0FFrHwOq2uDQkVsBSaP08vEQCWMBS3YqWDQCTgQUt7bZFzdltarqgFRorYKlV8XYsTQUWtBRadixNgxWwFFrASgUWtBRavXcrTYUVsBRawEoFFrQUWsd3fai0Aj4lVsDSLmu07FJaBCxoabeFpd13KE2N1SOwoKWeO6wH1qNz/SVbgKXAqr+lcgmszLIUWvXBKjO7MstSYNXf/70UVtBSaNXd+70kVsDS7rs6VN33vSxY0NJOC0k77PleGis34NXK9zr7vZe70W6WpcB67tEdsytoqYZ6VKcCWK2wOntp+N8/f1ON3jNo3f5MpO/gUnDQLMsJoRnAOvNSigxYtZxdXUHLCaGZ0PoKrvt/J/Ps6qVTXBpqF7g+a7TP61IQWqpv0aGClftZqmnqvtWiBaUGm+p6rNqD5dJQ1aWgR3dU1aM3VsGr9gOLTmZZqmZX0FJVWEFLFVYCLVVYQUtVYQUsVWAJtFRhBS1VhRW0VGEl0FKFFbRUYQUraKnCSqClCitoqcJKoKUKK4GWKqygpQoriYUWuLQzVLCCliqsBFqqsIIWtBRWAi1VWMkStMCl1aCCldmWqlmVQEsVVuISUV0CCrRUYSUuEVVdAorZlppVCbRUYSXgUlCBSqClsBJwqYJKkqAFLp0BFawEXAoqgRa0FFYCLgWVCLgUVAItcOlBqGAl4FJQicyAC169kAKVgEtBJQIuBZWAC17lkQKVtIYLXjmQApXAC16QEqkAF7z2IQUqEXhBSqQbXAAbBxSoRDbg1QmxUcfKqBMJhFcFxEYfC6NLJBlg0TCb+f2MHpHCgJ0BL9LnMTpEABa2fvoiEIOTiIAMTCKSCjRHWURERERERERERLLnX6YOyLqpyuYWAAAAAElFTkSuQmCC"



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
        <img src="data:image/png;base64,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" width="90" height="90" alt="Teamsamikoko Academy" style="object-fit:contain"/>
      </div>
      <div class="header-text">
        <div class="academy-name">Teamsamikoko Global Academy</div>
        <div class="academy-tagline">Educational Services &amp; Consultancy · Est. 2021 · Reg No: 3508656</div>
        <div style="margin-top:6px">
          <span class="ribbon">{cfg['ribbon_text']}</span>
        </div>
      </div>
      <div class="logo-wrap" style="opacity:0.12">
        <img src="data:image/png;base64,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" width="90" height="90" alt="Teamsamikoko Academy" style="object-fit:contain"/>
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
