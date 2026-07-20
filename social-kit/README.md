# social-kit — TikTok slideshow avtomatlaşdırma dəsti

Bir biznes üçün gündəlik, brendli TikTok photo-slideshow postlarını avtomatlaşdırır.
Tam quraşdırma addımları: **SETUP.md**.

Sürətli: `brand.config.example.json` → `brand.config.json` (doldur) → loqonu qoy →
`generate_slides.py` + `build_content.py` işlət → `worker.js`-i Cloudflare-ə deploy et →
Zernio açarlarını Secrets-ə qoy. Detallar SETUP.md-dədir.
