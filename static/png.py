"""
Generates the Teamsamikoko Global Academy logo as a PNG
and the MyPy Tutor logo as a PNG, then base64-encodes both
and writes them to static/icons/ for use in certificates.
Run once: python static/png.py
"""

import os, struct, zlib, math, base64

def make_png_from_pixels(width, height, get_pixel):
    """Build a minimal PNG from a pixel-generator function."""
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            r, g, b, a = get_pixel(x, y, width, height)
            row += bytes([r, g, b, a])
        rows.append(row)

    raw = b''.join(b'\x00' + row for row in rows)
    compressed = zlib.compress(raw, 9)

    def chunk(name, data):
        c = struct.pack('>I', len(data)) + name + data
        return c + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)

    png  = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png


def in_circle(x, y, cx, cy, r):
    return (x - cx)**2 + (y - cy)**2 <= r**2

def circle_edge(x, y, cx, cy, r, width=3):
    d = math.sqrt((x - cx)**2 + (y - cy)**2)
    return abs(d - r) <= width / 2

def in_spike(x, y, cx, cy, r_inner, r_outer, n_spikes):
    dx, dy = x - cx, y - cy
    d = math.sqrt(dx**2 + dy**2)
    if d < r_inner or d > r_outer: return False
    angle = math.atan2(dy, dx)
    spike_angle = (2 * math.pi) / n_spikes
    a = angle % spike_angle
    norm = a / spike_angle
    # spike shape: triangular
    frac = abs(norm - 0.5) * 2
    r_at_angle = r_inner + (r_outer - r_inner) * (1 - frac * 0.6)
    return d <= r_at_angle


def academy_logo_pixel(x, y, w, h):
    """Generate the Teamsamikoko Global Academy seal pixel by pixel."""
    cx, cy = w / 2, h / 2
    # radii as fractions of half-width
    hw = w / 2
    R_outer    = hw * 0.97
    R_spike_in = hw * 0.83
    R_spike_out= hw * 0.97
    R_band_out = hw * 0.82
    R_band_in  = hw * 0.72
    R_inner    = hw * 0.70
    R_white    = hw * 0.68

    # Colors
    BLUE  = (0, 51, 204)
    WHITE = (255, 255, 255)
    TRANSP = (255, 255, 255, 0)

    dx, dy = x - cx, y - cy
    d = math.sqrt(dx**2 + dy**2)

    # Outside everything — transparent
    if d > R_outer + 1: return (255, 255, 255, 0)

    # Spike crown
    if in_spike(x, y, cx, cy, R_spike_in, R_spike_out, 36):
        return (*BLUE, 255)

    # Outer blue band
    if R_band_in <= d <= R_band_out:
        return (*BLUE, 255)

    # Inner white circle
    if d <= R_white:
        return (*WHITE, 255)

    # Blue ring between white and band
    if R_white < d < R_band_in:
        return (*BLUE, 255)

    return (*WHITE, 255)


def make_academy_logo(size=300):
    """Create the academy seal PNG at given size."""
    w = h = size
    cx, cy = w / 2.0, h / 2.0
    hw = w / 2.0

    R_outer     = hw * 0.97
    R_spike_in  = hw * 0.83
    R_spike_out = hw * 0.97
    R_band_out  = hw * 0.82
    R_band_in   = hw * 0.74
    R_inner_edge= hw * 0.72
    R_white     = hw * 0.70

    BLUE  = (10, 50, 200)
    DKBLUE= (0, 30, 150)
    WHITE = (255, 255, 255)

    def pixel(x, y, W, H):
        dx, dy = x - cx, y - cy
        d = math.sqrt(dx**2 + dy**2)

        if d > R_outer: return (255, 255, 255, 0)

        # Spike ring
        if in_spike(x, y, cx, cy, R_spike_in, R_spike_out, 36):
            return (*BLUE, 255)

        # Blue band
        if R_band_in <= d <= R_band_out:
            return (*BLUE, 255)

        # Ring between band_in and white
        if R_white < d < R_band_in:
            return (*DKBLUE, 255)

        # Inner white area
        if d <= R_white:
            # Draw simplified globe (top half)
            gx, gy = cx, cy - hw * 0.12
            gr = hw * 0.22
            if in_circle(x, y, gx, gy, gr):
                if circle_edge(x, y, gx, gy, gr, 2): return (*DKBLUE, 255)
                # meridian lines
                if abs(x - gx) < 1.5 or abs(y - gy) < 1.5: return (100, 100, 200, 180)
                return (200, 220, 255, 255)

            # Draw simplified books below globe
            book_y = cy + hw * 0.08
            if cy + hw * 0.01 < y < cy + hw * 0.18:
                if cx - hw * 0.22 < x < cx + hw * 0.28:
                    stripe_h = hw * 0.055
                    if abs(y - book_y) < stripe_h: return (*DKBLUE, 180)
                    if abs(y - (book_y + stripe_h * 2.2)) < stripe_h * 0.8: return (*DKBLUE, 140)

            return (*WHITE, 255)

        return (*BLUE, 255)

    return make_png_from_pixels(w, h, pixel)


def make_mpt_logo(size=300):
    """Create a simple MPT (MyPy Tutor) logo PNG."""
    w = h = size
    cx, cy = w / 2.0, h / 2.0
    hw = w / 2.0

    DARK   = (15, 17, 23)
    COPPER = (180, 115, 50)
    GOLD   = (200, 165, 50)
    GREEN  = (50, 120, 70)
    WHITE  = (230, 220, 200)

    def pixel(x, y, W, H):
        dx, dy = x - cx, y - cy
        d = math.sqrt(dx**2 + dy**2)

        # Dark circular background
        if d > hw * 0.97: return (0, 0, 0, 0)
        if d > hw * 0.94: return (*GOLD, 255)
        if d > hw * 0.90: return (*DARK, 255)

        # Background
        bg = (*DARK, 255)

        # Letter M region (left)
        if cy - hw*0.35 < y < cy + hw*0.22:
            mx1, mx2 = cx - hw*0.60, cx - hw*0.20
            if mx1 < x < mx2:
                # Simple M shape
                lw = hw * 0.06
                if x < mx1 + lw or x > mx2 - lw: return (*COPPER, 255)
                mid = (mx1 + mx2) / 2
                slope = abs(x - mid) / (hw * 0.15)
                top_y = cy - hw*0.35 + slope * hw * 0.2
                if y < top_y + lw: return (*COPPER, 255)

        # Letter P region (middle)
        if cy - hw*0.35 < y < cy + hw*0.22:
            px1, px2 = cx - hw*0.15, cx + hw*0.18
            if px1 < x < px2:
                lw = hw * 0.06
                if x < px1 + lw: return (*COPPER, 255)
                if y < cy - hw*0.35 + lw * 2 or y > cy - hw*0.35 + hw*0.32:
                    if x < px2 - lw*0.5: return (*COPPER, 255)
                # P bowl
                bowl_cx, bowl_cy = px1 + lw*1.5 + hw*0.10, cy - hw*0.12
                if in_circle(x, y, bowl_cx, bowl_cy, hw*0.10):
                    if circle_edge(x, y, bowl_cx, bowl_cy, hw*0.10, hw*0.06): return (*COPPER, 255)
                    if x > px1 + lw: return (*DARK, 255)

        # Letter T region (right)
        if cy - hw*0.35 < y < cy + hw*0.22:
            tx1, tx2 = cx + hw*0.22, cx + hw*0.60
            if tx1 < x < tx2:
                lw = hw * 0.06
                mid = (tx1 + tx2) / 2
                # top bar
                if y < cy - hw*0.28: return (*COPPER, 255)
                # stem
                if mid - lw/2 < x < mid + lw/2: return (*COPPER, 255)

        # Snake wrapping (simplified S-curve)
        for t in range(100):
            tt = t / 99.0
            sx = cx + hw*0.15 * math.sin(tt * math.pi * 2.5) + hw*0.30
            sy = cy - hw*0.50 + tt * hw * 1.0
            if math.sqrt((x-sx)**2 + (y-sy)**2) < hw*0.055:
                # scale pattern
                if int(tt*20) % 2 == 0: return (*GREEN, 255)
                return (30, 90, 50, 255)

        # Pi symbol
        pi_cx, pi_cy = cx + hw*0.08, cy - hw*0.40
        if math.sqrt((x-pi_cx)**2 + (y-pi_cy)**2) < hw*0.14:
            return (*GOLD, 200)

        # Bottom text area — gold line
        if cy + hw*0.52 < y < cy + hw*0.58:
            return (*GOLD, 200)

        return bg

    return make_png_from_pixels(w, h, pixel)


if __name__ == "__main__":
    os.makedirs("static/icons", exist_ok=True)

    print("Generating academy logo...")
    academy_png = make_academy_logo(300)
    with open("static/icons/logo-academy.png", "wb") as f:
        f.write(academy_png)
    print(f"  → static/icons/logo-academy.png ({len(academy_png):,} bytes)")

    print("Generating MyPy Tutor logo...")
    mpt_png = make_mpt_logo(300)
    with open("static/icons/logo-mpt.png", "wb") as f:
        f.write(mpt_png)
    print(f"  → static/icons/logo-mpt.png ({len(mpt_png):,} bytes)")

    # Base64-encode both for embedding
    academy_b64 = base64.b64encode(academy_png).decode()
    mpt_b64     = base64.b64encode(mpt_png).decode()

    print(f"\nAcademy b64 length: {len(academy_b64)}")
    print(f"MPT b64 length:     {len(mpt_b64)}")
    print("\nDone! Now run: python app/embed_logos.py")
