"""
Fix certificates.py:
1. Embed all 3 real logos as base64 URIs (signature already embedded)
2. Fix CERT_CONFIGS descriptions to be generic (not Python-only)
3. Update the HTML header to show all 3 logos correctly
4. Update signature names to Amb. Samuel Atulegwu Nwosu (Sir. Tega)

Run: python scripts/fix_certificates.py
"""
import base64, os, re, ast, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
icons = os.path.join(ROOT, 'static', 'icons')


def b64uri(filename, mime=None):
    path = os.path.join(icons, filename)
    ext  = filename.rsplit('.', 1)[-1].lower()
    if mime is None:
        mime = 'image/png' if ext == 'png' else 'image/jpeg'
    data = open(path, 'rb').read()
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode()


# ── 1. Generate the 3 logo URIs (signature already in the file) ─────────────
academy_uri  = b64uri('tega logo.jpg')        # Teamsamikoko Global Academy
teamtega_uri = b64uri('logo-teamtega.jpg')    # TeamTega Technologies
mpt_uri      = b64uri('mypytutor_logo.jpg')   # MyPy Tutor app logo

print(f"Academy (Teamsamikoko) logo: {len(academy_uri):,} chars")
print(f"TeamTega Technologies logo:  {len(teamtega_uri):,} chars")
print(f"MyPy Tutor app logo:         {len(mpt_uri):,} chars")

# ── 2. Read current file ─────────────────────────────────────────────────────
cert_path = os.path.join(ROOT, 'app', 'certificates.py')
src = open(cert_path, encoding='utf-8').read()

# ── 3. Replace logo URI variables ────────────────────────────────────────────
# Replace ACADEMY_LOGO_URI (currently set to old/wrong data)
src = re.sub(
    r'ACADEMY_LOGO_URI\s*=\s*"data:image/[^"]*"',
    f'ACADEMY_LOGO_URI = "{academy_uri}"',
    src,
)
# Replace TEAMTEGA_LOGO_URI
src = re.sub(
    r'TEAMTEGA_LOGO_URI\s*=\s*"data:image/[^"]*"',
    f'TEAMTEGA_LOGO_URI = "{teamtega_uri}"',
    src,
)
# Replace MPT_LOGO_URI (MyPy Tutor logo)
src = re.sub(
    r'MPT_LOGO_URI\s*=\s*"data:image/[^"]*"',
    f'MPT_LOGO_URI = "{mpt_uri}"',
    src,
)
# If MPT_LOGO_URI doesn't exist yet, insert it after TEAMTEGA_LOGO_URI
if 'MPT_LOGO_URI' not in src:
    src = re.sub(
        r'(TEAMTEGA_LOGO_URI\s*=\s*"data:image/[^"]*")',
        r'\1\n\n# MyPy Tutor app logo — centre medallion\nMPT_LOGO_URI = "' + mpt_uri + '"',
        src,
    )
    print("MPT_LOGO_URI inserted")

print("Logo URIs updated")

# ── 4. Fix CERT_CONFIGS — make descriptions cover ALL courses ────────────────

# Basic certificate description
src = re.sub(
    r'"subtitle":\s*"Basic Python Programming"',
    '"subtitle":    "Python Programming & Technology"',
    src,
)
# Replace the basic description with a generic one
old_basic_desc_pattern = re.compile(
    r'("description":\s*\(\s*"has successfully completed the <strong>Basic Python Programming'
    r'</strong>.*?"\s*\))',
    re.DOTALL,
)
new_basic_desc = (
    '"description": (\n'
    '            "has successfully completed the required foundational curriculum at MyPy Tutor, "\n'
    '            "passed the required examinations and practical coding assessments with the qualifying score, "\n'
    '            "and demonstrated solid understanding of Python programming, problem-solving, "\n'
    '            "and computational thinking through structured exercises."\n'
    '        )'
)
if old_basic_desc_pattern.search(src):
    src = old_basic_desc_pattern.sub(new_basic_desc, src)
    print("Basic description updated")

# Advanced certificate description
src = re.sub(
    r'"subtitle":\s*"Advanced Python Programming"',
    '"subtitle":    "Python, Software Engineering & APIs"',
    src,
)
old_adv_desc_pattern = re.compile(
    r'("description":\s*\(\s*"has successfully completed the <strong>Advanced Python Programming'
    r'</strong>.*?"\s*\))',
    re.DOTALL,
)
new_adv_desc = (
    '"description": (\n'
    '            "has successfully completed the Advanced Programme at MyPy Tutor, "\n'
    '            "passed a multi-part examination (MCQ + short answer) with the minimum qualifying score, "\n'
    '            "and demonstrated proficiency in object-oriented programming, data structures, algorithms, "\n'
    '            "REST APIs, software design, and advanced Python patterns through practical assessments."\n'
    '        )'
)
if old_adv_desc_pattern.search(src):
    src = old_adv_desc_pattern.sub(new_adv_desc, src)
    print("Advanced description updated")

# Executive certificate description
src = re.sub(
    r'"subtitle":\s*"Python & AI Engineering"',
    '"subtitle":    "Python, Machine Learning & AI Engineering"',
    src,
)
old_exec_desc_pattern = re.compile(
    r'("description":\s*\(\s*"has successfully completed the <strong>Executive Masters Programme'
    r'.*?"\s*\))',
    re.DOTALL,
)
new_exec_desc = (
    '"description": (\n'
    '            "has successfully completed the Executive Masters Programme at MyPy Tutor, "\n'
    '            "passed a comprehensive examination (MCQ + code review + essay) with the minimum qualifying score, "\n'
    '            "and demonstrated expert-level mastery through advanced real-world coding challenges, "\n'
    '            "machine learning, AI engineering, prompt engineering, and system design."\n'
    '        )'
)
if old_exec_desc_pattern.search(src):
    src = old_exec_desc_pattern.sub(new_exec_desc, src)
    print("Executive description updated")

# ── 5. Update cert skill badges to be more universal ─────────────────────────
src = src.replace(
    '"skills": ["Variables & Data Types", "Loops & Conditionals", "Functions",\n'
    '                   "Exception Handling", "Basic Data Structures"]',
    '"skills": ["Python Fundamentals", "Control Flow & Functions", "Data Structures",\n'
    '                   "Problem Solving", "Code Quality"]',
)
src = src.replace(
    '"skills": ["OOP & Inheritance", "Data Structures & Algorithms",\n'
    '                   "REST APIs", "File Handling", "Modules & Packages"]',
    '"skills": ["Object-Oriented Programming", "Algorithms & Data Structures",\n'
    '                   "APIs & Web Development", "Databases", "Software Design"]',
)

# ── 6. Update the HTML header — add MyPy Tutor centre logo ──────────────────
# Find the header section and add centre logo between the two existing logos
old_header_img = (
    '    <div class="logo-circle"><img src="{ACADEMY_LOGO_URI}" alt="Teamsamikoko Global Academy"/></div>\n'
    '    <div class="hdr-center">'
)
new_header_img = (
    '    <div class="logo-circle"><img src="{ACADEMY_LOGO_URI}" alt="Teamsamikoko Global Academy"/></div>\n'
    '    <div class="logo-circle" style="width:66px;height:66px;background:rgba(255,255,255,0.92);border-color:rgba(255,255,255,0.7);">'
    '<img src="{MPT_LOGO_URI}" alt="MyPy Tutor" style="width:58px;height:58px;"/></div>\n'
    '    <div class="hdr-center">'
)

if old_header_img in src:
    src = src.replace(old_header_img, new_header_img, 1)
    print("Header centre logo added")
else:
    print("WARNING: Header img pattern not found — check manually")

# ── 7. Update signature names ────────────────────────────────────────────────
# First signature block (left side — Academy Director)
src = src.replace(
    '        <div class="sig-name">Academy Director</div>\n        <div class="sig-role">Teamsamikoko Global Academy</div>',
    '        <div class="sig-name">Amb. Samuel A. Nwosu (Sir. Tega)</div>\n        <div class="sig-role">Director, Teamsamikoko Global Academy</div>',
    1,
)
# Second signature block (right side — Programme Lead)
src = src.replace(
    '        <div class="sig-name">Programme Lead</div>\n        <div class="sig-role">TeamTega Technologies Limited</div>',
    '        <div class="sig-name">Amb. Samuel A. Nwosu (Sir. Tega)</div>\n        <div class="sig-role">CEO, TeamTega Technologies Limited</div>',
    1,
)
print("Signature names updated")

# ── 8. Write back ────────────────────────────────────────────────────────────
open(cert_path, 'w', encoding='utf-8').write(src)
print("\ncertificates.py written.")

# ── 9. Syntax check ──────────────────────────────────────────────────────────
try:
    ast.parse(open(cert_path, encoding='utf-8').read())
    print("Syntax check: PASS")
except SyntaxError as e:
    print(f"SYNTAX ERROR line {e.lineno}: {e.msg}")
    sys.exit(1)

print("\nAll done. Push to deploy.")
