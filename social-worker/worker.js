/**
 * Petekh sosial media avtomatlaşdırması — Cloudflare Worker.
 *
 * Hər gün bir dəfə (cron) işə düşür, həmin günün bütün TikTok slideshow
 * postlarını Zernio API vasitəsilə planlaşdırır (hər hesaba 3 post,
 * hesablar arasında vaxt sürüşməsi ilə).
 *
 * Secrets (wrangler secret put ...):
 *   ZERNIO_API_KEYS  — vergüllə ayrılmış Zernio açarları (sk_...,sk_...)
 *   RUN_TOKEN        — /run endpointini əl ilə işə salmaq üçün gizli token
 * Vars (wrangler.jsonc):
 *   SITE_BASE — slaydların və content.json-un verildiyi sayt (https://petekh.com)
 *   DRY_RUN   — "1" olduqda Zernio-ya heç nə göndərilmir, yalnız loglanır
 */

const ZERNIO_BASE = "https://zernio.com/api";
const BAKU_UTC_OFFSET_H = 4; // Asia/Baku, DST yoxdur

// ---------- deterministik seed RNG ----------
function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick(rng, arr) {
  return arr[Math.floor(rng() * arr.length)];
}

function shuffle(rng, arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---------- vaxt hesablamaları ----------
function bakuToday() {
  const now = new Date(Date.now() + BAKU_UTC_OFFSET_H * 3600 * 1000);
  return now.toISOString().slice(0, 10); // YYYY-MM-DD (Bakı günü)
}

function bakuTimeToUtcIso(dateStr, hhmm, extraMinutes) {
  const [hh, mm] = hhmm.split(":").map(Number);
  const utcMs =
    Date.parse(`${dateStr}T00:00:00Z`) +
    ((hh - BAKU_UTC_OFFSET_H) * 60 + mm + extraMinutes) * 60 * 1000;
  return new Date(utcMs).toISOString().replace(/\.\d{3}Z$/, "Z");
}

// ---------- Zernio API ----------
async function zernioGetTiktokAccounts(key) {
  const res = await fetch(`${ZERNIO_BASE}/v1/accounts`, {
    headers: { Authorization: `Bearer ${key}` },
  });
  if (!res.ok) {
    throw new Error(`accounts ${res.status}: ${(await res.text()).slice(0, 200)}`);
  }
  const data = await res.json();
  return (data.accounts || []).filter(
    (a) => a.platform === "tiktok" && a.isActive && !a.needsReconnection
  );
}

async function zernioCreatePost(key, body, requestId) {
  const res = await fetch(`${ZERNIO_BASE}/v1/posts`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      "x-request-id": requestId,
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`post ${res.status}: ${text.slice(0, 300)}`);
  }
  return JSON.parse(text);
}

// ---------- post qurulması ----------
function buildPost(content, siteBase, dateStr, slotIdx, account, globalIdx) {
  const rng = mulberry32(fnv1a(`${dateStr}|${slotIdx}|${account._id}`));
  const s = content.slides;
  const base = `${siteBase}${content.slideBase}`;

  const nCfg = content.slidesPerPost || { min: 6, max: 8 };
  const total = nCfg.min + Math.floor(rng() * (nCfg.max - nCfg.min + 1));

  const middlePool = shuffle(rng, [...s.features, ...s.shots]);
  const slideFiles = [
    pick(rng, s.hooks),
    ...middlePool.slice(0, total - 2),
    pick(rng, s.ctas),
  ];

  const caption = pick(rng, content.captions);
  const hashtags = pick(rng, content.hashtagSets);
  const scheduledFor = bakuTimeToUtcIso(
    dateStr,
    content.postTimesBaku[slotIdx],
    globalIdx * (content.accountStaggerMinutes || 7)
  );

  return {
    scheduledFor,
    body: {
      content: caption,
      hashtags,
      mediaItems: slideFiles.map((f) => ({
        type: "image",
        url: `${base}${f}`,
        mimeType: "image/png",
      })),
      platforms: [{ platform: "tiktok", accountId: account._id }],
      scheduledFor,
      timezone: content.timezone || "Asia/Baku",
      tiktokSettings: {
        mediaType: "photo",
        privacyLevel: "PUBLIC_TO_EVERYONE",
        allowComment: true,
        autoAddMusic: true,
        photoCoverIndex: 0,
      },
    },
  };
}

// ---------- əsas axın ----------
async function runDay(env, { dry }) {
  const siteBase = (env.SITE_BASE || "https://petekh.com").replace(/\/$/, "");
  const isDry = dry || env.DRY_RUN === "1";
  const dateStr = bakuToday();

  const res = await fetch(`${siteBase}/social/content.json`, {
    headers: { "cache-control": "no-cache" },
  });
  if (!res.ok) throw new Error(`content.json ${res.status}`);
  const content = await res.json();

  const keys = (env.ZERNIO_API_KEYS || "")
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);

  const summary = { date: dateStr, dry: isDry, scheduled: [], errors: [] };

  let accountsByKey;
  if (keys.length === 0) {
    if (!isDry) throw new Error("ZERNIO_API_KEYS secret qurulmayıb");
    accountsByKey = [["mock-key", [{ _id: "mock-acc-1", username: "demo1" }, { _id: "mock-acc-2", username: "demo2" }]]];
  } else {
    accountsByKey = [];
    for (const key of keys) {
      try {
        accountsByKey.push([key, await zernioGetTiktokAccounts(key)]);
      } catch (e) {
        summary.errors.push(`accounts(${key.slice(0, 8)}…): ${e.message}`);
      }
    }
  }

  let globalIdx = 0;
  for (const [key, accounts] of accountsByKey) {
    for (const account of accounts) {
      for (let slot = 0; slot < (content.postTimesBaku || []).length; slot++) {
        const post = buildPost(content, siteBase, dateStr, slot, account, globalIdx);
        const requestId = `petekh-${dateStr}-s${slot}-${account._id}`;
        const label = `@${account.username || account._id} slot${slot} ${post.scheduledFor} (${post.body.mediaItems.length} slayd)`;
        if (isDry) {
          summary.scheduled.push(`[DRY] ${label}`);
        } else {
          try {
            await zernioCreatePost(key, post.body, requestId);
            summary.scheduled.push(label);
          } catch (e) {
            summary.errors.push(`${label}: ${e.message}`);
          }
        }
      }
      globalIdx++;
    }
  }

  console.log(JSON.stringify(summary));
  return summary;
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runDay(env, { dry: false }));
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/run") {
      return new Response("petekh-social worker. GET /run?dry=1", { status: 404 });
    }
    const dry = url.searchParams.get("dry") === "1";
    const token = url.searchParams.get("token") || "";
    if (!dry && (!env.RUN_TOKEN || token !== env.RUN_TOKEN)) {
      return new Response("token tələb olunur (yalnız dry=1 tokensiz işləyir)", { status: 403 });
    }
    try {
      const summary = await runDay(env, { dry });
      return Response.json(summary);
    } catch (e) {
      return Response.json({ error: e.message }, { status: 500 });
    }
  },
};
