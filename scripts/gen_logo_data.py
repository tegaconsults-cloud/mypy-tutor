"""Generate base64 data URIs for all certificate logos."""
import base64, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

files = {
    'MYPYTUTOR_LOGO_URI': os.path.join(ROOT, 'static', 'icons', 'mypytutor_logo.jpg'),
    'TEAMTEGA_LOGO_URI':  os.path.join(ROOT, 'static', 'icons', 'logo-teamtega.jpg'),
    'TEGA_LOGO_URI':      os.path.join(ROOT, 'static', 'icons', 'tega logo.jpg'),
    'SIGNATURE_URI':      os.path.join(ROOT, 'static', 'icons', 'signature.png'),
}

print("# Auto-generated logo data URIs for certificates.py")
print("# Run: python scripts/gen_logo_data.py > /tmp/logo_uris.txt\n")
for var, path in files.items():
    data = open(path, 'rb').read()
    ext  = path.rsplit('.', 1)[-1].lower()
    mime = 'image/png' if ext == 'png' else 'image/jpeg'
    b64  = base64.b64encode(data).decode()
    # Print just first 40 and last 10 chars of each for verification
    print(f"{var} = 'data:{mime};base64,{b64[:40]}...{b64[-10:]}' # {len(b64)} chars")
