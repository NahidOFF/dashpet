# TikTok slideshow avtomatlaşdırması — quraşdırma bələdçisi (Claude Code üçün)

> Bu qovluğu (`social-kit/`) istənilən biznesin rep-una at və Claude Code-a de:
> **"social-kit/SETUP.md-ə əməl edib bu biznes üçün TikTok avtomatlaşdırmasını qur."**
> Claude Code aşağıdakı addımları icra edəcək.

## Sistem nədir

Gündə 3 dəfə (cədvələ görə) hər qoşulmuş TikTok hesabına branded photo-slideshow
(6-8 slayd) postlayan tam-pulsuz sistem:

```
Cloudflare Cron (gündə 1 dəfə)
  └─ <domain>/social/content.json   (slayd hovuzu, caption, cədvəl)
  └─ Zernio GET /v1/accounts         (bütün TikTok hesabları avtomatik)
  └─ Zernio POST /v1/posts           (hər hesaba N post, hesab başına sürüşmə)
```

- **Slaydlar** deterministik şəkil şablonları (AI deyil): brend rəngləri, loqo,
  başlıqlar + istəyə görə app-ın **real daxili ekranları** dik telefon çərçivəsində.
- **Xərc:** slaydlar $0 (Cloudflare statik) + Zernio (ilk 2 hesab pulsuz, sonra
  ~$6/hesab) + Worker $0. Bir Cloudflare hesabı bütün bizneslərə xidmət edə bilər.

## İstifadəçidən lazım olanlar (Claude Code soruşsun)

1. **Biznesin domeni** (slaydlar bu saytdan veriləcək; Cloudflare Pages/Workers statik sayt).
2. **Loqo** faylı (PNG, mərkəzində tünd işarə/simvol varsa "paw" kimi çıxarılır).
3. **Zernio API açar(lar)ı** — zernio.com → API. Hər hesab 2 TikTok bağlayır (pulsuz).
4. **Cloudflare API token** — dash.cloudflare.com/profile/api-tokens → "Edit Cloudflare Workers" şablonu.
5. **RUN_TOKEN** — `openssl rand -hex 24` ilə yaradılır.
6. (İstəyə görə) app-ın **daxili ekran görüntüləri** və ya lokal işlətmə imkanı.

> Gizli açarlar repoya YAZILMIR — GitHub Actions **Secrets**-ə qoyulur
> (`CLOUDFLARE_API_TOKEN`, `ZERNIO_API_KEYS`, `RUN_TOKEN`).

## Addımlar (Claude Code icra edir)

### 1. Konfiqurasiya
- `brand.config.example.json`-u `brand.config.json` kimi kopyala və doldur:
  brend adı/domeni, `footer` (məs. `"marka.com · tezliklə"` və ya sadəcə domen),
  `palette` (rənglər), `hooks`/`features`/`ctas`/`captions`/`hashtagSets`/`shotCaptions`.
  Mətnləri biznesin dilinə və məhsuluna uyğunlaşdır.
- Loqonu bu qovluğa qoy və `brand.config.json`-da `brand.logo` adını ver.

### 2. (İstəyə görə) real app ekranları
- App-ı lokal işlət (frontend + backend). Backend SQLite ilə işləyirsə, demo
  data seed et, test istifadəçi/məzmun yarat.
- `capture_app_shots.py` ilə daxili ekranları çək (`routes.json`-u həmin SPA-nın
  naviqasiya funksiyalarına uyğun düzəlt). Ekranları `app-shots/` qovluğuna yığ.
- Yoxsa bu addımı ötür — sistem yalnız branded slaydlarla da işləyir.

### 3. Slaydları və content.json-u yarat
```bash
pip install pillow
python3 generate_slides.py --config brand.config.json --out ../social/slides \
    [--shot app-shots/01-home.png --shot app-shots/03-cart.png ...]
python3 build_content.py --config brand.config.json --slides ../social/slides \
    --slide-base /social/slides/ --out ../social/content.json
```
- Nəticəni gözdən keçir: slaydlar 1080×1920 (9:16), oxunaqlı, brendli.

### 4. Saytı və Worker-i yerləşdir
- `../social/` (slides + content.json) biznesin statik saytına daxil olsun.
- `worker.js` + `wrangler.example.jsonc`-i `social-worker/` kimi qur; `<NAME>`,
  `<CLOUDFLARE_ACCOUNT_ID>`, `SITE_BASE`, cron vaxtını doldur.
- `deploy.example.yml`-i `.github/workflows/deploy-social.yml` kimi qoy
  (`<CLOUDFLARE_ACCOUNT_ID>` doldur). `post-once.mjs`-i `social-worker/`-ə əlavə et.

### 5. Secrets və deploy
- GitHub → Settings → Secrets and variables → Actions:
  `CLOUDFLARE_API_TOKEN`, `ZERNIO_API_KEYS`, `RUN_TOKEN`.
- Deploy workflow-u işə sal (push və ya workflow_dispatch). Sayt + Worker qalxır.

### 6. Test
- Quru sınaq: `https://<worker>.workers.dev/run?dry=1` → günün planını göstərir (heç nə postlamır).
- Real test: hər hesaba 1 post — `post-once.mjs` (Actions-da `workflow_dispatch` ilə).
- Cron artıq hər gün öz-özünə işləyəcək.

## Vacib qeydlər

- **9:16, tam görünsün.** Slaydlar 1080×1920; şəkil slaydlarında telefon çərçivəsi
  bir az aşağı yerləşir ki, üstü TikTok axtarış zolağından təmiz qalsın.
- **Teaser vs canlı.** Sayt hələ açılmayıbsa, mesajları "tezliklə / izlə" üslubunda
  saxla (`brand.config.json`-da). Açılandan sonra "indi sifariş et"-ə keçir.
- **Follow strategiyası.** Hər slaydın altında "+ İzlə" çipi; son (CTA) slaydda güclü
  follow çağırışı. Caption-larda da follow səbəbi olsun ("izlə ki, ... qaçırma").
- **Zernio dublikat qaydası.** Eyni məzmun 24 saatda təkrar postlana bilməz (409).
  `post-once.mjs` hər dəfə fərqli məzmun seçir; cron isə gün+slot+hesaba görə unikal.
- **Çoxlu hesab.** Hər Zernio açarı 2 TikTok (pulsuz). Daha çox hesab üçün əlavə
  Zernio hesabları aç, açarları vergüllə `ZERNIO_API_KEYS`-ə əlavə et — Worker
  hər gün siyahını təzədən çəkir, yeni hesab avtomatik cədvələ düşür.
- **Məzmunu yeniləmək.** Slaydlar/caption üçün `brand.config.json`-u dəyiş və 3-cü
  addımı təkrar işlət; sayt deploy olan kimi qüvvəyə minir (Worker-ə toxunmadan).

## Fayllar
- `brand.config.example.json` — per-biznes konfiqurasiya şablonu
- `generate_slides.py` — slayd generatoru (config-driven, 9:16)
- `build_content.py` — content.json qurucusu
- `worker.js` + `wrangler.example.jsonc` — Cloudflare planlayıcı
- `post-once.mjs` — bir dəfəlik test posteri
- `deploy.example.yml` — GitHub Actions deploy
- `capture_app_shots.py` — app daxili ekranlarını çəkən Playwright köməkçisi
