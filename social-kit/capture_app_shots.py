#!/usr/bin/env python3
"""App-ın daxili ekranlarını Playwright ilə çəkir (real-ekran slaydları üçün).

Frontend-i lokal işlət (backend + sayt), sonra:
    python3 capture_app_shots.py --url http://127.0.0.1:8080/index.html \
        --token <AUTH_TOKEN> --out app-shots --routes routes.json

routes.json nümunəsi (SPA-nın naviqasiya funksiyasına uyğunlaşdır):
    {
      "tokenKey": "token",
      "nav": "go",                 // pəncərədəki naviqasiya funksiyası: go('home')
      "screens": [
        {"name": "01-home",   "call": "go('home')"},
        {"name": "02-product","call": "openProduct(S.products[0].id)"},
        {"name": "03-cart",   "call": "(S.products||[]).slice(0,3).forEach(p=>addCart(p.id)); go('card')"}
      ]
    }

Qeyd: hər SPA fərqlidir — screens[].call sətirlərini həmin app-ın funksiya
adlarına görə düzəlt. Naviqasiya JS-i tapmaq üçün index.html-də `go(`, `render`,
`S.view=` axtar.
"""
import argparse
import glob
import json
import os
import time

from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--token", default="")
    ap.add_argument("--routes", required=True)
    ap.add_argument("--out", default="app-shots")
    ap.add_argument("--width", type=int, default=390)
    ap.add_argument("--height", type=int, default=844)
    args = ap.parse_args()

    with open(args.routes, encoding="utf-8") as f:
        routes = json.load(f)
    os.makedirs(args.out, exist_ok=True)

    exe = None
    for c in glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"):
        exe = c
        break

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=exe,
                                    args=["--disable-web-security", "--no-sandbox", "--disable-gpu", "--hide-scrollbars"])
        ctx = browser.new_context(viewport={"width": args.width, "height": args.height}, device_scale_factor=2)
        if args.token:
            key = routes.get("tokenKey", "token")
            ctx.add_init_script(f"localStorage.setItem('{key}', '{args.token}');")
        page = ctx.new_page()
        page.goto(args.url, wait_until="networkidle")
        time.sleep(3)
        for sc in routes["screens"]:
            try:
                page.evaluate(sc["call"])
            except Exception as e:
                print("skip", sc["name"], e)
                continue
            time.sleep(1.5)
            page.screenshot(path=os.path.join(args.out, sc["name"] + ".png"))
            print("shot", sc["name"])
        browser.close()


if __name__ == "__main__":
    main()
