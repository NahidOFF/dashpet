#!/usr/bin/env python3
"""Petekh TikTok slayd hovuzu generatoru (v2 — TikTok təhlükəsiz zona).

TikTok 9:16 şəkli hündür ekranlara doldurub kənarları kəsir, alt hissəni isə
caption örtür. Ona görə bütün məzmun mərkəzi təhlükəsiz zonada yerləşdirilir:
üfüqi ~620px mərkəz zolağı, şaquli y=300..1360. Yazılar kiçik və mərkəzləşmiş.

İşlətmək:
    python3 social/generate_slides.py [--shot path/to/screenshot.png ...]
Nəticə: social/slides/*.png (1080x1920)
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
TEXT_MAX_W = 620          # üfüqi təhlükəsiz mətn eni
SAFE_TOP, SAFE_BOTTOM = 300, 1360

CREAM = (255, 247, 230)
ORANGE = (244, 155, 13)
ORANGE_DARK = (222, 127, 6)
YELLOW = (255, 217, 121)
NAVY = (46, 50, 64)
BROWN = (122, 59, 0)
WHITE = (255, 255, 255)

F_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

HOOKS = [
    ("Ev heyvanın üçün hər şey — Petekh", "Sifariş et, qapına gəlsin"),
    ("Pişiyin yemi bitib?", "5 dəqiqəyə sifariş et"),
    ("Zoomağazaya getməyə vaxt yoxdur?", "Petekh sənin yerinə gedər"),
    ("Bütün zoomağazalar bir tətbiqdə", "Qiymətləri müqayisə et"),
    ("Qidadan oyuncağa — hər şey burada", "Petekh ilə asan"),
    ("Sevimli dostun ac qalmasın", "Sürətli çatdırılma"),
    ("Ən sərfəli qiymətlər", "Müqayisə et, qazan"),
    ("İtinin sevimli yemi endirimlə", "Yalnız Petekh-də"),
]

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

CTAS = [
    ("Petekh-i sına", "petekh.com"),
    ("İndi qeydiyyatdan keç", "petekh.com"),
    ("Sevimli dostun üçün ən yaxşısı", "petekh.com"),
]

SHOT_OVERLAYS = [
    "Sadə və sürətli",
    "Bir dəqiqəyə başla",
    "Cibindəki zoomağaza",
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
    """Loqonun mərkəzindəki əsl it pəncəsini sprite kimi çıxarır."""
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


def pill(img, y=1265, text="petekh.com"):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_SANS, 32)
    pw, ph = 330, 74
    d.rounded_rectangle([(W - pw) // 2, y, (W + pw) // 2, y + ph], radius=37, fill=WHITE)
    center(d, y + 19, text, f, ORANGE_DARK)


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
    lc = logo_card(150, 34)
    img.paste(lc, ((W - 150) // 2, 330), lc)
    f_h = ImageFont.truetype(F_SERIF, 58)
    f_s = ImageFont.truetype(F_SANS, 36)
    y = center_block(d, 570, headline, f_h, head_c, 76)
    p = paw(84, head_c)
    img.paste(p, ((W - 84) // 2, y + 42), p)
    center_block(d, y + 168, sub, f_s, sub_c, 48)
    pill(img)
    return img


def feature_slide(title, sub, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(140, 32)
    img.paste(lc, ((W - 140) // 2, 320), lc)
    cx0, cy0, cx1, cy1 = 210, 520, 870, 1180
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=48, fill=WHITE)
    p = paw(120, ORANGE)
    img.paste(p, ((W - 120) // 2, cy0 + 70), p)
    f_t = ImageFont.truetype(F_SANS, 44)
    f_s = ImageFont.truetype(F_SANS, 32)
    y = center_block(d, cy0 + 250, title, f_t, NAVY, 58, max_w=560)
    center_block(d, y + 26, sub, f_s, ORANGE_DARK, 42, max_w=560)
    pill(img)
    return img


def shot_slide(shot_path, headline, scheme):
    img, head_c, _ = base(scheme)
    d = ImageDraw.Draw(img)
    f_h = ImageFont.truetype(F_SERIF, 46)
    y = center_block(d, 320, headline, f_h, head_c, 60)
    shot = Image.open(shot_path).convert("RGB")
    ph_w = 380
    ph_h = min(int(ph_w * shot.height / shot.width), 830)
    inner = shot.resize((ph_w - 28, ph_h - 28))
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner.width - 1, inner.height - 1], radius=34, fill=255)
    frame = Image.new("RGBA", (ph_w + 36, ph_h + 36), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    sh = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([26, 32, ph_w + 6, ph_h + 16], radius=48, fill=(60, 30, 0, 110))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    fd.rounded_rectangle([16, 16, ph_w + 15, ph_h + 15], radius=44, fill=NAVY)
    frame.paste(inner, (30, 30), mask)
    fd.rounded_rectangle([ph_w // 2 - 46, 21, ph_w // 2 + 62, 33], radius=6, fill=(20, 22, 30))
    img.paste(frame, ((W - frame.width) // 2, max(y + 40, 450)), frame)
    return img


def cta_slide(title, url, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(190, 44)
    img.paste(lc, ((W - 190) // 2, 420), lc)
    f_h = ImageFont.truetype(F_SERIF, 56)
    f_u = ImageFont.truetype(F_SANS, 46)
    y = center_block(d, 720, title, f_h, head_c, 74, max_w=600)
    bw, bh = 460, 104
    d.rounded_rectangle([(W - bw) // 2, y + 56, (W + bw) // 2, y + 56 + bh], radius=52, fill=NAVY)
    center(d, y + 56 + 27, url, f_u, WHITE)
    p = paw(84, head_c)
    img.paste(p, ((W - 84) // 2, y + 56 + bh + 60), p)
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

    for i, (t, u) in enumerate(CTAS):
        name = f"cta-{i:02d}.png"
        cta_slide(t, u, "orange" if i % 2 == 0 else "cream").save(os.path.join(OUT, name), optimize=True)
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
