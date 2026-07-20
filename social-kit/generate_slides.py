#!/usr/bin/env python3
"""Generik TikTok teaser-slayd generatoru (brand.config.json ilə idarə olunur).

Hər bir biznes üçün: brand.config.json-u redaktə et, logo və (istəyə görə) app
ekran görüntülərini qoy, işə sal:

    python3 generate_slides.py --config brand.config.json \
        --out slides [--shot app-shots/01-home.png ...]

Kətan 9:16 (1080x1920). Slayd növləri:
  hook-*    — diqqətçəkən başlıq (2 rəng sxemi)
  feature-* — dəyər vədi (ağ kart)
  shot-*    — real app ekranı dik telefon çərçivəsində (tam görünür)
  cta-*     — güclü "İzlə" çağırışı
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
TEXT_MAX_W = 660
F_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def load_font(size, serif=False):
    return ImageFont.truetype(F_SERIF if serif else F_SANS, size)


class Kit:
    def __init__(self, cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            self.cfg = json.load(f)
        base_dir = os.path.dirname(os.path.abspath(cfg_path))
        p = self.cfg["palette"]
        self.CREAM = tuple(p["cream"]); self.CREAM2 = tuple(p["cream2"])
        self.YELLOW = tuple(p["yellow"]); self.ACCENT = tuple(p["accent"])
        self.ACCENT_DARK = tuple(p["accent_dark"]); self.DARK = tuple(p["dark"])
        self.BROWN = tuple(p["brown"]); self.WHITE = tuple(p["white"])
        self.logo_path = os.path.join(base_dir, self.cfg["brand"]["logo"])
        self.footer = self.cfg["brand"].get("footer", self.cfg["brand"]["domain"])
        self.follow_label = self.cfg.get("followLabel", "+ Follow")
        self._paw = None

    # ---- background ----
    def gradient(self, img, top, bottom):
        d = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H
            d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))

    def hexagons(self, img, color):
        def hx(cx, cy, r):
            return [(cx + r * math.cos(math.radians(60 * i - 30)),
                     cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for cx, cy, r in [(90, 360, 115), (1000, 300, 145), (70, 1600, 135), (1010, 1500, 125)]:
            d.polygon(hx(cx, cy, r), outline=color, width=9)
        img.paste(layer, (0, 0), layer)

    def base(self, scheme):
        img = Image.new("RGB", (W, H), self.CREAM)
        if scheme == "accent":
            self.gradient(img, self.YELLOW, self.ACCENT)
            self.hexagons(img, self.WHITE + (70,))
            return img, self.BROWN, self.DARK
        self.gradient(img, self.CREAM, self.CREAM2)
        self.hexagons(img, self.ACCENT + (45,))
        return img, self.ACCENT_DARK, self.DARK

    # ---- logo / paw ----
    def paw_sprite(self):
        if self._paw is None:
            logo = Image.open(self.logo_path).convert("RGBA")
            px = logo.load(); w, h = logo.size
            mask = Image.new("L", (w, h), 0); mp = mask.load()
            for y in range(h):
                for x in range(w):
                    r, g, b, a = px[x, y]
                    if a > 100 and r < 110 and g < 110 and b < 110:
                        mp[x, y] = a
            bbox = mask.getbbox()
            self._paw = mask.crop(bbox) if bbox else None
        return self._paw

    def paw(self, size, color):
        sprite = self.paw_sprite()
        if sprite is None:
            return Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ratio = min(size / sprite.width, size / sprite.height)
        m = sprite.resize((max(1, int(sprite.width * ratio)), max(1, int(sprite.height * ratio))))
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        layer.paste(Image.new("RGBA", m.size, tuple(color[:3]) + (255,)),
                    ((size - m.width) // 2, (size - m.height) // 2), m)
        return layer

    def logo_card(self, size, radius):
        logo = Image.open(self.logo_path).convert("RGBA")
        logo.thumbnail((int(size * 0.74), int(size * 0.74)))
        card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=self.WHITE)
        card.paste(logo, ((size - logo.width) // 2, (size - logo.height) // 2), logo)
        return card

    # ---- text ----
    @staticmethod
    def wrap(d, text, font, max_w=TEXT_MAX_W):
        words, lines, cur = text.split(), [], ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if d.textlength(t, font=font) > max_w and cur:
                lines.append(cur); cur = w_
            else:
                cur = t
        lines.append(cur)
        return lines

    @staticmethod
    def center(d, y, text, font, fill):
        d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)

    def cblock(self, d, y, text, font, fill, lh, max_w=TEXT_MAX_W):
        for ln in self.wrap(d, text, font, max_w):
            self.center(d, y, ln, font, fill); y += lh
        return y

    def follow_chip(self, img, y):
        d = ImageDraw.Draw(img)
        f = load_font(34)
        tw = d.textlength(self.follow_label, font=f)
        pw, ph = int(tw) + 100, 78
        x0 = (W - pw) // 2
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([x0, y + 4, x0 + pw, y + ph + 4], radius=ph // 2, fill=(40, 44, 60, 90))
        img.paste(Image.alpha_composite(img.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(8))).convert("RGB"), (0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0, y, x0 + pw, y + ph], radius=ph // 2, fill=self.DARK)
        d.text(((W - tw) / 2, y + 19), self.follow_label, font=f, fill=self.WHITE)
        self.center(d, y + ph + 14, self.footer, load_font(26), self.ACCENT_DARK)

    # ---- slides ----
    def hero(self, headline, sub, scheme):
        img, head_c, sub_c = self.base(scheme)
        d = ImageDraw.Draw(img)
        lc = self.logo_card(158, 36); img.paste(lc, ((W - 158) // 2, 470), lc)
        y = self.cblock(d, 760, headline, load_font(60, True), head_c, 80)
        p = self.paw(84, head_c); img.paste(p, ((W - 84) // 2, y + 40), p)
        y2 = self.cblock(d, y + 168, sub, load_font(36), sub_c, 50)
        self.follow_chip(img, y2 + 120)
        return img

    def feature(self, title, sub, scheme):
        img, head_c, sub_c = self.base(scheme)
        d = ImageDraw.Draw(img)
        lc = self.logo_card(140, 32); img.paste(lc, ((W - 140) // 2, 400), lc)
        cx0, cy0, cx1, cy1 = 200, 620, 880, 1300
        d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=50, fill=self.WHITE)
        p = self.paw(120, self.ACCENT); img.paste(p, ((W - 120) // 2, cy0 + 70), p)
        y = self.cblock(d, cy0 + 250, title, load_font(48), self.DARK, 60, 580)
        self.cblock(d, y + 24, sub, load_font(34), self.ACCENT_DARK, 44, 580)
        self.follow_chip(img, 1420)
        return img

    def shot(self, shot_path, caption, scheme):
        img, head_c, _ = self.base(scheme)
        d = ImageDraw.Draw(img)
        self.cblock(d, 210, caption, load_font(46, True), head_c, 58)
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
        fd.rounded_rectangle([15, 15, ph_w + 22, ph_h + 22], radius=52, fill=self.DARK)
        frame.paste(inner, (28, 28), mask)
        fd.rounded_rectangle([ph_w // 2 - 48, 21, ph_w // 2 + 66, 33], radius=7, fill=(20, 22, 30))
        img.paste(frame, ((W - frame.width) // 2, 350), frame)
        self.follow_chip(img, 350 + ph_h + 60)
        return img

    def cta(self, title, follow_line, scheme):
        img, head_c, sub_c = self.base(scheme)
        d = ImageDraw.Draw(img)
        lc = self.logo_card(190, 44); img.paste(lc, ((W - 190) // 2, 470), lc)
        y = self.cblock(d, 760, title, load_font(58, True), head_c, 78, 620)
        f_b = load_font(50)
        tw = d.textlength(self.follow_label, font=f_b)
        bw, bh = int(tw) + 150, 120
        bx, by = (W - bw) // 2, y + 46
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=self.DARK)
        d.text(((W - tw) / 2, by + 32), self.follow_label, font=f_b, fill=self.WHITE)
        y2 = self.cblock(d, by + bh + 36, follow_line, load_font(34), sub_c, 48, 640)
        self.center(d, y2 + 20, self.footer, load_font(30), self.ACCENT_DARK)
        return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="brand.config.json")
    ap.add_argument("--out", default="slides")
    ap.add_argument("--shot", action="append", default=[])
    args = ap.parse_args()

    kit = Kit(args.config)
    os.makedirs(args.out, exist_ok=True)
    cfg = kit.cfg
    made = []

    for i, (hl, sub) in enumerate(cfg["hooks"]):
        for scheme in ("accent", "cream"):
            n = f"hook-{i:02d}-{scheme}.png"
            kit.hero(hl, sub, scheme).save(os.path.join(args.out, n), optimize=True); made.append(n)

    for i, (t, s) in enumerate(cfg["features"]):
        n = f"feature-{i:02d}.png"
        kit.feature(t, s, "accent" if i % 2 == 0 else "cream").save(os.path.join(args.out, n), optimize=True); made.append(n)

    for i, (t, fl) in enumerate(cfg["ctas"]):
        n = f"cta-{i:02d}.png"
        kit.cta(t, fl, "accent" if i % 2 == 0 else "cream").save(os.path.join(args.out, n), optimize=True); made.append(n)

    shot_caps = cfg.get("shotCaptions", {})
    for si, shot in enumerate(args.shot):
        bn = os.path.splitext(os.path.basename(shot))[0]
        cap = shot_caps.get(bn, "")
        for oi, scheme in enumerate(("cream", "accent")):
            n = f"shot-{si:02d}-{oi}.png"
            kit.shot(shot, cap, scheme).save(os.path.join(args.out, n), optimize=True); made.append(n)

    for n in made:
        print(n)
    print(f"# {len(made)} slayd -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
