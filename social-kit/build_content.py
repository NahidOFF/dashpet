#!/usr/bin/env python3
"""brand.config.json + yaradılmış slaydlardan content.json qurur.

    python3 build_content.py --config brand.config.json --slides slides \
        --slide-base /social/slides/ --out content.json

content.json Worker tərəfindən oxunur (caption/hashtag hovuzu, cədvəl, slayd
adları). Slaydlar prefiksinə görə hovuzlara bölünür: hook-/feature-/shot-/cta-.
"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="brand.config.json")
    ap.add_argument("--slides", default="slides")
    ap.add_argument("--slide-base", default="/social/slides/")
    ap.add_argument("--out", default="content.json")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    pools = {"hooks": [], "features": [], "shots": [], "ctas": []}
    for fn in sorted(os.listdir(args.slides)):
        for key, pre in (("hooks", "hook-"), ("features", "feature-"),
                         ("shots", "shot-"), ("ctas", "cta-")):
            if fn.startswith(pre):
                pools[key].append(fn)

    sch = cfg["schedule"]
    content = {
        "version": 1,
        "slideBase": args.slide_base,
        "slides": pools,
        "slidesPerPost": sch.get("slidesPerPost", {"min": 6, "max": 8}),
        "postTimesLocal": sch["postTimesLocal"],
        "utcOffsetHours": sch.get("utcOffsetHours", 0),
        "accountStaggerMinutes": sch.get("accountStaggerMinutes", 7),
        "timezone": sch.get("timezone", "UTC"),
        "captions": cfg["captions"],
        "hashtagSets": cfg["hashtagSets"],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    print("content.json:", {k: len(v) for k, v in pools.items()},
          "| captions:", len(content["captions"]))


if __name__ == "__main__":
    main()
