// Bir dəfəlik test: hər qoşulmuş TikTok hesabına 1 slideshow postu (dərhal dərc).
// Gündəlik sistemə toxunmur — yalnız əl ilə (workflow_dispatch) işə düşür.
const ZERNIO = "https://zernio.com/api";
const SITE = "https://petekh.com";

function fnv(s) { let h = 0x811c9dc5; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; }
function rng32(a) { return function () { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const pick = (r, arr) => arr[Math.floor(r() * arr.length)];
const shuffle = (r, arr) => { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

const content = await (await fetch(`${SITE}/social/content.json`)).json();
const keys = (process.env.ZERNIO_API_KEYS || "").split(",").map(k => k.trim()).filter(Boolean);
if (!keys.length) { console.error("ZERNIO_API_KEYS secret-i yoxdur"); process.exit(1); }

let fails = 0;
for (const key of keys) {
  const res = await fetch(`${ZERNIO}/v1/accounts`, { headers: { Authorization: `Bearer ${key}` } });
  if (!res.ok) { console.log(`XETA accounts: ${res.status}`); fails++; continue; }
  const accounts = (await res.json()).accounts.filter(a => a.platform === "tiktok" && a.isActive && !a.needsReconnection);
  for (const acc of accounts) {
    const r = rng32(fnv(`${Date.now()}|test|${Math.random()}|${acc._id}`));
    const s = content.slides, base = `${SITE}${content.slideBase}`;
    const files = [pick(r, s.hooks), ...shuffle(r, [...s.features, ...s.shots]).slice(0, 4), pick(r, s.ctas)];
    const body = {
      content: pick(r, content.captions),
      hashtags: pick(r, content.hashtagSets),
      mediaItems: files.map(f => ({ type: "image", url: `${base}${f}`, mimeType: "image/png" })),
      platforms: [{ platform: "tiktok", accountId: acc._id }],
      publishNow: true,
      tiktokSettings: { mediaType: "photo", privacyLevel: "PUBLIC_TO_EVERYONE", allowComment: true, autoAddMusic: true, photoCoverIndex: 0 },
    };
    const pr = await fetch(`${ZERNIO}/v1/posts`, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", "x-request-id": `petekh-test-${Date.now()}-${acc._id}` },
      body: JSON.stringify(body),
    });
    const txt = await pr.text();
    if (pr.ok) {
      console.log(`OK  @${acc.username || acc._id}: ${files.length} slaydlıq post göndərildi`);
      console.log(`    slaydlar: ${files.join(", ")}`);
    } else {
      console.log(`XETA @${acc.username || acc._id}: ${pr.status} ${txt.slice(0, 300)}`);
      fails++;
    }
  }
}
process.exit(fails ? 1 : 0);
