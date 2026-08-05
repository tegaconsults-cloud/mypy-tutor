"""
Embed the three logo images + signature as base64 data URIs into certificates.py.
Run once: python scripts/embed_logos.py
"""
import base64, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def b64uri(path, mime="image/jpeg"):
    data = open(path, "rb").read()
    return "data:" + mime + ";base64," + base64.b64encode(data).decode()

icons = os.path.join(ROOT, "static", "icons")
replacements = {
    "MYPYTUTOR_LOGO_URI": b64uri(os.path.join(icons, "mypytutor_logo.jpg")),
    "TEAMTEGA_LOGO_URI":  b64uri(os.path.join(icons, "logo-teamtega.jpg")),
    "TEGA_LOGO_URI":      b64uri(os.path.join(icons, "tega logo.jpg")),
    "SIGNATURE_URI":      b64uri(os.path.join(icons, "signature.png"), "image/png"),
}

cert_path = os.path.join(ROOT, "app", "certificates.py")
src = open(cert_path, encoding="utf-8").read()

for var, uri in replacements.items():
    # Replace any existing assignment for this variable
    # Pattern: VAR = "data:..." or VAR = 'data:...'
    pattern = rf'{var}\s*=\s*["\']data:[^"\']*["\']'
    new_val  = f'{var} = "{uri}"'
    if re.search(pattern, src):
        src = re.sub(pattern, new_val, src)
        print(f"  Updated {var} ({len(uri)} chars)")
    else:
        print(f"  WARNING: {var} not found in certificates.py — skipping")

open(cert_path, "w", encoding="utf-8").write(src)
print("\nDone. certificates.py updated.")
