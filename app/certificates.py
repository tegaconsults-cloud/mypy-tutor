"""
Certificate generator for MyPy Tutor.
Produces self-contained HTML certificates that can be printed or saved as PDF.
Three levels: Basic, Advanced, Executive Masters
Certifying body: TEAMSAMIKOKO GLOBAL ACADEMY
No extra packages required — free tier safe.
"""

import html
from datetime import datetime

SIGNATURE_URI = "data:image/png;base64,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"

TEAMTEGA_LOGO_URI = "data:image/png;base64,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"

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
        <img src="{ACADEMY_LOGO_URI}" width="90" height="90" alt="Teamsamikoko Global Academy" style="object-fit:contain"/>
      </div>
      <div class="header-text">
        <div class="academy-name">Teamsamikoko Global Academy</div>
        <div class="academy-tagline">Educational Services &amp; Consultancy · Est. 2021 · Reg No: 3508656</div>
        <div style="font-size:0.65rem;color:#718096;margin-top:3px;">In partnership with TeamTega Technologies Limited</div>
        <div style="margin-top:6px">
          <span class="ribbon">{cfg['ribbon_text']}</span>
        </div>
      </div>
      <div class="logo-wrap" style="opacity:0.12">
        <img src="{ACADEMY_LOGO_URI}" width="90" height="90" alt="Teamsamikoko Global Academy" style="object-fit:contain"/>
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
        <img src="{SIGNATURE_URI}" alt="Signature" style="width:140px;height:44px;object-fit:contain;display:block;margin:0 auto 4px;"/>
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
        <img src="{SIGNATURE_URI}" alt="Signature" style="width:140px;height:44px;object-fit:contain;display:block;margin:0 auto 4px;opacity:0.7;"/>
        <div class="sig-name">Programme Lead</div>
        <div class="sig-title">TeamTega Technologies Limited</div>
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
