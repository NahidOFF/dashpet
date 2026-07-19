#!/usr/bin/env python3
"""Petekh TikTok slayd hovuzu generatoru (v3 — pre-launch teaser + follow).

Petekh hələ açılmayıb (avqustda gözlənilir), ona görə mesajlar "indi sifariş et"
deyil, "avqustda gəlir — izlə" teaser üslubundadır. Hər slaydın altında incə,
ardıcıl "+ İzlə" çipi var (səbəb: açılışı qaçırmamaq); sonuncu (CTA) slaydda
güclü follow çağırışı.

TikTok təhlükəsiz zona: mətn/loqo mərkəzi ~620px zolaqda, şaquli y=300..1300;
alt caption zonasına və kəsilən kənarlara heç nə düşmür.

    python3 social/generate_slides.py [--shot ekran.png ...]
"""
import argparse
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "social", "slides")
LOGO = os.path.join(ROOT, "logo-mark-t.png")

W, H = 1080, 1920
TEXT_MAX_W = 620

CREAM = (255, 247, 230)
ORANGE = (244, 155, 13)
ORANGE_DARK = (222, 127, 6)
YELLOW = (255, 217, 121)
NAVY = (46, 50, 64)
BROWN = (122, 59, 0)
WHITE = (255, 255, 255)

F_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Teaser hook-lar (açılış avqustda) — birinci slayd
HOOKS = [
    ("Ev heyvanın üçün hər şey — bir tətbiqdə", "Petekh avqustda gəlir"),
    ("Pişiyin yemi bitəndə panika?", "Tezliklə buna son"),
    ("Zoomağazaya getməyə vaxt yoxdur?", "Avqustdan Petekh sənin yerinə gedəcək"),
    ("Bütün zoomağazalar bir tətbiqdə", "Tezliklə — Petekh"),
    ("Qidadan oyuncağa hər şey", "Bir ünvanda, avqustda"),
    ("Bakıda pet alış-verişi dəyişir", "Petekh yolda"),
    ("Ən sərfəli qiymətləri müqayisə et", "Açılış avqustda"),
    ("Sevimli dostun üçün böyük yenilik", "Az qalıb"),
]

# Dəyər vədləri (nə gətiririk) — orta slaydlar
FEATURES = [
    ("Çoxmağazalı seçim", "Bir səbətdə ən yaxşı qiymət"),
    ("Qapına çatdırılma", "Evdən çıxmadan sifariş"),
    ("Endirim və kampaniyalar", "Hər həftə yeni təkliflər"),
    ("Pişik, it, quş və digərləri", "Hamısı üçün hər şey"),
    ("Təhlükəsiz ödəniş", "Kartla və ya nağd"),
    ("Rəylərlə seçim", "Digər sahiblərin təcrübəsi"),
    ("Sifarişini izlə", "Harada olduğunu həmişə bil"),
    ("Yerli mağazaları dəstəklə", "Şəhərindəki zoomağazalar"),
]

# CTA (son slayd) — güclü follow çağırışı
CTAS = [
    ("Açılışı qaçırma", "İzlə — avqustda xəbər ver"),
    ("İlk sınayanlardan ol", "İzlə, açılışdan xəbərdar ol"),
    ("Böyük gün yaxınlaşır", "İzlə — Petekh avqustda"),
]

SHOT_OVERLAYS = [
    "Belə görünəcək",
    "Cibindəki zoomağaza",
    "Avqustda səndə",
]


def gradient(img, top, bottom):
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))


def hexagons(img, color=(255, 255, 255, 70)):
    def hx(cx, cy, r):
        return [(cx + r * math.cos(math.radians(60 * i - 30)),
                 cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for cx, cy, r in [(90, 380, 110), (1000, 300, 140), (70, 1560, 130), (1010, 1460, 120)]:
        d.polygon(hx(cx, cy, r), outline=color, width=9)
    img.paste(layer, (0, 0), layer)


_PAW_SPRITE = None


def _paw_sprite():
    global _PAW_SPRITE
    if _PAW_SPRITE is None:
        logo = Image.open(LOGO).convert("RGBA")
        px = logo.load()
        w, h = logo.size
        mask = Image.new("L", (w, h), 0)
        mp = mask.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a > 100 and r < 110 and g < 110 and b < 110:
                    mp[x, y] = a
        _PAW_SPRITE = mask.crop(mask.getbbox())
    return _PAW_SPRITE


def paw(size, color):
    sprite = _paw_sprite()
    ratio = min(size / sprite.width, size / sprite.height)
    m = sprite.resize((max(1, int(sprite.width * ratio)), max(1, int(sprite.height * ratio))))
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    solid = Image.new("RGBA", m.size, tuple(color[:3]) + (255,))
    layer.paste(solid, ((size - m.width) // 2, (size - m.height) // 2), m)
    return layer


def logo_card(size=150, radius=34):
    logo = Image.open(LOGO).convert("RGBA")
    logo.thumbnail((int(size * 0.74), int(size * 0.74)))
    card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=WHITE)
    card.paste(logo, ((size - logo.width) // 2, (size - logo.height) // 2), logo)
    return card


def wrap(d, text, font, max_w=TEXT_MAX_W):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) > max_w and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = t
    lines.append(cur)
    return lines


def center(d, y, text, font, fill):
    d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)


def center_block(d, y, text, font, fill, line_h, max_w=TEXT_MAX_W):
    for ln in wrap(d, text, font, max_w):
        center(d, y, ln, font, fill)
        y += line_h
    return y


def follow_chip(img, y=1230, subtext="petekh.com · avqustda"):
    """Hər slaydın altında incə, ardıcıl follow çağırışı."""
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_SANS, 34)
    label = "+ İzlə"
    tw = d.textlength(label, font=f)
    pw, ph = int(tw) + 96, 76
    x0 = (W - pw) // 2
    # kölgə
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0, y + 4, x0 + pw, y + ph + 4], radius=ph // 2, fill=(40, 44, 60, 90))
    img.paste(Image.alpha_composite(img.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(8))).convert("RGB"), (0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y, x0 + pw, y + ph], radius=ph // 2, fill=NAVY)
    d.text(((W - tw) / 2, y + 18), label, font=f, fill=WHITE)
    fs = ImageFont.truetype(F_SANS, 26)
    center(d, y + ph + 14, subtext, fs, ORANGE_DARK)


def base(scheme):
    img = Image.new("RGB", (W, H), CREAM)
    if scheme == "orange":
        gradient(img, YELLOW, ORANGE)
        hexagons(img)
        return img, BROWN, NAVY
    gradient(img, CREAM, (250, 232, 200))
    hexagons(img, (244, 155, 13, 45))
    return img, ORANGE_DARK, NAVY


def hero_slide(headline, sub, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(146, 34)
    img.paste(lc, ((W - 146) // 2, 315), lc)
    f_h = ImageFont.truetype(F_SERIF, 56)
    f_s = ImageFont.truetype(F_SANS, 34)
    y = center_block(d, 540, headline, f_h, head_c, 72)
    p = paw(76, head_c)
    img.paste(p, ((W - 76) // 2, y + 34), p)
    center_block(d, y + 150, sub, f_s, sub_c, 46)
    follow_chip(img)
    return img


def feature_slide(title, sub, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(132, 30)
    img.paste(lc, ((W - 132) // 2, 315), lc)
    cx0, cy0, cx1, cy1 = 220, 500, 860, 1120
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=46, fill=WHITE)
    p = paw(112, ORANGE)
    img.paste(p, ((W - 112) // 2, cy0 + 62), p)
    f_t = ImageFont.truetype(F_SANS, 44)
    f_s = ImageFont.truetype(F_SANS, 32)
    y = center_block(d, cy0 + 234, title, f_t, NAVY, 56, max_w=560)
    center_block(d, y + 22, sub, f_s, ORANGE_DARK, 42, max_w=560)
    follow_chip(img)
    return img


def shot_slide(shot_path, headline, scheme):
    img, head_c, _ = base(scheme)
    d = ImageDraw.Draw(img)
    f_h = ImageFont.truetype(F_SERIF, 44)
    center_block(d, 315, headline, f_h, head_c, 58)
    shot = Image.open(shot_path).convert("RGB")
    ph_w = 360
    ph_h = min(int(ph_w * shot.height / shot.width), 720)
    inner = shot.resize((ph_w - 26, ph_h - 26))
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner.width - 1, inner.height - 1], radius=32, fill=255)
    frame = Image.new("RGBA", (ph_w + 34, ph_h + 34), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    sh = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([24, 30, ph_w + 6, ph_h + 14], radius=44, fill=(60, 30, 0, 110))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(13)))
    fd.rounded_rectangle([15, 15, ph_w + 14, ph_h + 14], radius=42, fill=NAVY)
    frame.paste(inner, (28, 28), mask)
    fd.rounded_rectangle([ph_w // 2 - 44, 20, ph_w // 2 + 58, 31], radius=6, fill=(20, 22, 30))
    img.paste(frame, ((W - frame.width) // 2, 440), frame)
    follow_chip(img)
    return img


def cta_slide(title, follow_line, scheme):
    """Son slayd — güclü follow çağırışı əsas mesajdır."""
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(176, 40)
    img.paste(lc, ((W - 176) // 2, 380), lc)
    f_h = ImageFont.truetype(F_SERIF, 58)
    y = center_block(d, 640, title, f_h, head_c, 76, max_w=600)
    # böyük follow düyməsi
    f_b = ImageFont.truetype(F_SANS, 48)
    label = "+ İzlə"
    tw = d.textlength(label, font=f_b)
    bw, bh = int(tw) + 150, 116
    bx, by = (W - bw) // 2, y + 44
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=NAVY)
    d.text(((W - tw) / 2, by + 30), label, font=f_b, fill=WHITE)
    f_r = ImageFont.truetype(F_SANS, 34)
    center_block(d, by + bh + 34, follow_line, f_r, sub_c, 46, max_w=620)
    f_u = ImageFont.truetype(F_SANS, 30)
    center(d, 1250, "petekh.com · avqustda", f_u, ORANGE_DARK)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", action="append", default=[], help="real tətbiq ekran görüntüsü")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    made = []

    for i, (headline, sub) in enumerate(HOOKS):
        for scheme in ("orange", "cream"):
            name = f"hook-{i:02d}-{scheme}.png"
            hero_slide(headline, sub, scheme).save(os.path.join(OUT, name), optimize=True)
            made.append(name)

    for i, (t, s) in enumerate(FEATURES):
        name = f"feature-{i:02d}.png"
        feature_slide(t, s, "orange" if i % 2 == 0 else "cream").save(os.path.join(OUT, name), optimize=True)
        made.append(name)

    for i, (t, fl) in enumerate(CTAS):
        name = f"cta-{i:02d}.png"
        cta_slide(t, fl, "orange" if i % 2 == 0 else "cream").save(os.path.join(OUT, name), optimize=True)
        made.append(name)

    for si, shot in enumerate(args.shot):
        for oi, ov in enumerate(SHOT_OVERLAYS):
            name = f"shot-{si:02d}-{oi}.png"
            shot_slide(shot, ov, "orange" if oi % 2 == 0 else "cream").save(os.path.join(OUT, name), optimize=True)
            made.append(name)

    for n in made:
        print(n)
    print(f"# {len(made)} slayd -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
