import base64

# Read logo
with open('static/mypytutor_logo.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('ascii')

uri = f'data:image/png;base64,{b64}'

# Read cert file
with open('app/certificates.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find TEAMTEGA_LOGO_URI = "..." and replace the value
# The variable is defined as:  TEAMTEGA_LOGO_URI = "data:image/jpeg;base64,..."
# We locate the start of the value and find the closing quote

marker = 'TEAMTEGA_LOGO_URI = "'
start = content.find(marker)
if start == -1:
    print("ERROR: TEAMTEGA_LOGO_URI not found")
    exit(1)

val_start = start + len(marker)
# Find closing quote — it's the next unescaped " after val_start
val_end = content.index('"', val_start)

new_content = content[:start] + f'TEAMTEGA_LOGO_URI = "{uri}"' + content[val_end+1:]

with open('app/certificates.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Done. New TEAMTEGA_LOGO_URI length: {len(uri)}")
print(f"File size: {len(new_content)} chars")
