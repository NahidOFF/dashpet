# Petekh Sosial Media Avtomatlaşdırması

Gündə 3 dəfə, hər qoşulmuş TikTok hesabına branded photo-slideshow (6-8 slayd)
postlayan sistem. Tam pulsuz infrastruktur: Cloudflare Worker (cron) + statik
slaydlar (bu sayt) + Zernio API (postlama).

## Necə işləyir

```
Cloudflare Cron (hər gün 08:30 Bakı)
  └─> petekh.com/social/content.json  (slayd hovuzu, captionlar, cədvəl)
  └─> Zernio GET /v1/accounts          (bütün TikTok hesabları avtomatik tapılır)
  └─> Zernio POST /v1/posts            (hər hesaba 3 post: 09:30, 13:45, 19:20
                                        + hesab başına 7 dəq sürüşmə)
```

Hər postun slayd kombinasiyası, caption və hashtag-ləri tarix+hesab əsasında
deterministik seçilir — eyni gün iki hesab eyni posту paylaşmır.

## Quraşdırma (bir dəfəlik)

1. Repo kökündə slaydlar artıq var (`social/slides/`). Sayt deploy olunanda
   avtomatik veriləcək.
2. Worker-i deploy et:
   ```
   cd social-worker
   npx wrangler deploy
   npx wrangler secret put ZERNIO_API_KEYS   # sk_...,sk_...,sk_... (vergüllə)
   npx wrangler secret put RUN_TOKEN         # istənilən uzun təsadüfi sətir
   ```
   (Alternativ: Cloudflare dashboard → Workers → petekh-social → Settings →
   Variables and Secrets bölməsindən də əlavə etmək olar.)

## Test

- Quru sınaq (heç nə postlanmır): `https://<worker-url>/run?dry=1`
- Əl ilə real işə salma: `https://<worker-url>/run?token=<RUN_TOKEN>`
- Lokal: `npx wrangler dev --var DRY_RUN:1` → `curl localhost:8787/run?dry=1`

## Kontenti yeniləmək

- **Slaydlar**: `python3 social/generate_slides.py --shot <ekran-görüntüsü>` —
  başlıqlar/mətnlər skriptin içindəki siyahılardadır.
- **Caption/hashtag**: `social/content.json` faylını redaktə et.
- **Post vaxtları**: `content.json` → `postTimesBaku`.
- Dəyişikliklər sayt deploy olunan kimi qüvvəyə minir (Worker-ə toxunmaq lazım deyil).

## Yeni TikTok hesabı əlavə etmək

Zernio-da hesabı qoş — vəssalam. Worker hər gün hesab siyahısını təzədən
çəkir, yeni hesab avtomatik cədvələ düşür. Yeni Zernio hesabı (yeni açar)
əlavə olunursa, `ZERNIO_API_KEYS` secret-inə vergüllə əlavə edin.
