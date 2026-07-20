#!/usr/bin/env python3
"""Petekh TikTok slayd generatoru (v7 — 9:16 kətan + telefon çərçivəsi).

- Kətan 1080x1920 (9:16).
- Şəkil slaydlarında app ekranı DİK TELEFON çərçivəsində, tam görünür (bir az
  aşağı yerləşdirilib ki, üstü TikTok axtarış zolağına düşməsin).
- Başlıq yuxarıda, '+ İzlə' çipi altda. Hook/feature/CTA tarazlaşdırılıb.

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
TEXT_MAX_W = 660

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
    ("Ev heyvanın üçün hər şey — bir tətbiqdə", "Petekh avqustda gəlir"),
    ("Pişiyin yemi bitəndə panika?", "Tezliklə buna son"),
    ("Zoomağazaya getməyə vaxt yoxdur?", "Avqustdan Petekh sənin yerinə gedəcək"),
    ("Bütün zoomağazalar bir tətbiqdə", "Tezliklə — Petekh"),
    ("Qidadan oyuncağa hər şey", "Bir ünvanda, avqustda"),
    ("Bakıda pet alış-verişi dəyişir", "Petekh yolda"),
    ("Ən sərfəli qiymətləri müqayisə et", "Açılış avqustda"),
    ("Sevimli dostun üçün böyük yenilik", "Az qalıb"),
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
    ("Açılışı qaçırma", "İzlə — avqustda xəbər ver"),
    ("İlk sınayanlardan ol", "İzlə, açılışdan xəbərdar ol"),
    ("Böyük gün yaxınlaşır", "İzlə — Petekh avqustda"),
]

SHOT_CAPTIONS = {
    "01-home": "Bütün məhsullar bir yerdə",
    "02-product": "Qiymət, stok, abunə",
    "03-cart": "Bir toxunuşla sifariş",
    "04-mypets": "Heyvanının öz profili",
    "06-bal": "Al, Bal qazan",
    "10-petai": "PetAI — ağıllı köməkçin",
}


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
    for cx, cy, r in [(90, 360, 115), (1000, 300, 145), (70, 1600, 135), (1010, 1500, 125)]:
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


def follow_chip(img, y, subtext="petekh.com · avqustda"):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_SANS, 34)
    label = "+ İzlə"
    tw = d.textlength(label, font=f)
    pw, ph = int(tw) + 100, 78
    x0 = (W - pw) // 2
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0, y + 4, x0 + pw, y + ph + 4], radius=ph // 2, fill=(40, 44, 60, 90))
    img.paste(Image.alpha_composite(img.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(8))).convert("RGB"), (0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y, x0 + pw, y + ph], radius=ph // 2, fill=NAVY)
    d.text(((W - tw) / 2, y + 19), label, font=f, fill=WHITE)
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
    lc = logo_card(158, 36)
    img.paste(lc, ((W - 158) // 2, 470), lc)
    f_h = ImageFont.truetype(F_SERIF, 60)
    f_s = ImageFont.truetype(F_SANS, 36)
    y = center_block(d, 760, headline, f_h, head_c, 80)
    p = paw(84, head_c)
    img.paste(p, ((W - 84) // 2, y + 40), p)
    y2 = center_block(d, y + 168, sub, f_s, sub_c, 50)
    follow_chip(img, y2 + 120)
    return img


def feature_slide(title, sub, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(140, 32)
    img.paste(lc, ((W - 140) // 2, 400), lc)
    cx0, cy0, cx1, cy1 = 200, 620, 880, 1300
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=50, fill=WHITE)
    p = paw(120, ORANGE)
    img.paste(p, ((W - 120) // 2, cy0 + 70), p)
    f_t = ImageFont.truetype(F_SANS, 48)
    f_s = ImageFont.truetype(F_SANS, 34)
    y = center_block(d, cy0 + 250, title, f_t, NAVY, 60, max_w=580)
    center_block(d, y + 24, sub, f_s, ORANGE_DARK, 44, max_w=580)
    follow_chip(img, 1420)
    return img


def shot_slide(shot_path, caption, scheme):
    """App ekranı DİK TELEFON çərçivəsində, tam görünür (9:16 kətan)."""
    img, head_c, _ = base(scheme)
    d = ImageDraw.Draw(img)
    f_h = ImageFont.truetype(F_SERIF, 46)
    center_block(d, 210, caption, f_h, head_c, 58)

    shot = Image.open(shot_path).convert("RGB")
    ph_w = 540
    ph_h = int(ph_w * shot.height / shot.width)
    inner = shot.resize((ph_w - 28, ph_h - 28))
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner.width - 1, inner.height - 1], radius=42, fill=255)
    frame = Image.new("RGBA", (ph_w + 38, ph_h + 38), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    sh = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([26, 32, ph_w + 8, ph_h + 16], radius=54, fill=(60, 30, 0, 120))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(15)))
    fd.rounded_rectangle([15, 15, ph_w + 22, ph_h + 22], radius=52, fill=NAVY)
    frame.paste(inner, (28, 28), mask)
    fd.rounded_rectangle([ph_w // 2 - 48, 21, ph_w // 2 + 66, 33], radius=7, fill=(20, 22, 30))
    # bir az aşağı — üstü TikTok axtarış zolağından təmiz qalsın
    img.paste(frame, ((W - frame.width) // 2, 350), frame)
    follow_chip(img, 350 + ph_h + 60)
    return img


def cta_slide(title, follow_line, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(190, 44)
    img.paste(lc, ((W - 190) // 2, 470), lc)
    f_h = ImageFont.truetype(F_SERIF, 58)
    y = center_block(d, 760, title, f_h, head_c, 78, max_w=620)
    f_b = ImageFont.truetype(F_SANS, 50)
    label = "+ İzlə"
    tw = d.textlength(label, font=f_b)
    bw, bh = int(tw) + 150, 120
    bx, by = (W - bw) // 2, y + 46
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=NAVY)
    d.text(((W - tw) / 2, by + 32), label, font=f_b, fill=WHITE)
    f_r = ImageFont.truetype(F_SANS, 34)
    y2 = center_block(d, by + bh + 36, follow_line, f_r, sub_c, 48, max_w=640)
    f_u = ImageFont.truetype(F_SANS, 30)
    center(d, y2 + 20, "petekh.com · avqustda", f_u, ORANGE_DARK)
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
        base_name = os.path.splitext(os.path.basename(shot))[0]
        caption = SHOT_CAPTIONS.get(base_name, "Belə görünəcək")
        for oi, scheme in enumerate(("cream", "orange")):
            name = f"shot-{si:02d}-{oi}.png"
            shot_slide(shot, caption, scheme).save(os.path.join(OUT, name), optimize=True)
            made.append(name)

    for n in made:
        print(n)
    print(f"# {len(made)} slayd -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
