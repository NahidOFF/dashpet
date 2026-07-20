/**
 * Generik sosial-media avtomatlaşdırması — Cloudflare Worker.
 *
 * Gündə bir dəfə cron ilə işə düşür, həmin günün bütün TikTok slideshow
 * postlarını Zernio API ilə planlaşdırır (hər hesaba postTimesLocal qədər post,
 * hesablar arası vaxt sürüşməsi ilə).
 *
 * Secrets:  ZERNIO_API_KEYS (vergüllə: sk_...,sk_...)  |  RUN_TOKEN
 * Vars:     SITE_BASE (content.json və slaydların verildiyi sayt)  |  DRY_RUN ("0"/"1")
 */
const ZERNIO_BASE = "https://zernio.com/api";

function fnv1a(s) { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; }
function mulberry32(a) { return function () { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const pick = (r, a) => a[Math.floor(r() * a.length)];
const shuffle = (r, a) => { const b = a.slice(); for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };

function localToday(offsetH) {
  return new Date(Date.now() + offsetH * 3600 * 1000).toISOString().slice(0, 10);
}
function localToUtcIso(dateStr, hhmm, offsetH, extraMin) {
  const [hh, mm] = hhmm.split(":").map(Number);
  const ms = Date.parse(`${dateStr}T00:00:00Z`) + ((hh - offsetH) * 60 + mm + extraMin) * 60000;
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function getTiktokAccounts(key) {
  const res = await fetch(`${ZERNIO_BASE}/v1/accounts`, { headers: { Authorization: `Bearer ${key}` } });
  if (!res.ok) throw new Error(`accounts ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return (await res.json()).accounts.filter((a) => a.platform === "tiktok" && a.isActive && !a.needsReconnection);
}

async function createPost(key, body, requestId) {
  const res = await fetch(`${ZERNIO_BASE}/v1/posts`, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", "x-request-id": requestId },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`post ${res.status}: ${text.slice(0, 300)}`);
  return JSON.parse(text);
}

function buildPost(content, siteBase, dateStr, slotIdx, account, globalIdx) {
  const rng = mulberry32(fnv1a(`${dateStr}|${slotIdx}|${account._id}`));
  const s = content.slides, base = `${siteBase}${content.slideBase}`;
  const n = content.slidesPerPost || { min: 6, max: 8 };
  const total = n.min + Math.floor(rng() * (n.max - n.min + 1));
  const middle = shuffle(rng, [...s.features, ...(s.shots || [])]);
  const files = [pick(rng, s.hooks), ...middle.slice(0, total - 2), pick(rng, s.ctas)];
  const scheduledFor = localToUtcIso(dateStr, content.postTimesLocal[slotIdx],
    content.utcOffsetHours || 0, globalIdx * (content.accountStaggerMinutes || 7));
  return {
    scheduledFor,
    body: {
      content: pick(rng, content.captions),
      hashtags: pick(rng, content.hashtagSets),
      mediaItems: files.map((f) => ({ type: "image", url: `${base}${f}`, mimeType: "image/png" })),
      platforms: [{ platform: "tiktok", accountId: account._id }],
      scheduledFor,
      timezone: content.timezone || "UTC",
      tiktokSettings: { mediaType: "photo", privacyLevel: "PUBLIC_TO_EVERYONE", allowComment: true, autoAddMusic: true, photoCoverIndex: 0 },
    },
  };
}

async function runDay(env, { dry }) {
  const siteBase = (env.SITE_BASE || "").replace(/\/$/, "");
  const isDry = dry || env.DRY_RUN === "1";
  const content = await (await fetch(`${siteBase}/social/content.json`, { headers: { "cache-control": "no-cache" } })).json();
  const dateStr = localToday(content.utcOffsetHours || 0);
  const keys = (env.ZERNIO_API_KEYS || "").split(",").map((k) => k.trim()).filter(Boolean);
  const summary = { date: dateStr, dry: isDry, scheduled: [], errors: [] };

  let byKey = [];
  if (!keys.length) {
    if (!isDry) throw new Error("ZERNIO_API_KEYS secret qurulmayıb");
    byKey = [["mock", [{ _id: "mock1", username: "demo1" }, { _id: "mock2", username: "demo2" }]]];
  } else {
    for (const key of keys) {
      try { byKey.push([key, await getTiktokAccounts(key)]); }
      catch (e) { summary.errors.push(`accounts(${key.slice(0, 8)}…): ${e.message}`); }
    }
  }

  let gi = 0;
  for (const [key, accounts] of byKey) {
    for (const account of accounts) {
      for (let slot = 0; slot < (content.postTimesLocal || []).length; slot++) {
        const post = buildPost(content, siteBase, dateStr, slot, account, gi);
        const label = `@${account.username || account._id} slot${slot} ${post.scheduledFor} (${post.body.mediaItems.length})`;
        if (isDry) { summary.scheduled.push(`[DRY] ${label}`); continue; }
        try { await createPost(key, post.body, `once-${dateStr}-s${slot}-${account._id}`); summary.scheduled.push(label); }
        catch (e) { summary.errors.push(`${label}: ${e.message}`); }
      }
      gi++;
    }
  }
  console.log(JSON.stringify(summary));
  return summary;
}

export default {
  async scheduled(event, env, ctx) { ctx.waitUntil(runDay(env, { dry: false })); },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/run") return new Response("social worker. GET /run?dry=1", { status: 404 });
    const dry = url.searchParams.get("dry") === "1";
    const token = url.searchParams.get("token") || "";
    if (!dry && (!env.RUN_TOKEN || token !== env.RUN_TOKEN)) return new Response("token tələb olunur", { status: 403 });
    try { return Response.json(await runDay(env, { dry })); }
    catch (e) { return Response.json({ error: e.message }, { status: 500 }); }
  },
};
