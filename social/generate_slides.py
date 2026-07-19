#!/usr/bin/env python3
"""Petekh TikTok slayd hovuzu generatoru.

Brend şablonlarından deterministik slaydlar yaradır (AI deyil — loqo, mətn və
ekran görüntüləri dəqiq yerləşdirilir). İşlətmək:

    python3 social/generate_slides.py [--shot path/to/screenshot.png ...]

Nəticə: social/slides/*.png (1080x1920) və stdout-da fayl siyahısı.
Yeni real tətbiq ekran görüntüləri əlavə etmək üçün --shot ilə verin və
yenidən işə salın; content.json-dakı "shots" bölməsini yeniləyin.
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
    ("Ev heyvanın üçün", "hər şey — Petekh", "Sifariş et, qapına gəlsin"),
    ("Pişiyin yemi", "bitib?", "5 dəqiqəyə sifariş et"),
    ("Zoomağazaya getməyə", "vaxt yoxdur?", "Petekh sənin yerinə gedər"),
    ("Bütün zoomağazalar", "bir tətbiqdə", "Qiymətləri müqayisə et"),
    ("Qidadan oyuncağa —", "hər şey burada", "Petekh ilə asan"),
    ("Sevimli dostun", "ac qalmasın", "Sürətli çatdırılma"),
    ("Ən sərfəli", "qiymətlər", "Müqayisə et, qazan"),
    ("İtinin sevimli yemi", "endirimlə", "Yalnız Petekh-də"),
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
    "Petekh — cibindəki zoomağaza",
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
    for cx, cy, r in [(120, 320, 130), (990, 240, 170), (80, 1650, 160), (1010, 1500, 140), (950, 1800, 110)]:
        d.polygon(hx(cx, cy, r), outline=color, width=10)
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
        bbox = mask.getbbox()
        _PAW_SPRITE = mask.crop(bbox)
    return _PAW_SPRITE


def paw(size, color):
    """Loqodakı real pəncə izi, istənilən rəngdə."""
    sprite = _paw_sprite()
    ratio = min(size / sprite.width, size / sprite.height)
    m = sprite.resize((max(1, int(sprite.width * ratio)), max(1, int(sprite.height * ratio))))
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    solid = Image.new("RGBA", m.size, tuple(color[:3]) + (255,))
    layer.paste(solid, ((size - m.width) // 2, (size - m.height) // 2), m)
    return layer


def logo_card(size=230, radius=52):
    logo = Image.open(LOGO).convert("RGBA")
    logo.thumbnail((int(size * 0.74), int(size * 0.74)))
    card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=WHITE)
    card.paste(logo, ((size - logo.width) // 2, (size - logo.height) // 2), logo)
    return card


def center(d, y, text, font, fill):
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, y), text, font=font, fill=fill)


def footer_pill(img, text="petekh.com"):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_SANS, 40)
    pw, ph = 440, 92
    d.rounded_rectangle([(W - pw) // 2, 1770, (W + pw) // 2, 1770 + ph], radius=46, fill=WHITE)
    center(d, 1770 + 24, text, f, ORANGE_DARK)


def base(scheme):
    img = Image.new("RGB", (W, H), CREAM)
    if scheme == "orange":
        gradient(img, YELLOW, ORANGE)
        hexagons(img)
        return img, BROWN, NAVY
    gradient(img, CREAM, (250, 232, 200))
    hexagons(img, (244, 155, 13, 45))
    return img, ORANGE_DARK, NAVY


def hero_slide(idx, line1, line2, sub, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    img.paste(logo_card(), ((W - 230) // 2, 120), logo_card())
    f_h = ImageFont.truetype(F_SERIF, 96)
    f_s = ImageFont.truetype(F_SANS, 48)
    center(d, 480, line1, f_h, head_c)
    center(d, 610, line2, f_h, head_c)
    p = paw(120, head_c + (255,) if len(head_c) == 3 else head_c)
    img.paste(p, ((W - 120) // 2, 800), p)
    center(d, 1000, sub, f_s, sub_c)
    footer_pill(img)
    return img


def feature_slide(idx, title, sub, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    card_w, card_h = 900, 760
    cx, cy = (W - card_w) // 2, 560
    d.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=60, fill=WHITE)
    img.paste(logo_card(180, 42), ((W - 180) // 2, 150), logo_card(180, 42))
    p = paw(190, ORANGE + (255,))
    img.paste(p, ((W - 190) // 2, cy + 90), p)
    f_t = ImageFont.truetype(F_SANS, 62)
    f_s = ImageFont.truetype(F_SANS, 42)
    # sətirlərə böl
    words, lines, cur = title.split(), [], ""
    dd = ImageDraw.Draw(img)
    for w_ in words:
        t = (cur + " " + w_).strip()
        if dd.textlength(t, font=f_t) > card_w - 120:
            lines.append(cur)
            cur = w_
        else:
            cur = t
    lines.append(cur)
    ty = cy + 340
    for ln in lines:
        center(dd, ty, ln, f_t, NAVY)
        ty += 84
    center(dd, ty + 30, sub, f_s, ORANGE_DARK)
    footer_pill(img)
    return img


def shot_slide(idx, shot_path, headline, scheme):
    img, head_c, _ = base(scheme)
    d = ImageDraw.Draw(img)
    f_h = ImageFont.truetype(F_SERIF, 76)
    center(d, 140, headline, f_h, head_c)
    shot = Image.open(shot_path).convert("RGB")
    ph_w = 620
    ph_h = int(ph_w * shot.height / shot.width)
    ph_h = min(ph_h, 1380)
    inner = shot.resize((ph_w - 36, ph_h - 36))
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner.width - 1, inner.height - 1], radius=48, fill=255)
    frame = Image.new("RGBA", (ph_w + 40, ph_h + 40), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    sh = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([30, 40, ph_w + 10, ph_h + 20], radius=70, fill=(60, 30, 0, 110))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    fd.rounded_rectangle([20, 20, ph_w + 19, ph_h + 19], radius=64, fill=NAVY)
    frame.paste(inner, (38, 38), mask)
    fd.rounded_rectangle([ph_w // 2 - 70, 26, ph_w // 2 + 110, 44], radius=10, fill=(20, 22, 30))
    img.paste(frame, ((W - frame.width) // 2, 310), frame)
    footer_pill(img)
    return img


def cta_slide(idx, title, url, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    img.paste(logo_card(280, 62), ((W - 280) // 2, 380), logo_card(280, 62))
    f_h = ImageFont.truetype(F_SERIF, 84)
    f_u = ImageFont.truetype(F_SANS, 64)
    words, lines, cur = title.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f_h) > W - 140:
            lines.append(cur)
            cur = w_
        else:
            cur = t
    lines.append(cur)
    ty = 800
    for ln in lines:
        center(d, ty, ln, f_h, head_c)
        ty += 110
    d.rounded_rectangle([(W - 560) // 2, ty + 90, (W + 560) // 2, ty + 210], radius=60, fill=NAVY)
    center(d, ty + 118, url, f_u, WHITE)
    p = paw(110, head_c + (255,))
    img.paste(p, ((W - 110) // 2, ty + 300), p)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", action="append", default=[], help="real tətbiq ekran görüntüsü (bir neçə dəfə verilə bilər)")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    made = []

    for i, (l1, l2, sub) in enumerate(HOOKS):
        for scheme in ("orange", "cream"):
            name = f"hook-{i:02d}-{scheme}.png"
            hero_slide(i, l1, l2, sub, scheme).save(os.path.join(OUT, name), optimize=True)
            made.append(name)

    for i, (t, s) in enumerate(FEATURES):
        scheme = "orange" if i % 2 == 0 else "cream"
        name = f"feature-{i:02d}.png"
        feature_slide(i, t, s, scheme).save(os.path.join(OUT, name), optimize=True)
        made.append(name)

    for i, (t, u) in enumerate(CTAS):
        name = f"cta-{i:02d}.png"
        cta_slide(i, t, u, "orange" if i % 2 == 0 else "cream").save(os.path.join(OUT, name), optimize=True)
        made.append(name)

    for si, shot in enumerate(args.shot):
        for oi, ov in enumerate(SHOT_OVERLAYS):
            name = f"shot-{si:02d}-{oi}.png"
            shot_slide(si, shot, ov, "orange" if oi % 2 == 0 else "cream").save(os.path.join(OUT, name), optimize=True)
            made.append(name)

    for n in made:
        print(n)
    print(f"# {len(made)} slayd -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
