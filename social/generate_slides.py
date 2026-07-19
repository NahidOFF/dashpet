#!/usr/bin/env python3
"""Petekh TikTok slayd generatoru (v5 — tam ekran 9:19.5 + böyük telefon).

Dəyişikliklər (istifadəçi geri-bildirişi):
- Kətan 1080x2340 (9:19.5) — müasir telefonları tam doldurur, TikTok-un qara
  letterbox zolağı olmur.
- Şəkil (real app ekranı) telefon çərçivəsində xeyli böyüdülüb; ekran görüntüsü
  yuxarı hissəyə görə kəsilir ki, çərçivə enli və oxunaqlı olsun.
- Bütün mətn/loqo mərkəzi 640px zolaqda, şaquli təhlükəsiz aralıqda (330..1760);
  alt ~25% TikTok caption/düymələri üçün boş saxlanılır.

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

W, H = 1080, 2340
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

# Real app ekranlarına uyğun başlıqlar (fayl adına görə)
SHOT_CAPTIONS = {
    "01-home": "Bütün məhsullar bir yerdə",
    "02-product": "Qiymət, stok, abunə — hamısı burada",
    "03-cart": "Bir toxunuşla sifariş",
    "04-mypets": "Heyvanının öz profili",
    "06-bal": "Al, Bal qazan",
    "10-petai": "PetAI — ağıllı köməkçin",
}

# Ekran görüntüsünün yuxarıdan neçə faizi göstərilsin (telefon enli görünsün)
SHOT_CROP = 0.60


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
    for cx, cy, r in [(90, 440, 120), (1000, 340, 150), (70, 1960, 140),
                      (1010, 1820, 130), (120, 2180, 110)]:
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


def logo_card(size=160, radius=36):
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


def follow_chip(img, y=1560, subtext="petekh.com · avqustda"):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_SANS, 36)
    label = "+ İzlə"
    tw = d.textlength(label, font=f)
    pw, ph = int(tw) + 104, 82
    x0 = (W - pw) // 2
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0, y + 5, x0 + pw, y + ph + 5], radius=ph // 2, fill=(40, 44, 60, 90))
    img.paste(Image.alpha_composite(img.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(9))).convert("RGB"), (0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y, x0 + pw, y + ph], radius=ph // 2, fill=NAVY)
    d.text(((W - tw) / 2, y + 20), label, font=f, fill=WHITE)
    fs = ImageFont.truetype(F_SANS, 28)
    center(d, y + ph + 16, subtext, fs, ORANGE_DARK)


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
    lc = logo_card(168, 38)
    img.paste(lc, ((W - 168) // 2, 620), lc)
    f_h = ImageFont.truetype(F_SERIF, 64)
    f_s = ImageFont.truetype(F_SANS, 38)
    y = center_block(d, 920, headline, f_h, head_c, 84)
    p = paw(88, head_c)
    img.paste(p, ((W - 88) // 2, y + 46), p)
    y2 = center_block(d, y + 184, sub, f_s, sub_c, 52)
    follow_chip(img, y=y2 + 150)
    return img


def feature_slide(title, sub, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(150, 34)
    img.paste(lc, ((W - 150) // 2, 560), lc)
    cx0, cy0, cx1, cy1 = 190, 810, 890, 1530
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=52, fill=WHITE)
    p = paw(126, ORANGE)
    img.paste(p, ((W - 126) // 2, cy0 + 74), p)
    f_t = ImageFont.truetype(F_SANS, 50)
    f_s = ImageFont.truetype(F_SANS, 36)
    y = center_block(d, cy0 + 270, title, f_t, NAVY, 64, max_w=600)
    center_block(d, y + 26, sub, f_s, ORANGE_DARK, 48, max_w=600)
    follow_chip(img, y=1650)
    return img


def shot_slide(shot_path, caption, scheme):
    img, head_c, _ = base(scheme)
    d = ImageDraw.Draw(img)
    f_h = ImageFont.truetype(F_SERIF, 48)
    center_block(d, 210, caption, f_h, head_c, 60)

    # Dik (portret) telefon, tam boy — kəsmə yoxdur, böyük göstərilir
    shot = Image.open(shot_path).convert("RGB")
    ph_w = 570
    ph_h = int(ph_w * shot.height / shot.width)
    inner = shot.resize((ph_w - 30, ph_h - 30))
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner.width - 1, inner.height - 1], radius=44, fill=255)
    frame = Image.new("RGBA", (ph_w + 40, ph_h + 40), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    sh = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([28, 34, ph_w + 8, ph_h + 18], radius=58, fill=(60, 30, 0, 120))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    fd.rounded_rectangle([16, 16, ph_w + 23, ph_h + 23], radius=56, fill=NAVY)   # telefon gövdəsi
    frame.paste(inner, (30, 30), mask)
    fd.rounded_rectangle([ph_w // 2 - 50, 22, ph_w // 2 + 70, 35], radius=7, fill=(20, 22, 30))  # notch
    img.paste(frame, ((W - frame.width) // 2, 330), frame)
    follow_chip(img, y=1620)
    return img


def cta_slide(title, follow_line, scheme):
    img, head_c, sub_c = base(scheme)
    d = ImageDraw.Draw(img)
    lc = logo_card(196, 44)
    img.paste(lc, ((W - 196) // 2, 560), lc)
    f_h = ImageFont.truetype(F_SERIF, 62)
    y = center_block(d, 900, title, f_h, head_c, 82, max_w=640)
    f_b = ImageFont.truetype(F_SANS, 52)
    label = "+ İzlə"
    tw = d.textlength(label, font=f_b)
    bw, bh = int(tw) + 160, 126
    bx, by = (W - bw) // 2, y + 50
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=NAVY)
    d.text(((W - tw) / 2, by + 34), label, font=f_b, fill=WHITE)
    f_r = ImageFont.truetype(F_SANS, 36)
    y2 = center_block(d, by + bh + 40, follow_line, f_r, sub_c, 50, max_w=660)
    f_u = ImageFont.truetype(F_SANS, 32)
    center(d, y2 + 24, "petekh.com · avqustda", f_u, ORANGE_DARK)
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
