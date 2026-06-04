const $ = (id) => document.getElementById(id);

function buildPost() {
  const tags = $("tags").value.split(",").map(s => s.trim()).filter(Boolean);
  const media = $("media").value.split("\n").map(s => s.trim()).filter(Boolean)
    .map(path => ({
      path,
      type: /\.(mp4|mov|avi|mkv|webm)$/i.test(path) ? "video" : "image",
    }));
  return { title: $("title").value, body: $("body").value, tags, media, overrides: {} };
}

function selectedPlatforms() {
  return [...document.querySelectorAll(".pf:checked")].map(c => c.value);
}

async function loadPlatforms() {
  const res = await fetch("/api/platforms").then(r => r.json());
  $("platforms").innerHTML = res.map(p => `
    <label class="pf-row">
      <input class="pf" type="checkbox" value="${p.platform}" checked>
      ${p.platform}
      <span class="${p.ready ? "ok" : "warn"}">
        ${p.ready ? "就绪" : "未连接/未登录"}
      </span>
    </label>`).join("");
}

function renderRows(rows) {
  $("results").innerHTML = rows.map(r => `
    <div class="result ${r.status}">
      <strong>${r.platform}</strong>
      <span>${r.status}</span>
      ${r.url ? `<a href="${r.url}" target="_blank">查看</a>` : ""}
      <span class="msg">${r.message || ""}</span>
    </div>`).join("");
}

$("validate").onclick = async () => {
  const out = await fetch("/api/validate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildPost()),
  }).then(r => r.json());
  renderRows(Object.entries(out).map(([platform, v]) =>
    ({ platform, status: v.status, message: v.message })));
};

$("publish").onclick = async () => {
  $("results").innerHTML = "发布中…";
  const out = await fetch("/api/publish", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ post: buildPost(), platforms: selectedPlatforms() }),
  }).then(r => r.json());
  renderRows(out);
};

$("save_x").onclick = async () => {
  $("x_save_msg").textContent = "保存中…";
  const res = await fetch("/api/credentials/x", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: $("x_api_key").value.trim(),
      api_secret: $("x_api_secret").value.trim(),
      access_token: $("x_access_token").value.trim(),
      access_token_secret: $("x_access_token_secret").value.trim(),
    }),
  }).then(r => r.json());
  $("x_save_msg").textContent = res.ready ? "已保存,X 就绪" : "已保存,但凭证不完整";
  loadPlatforms();
};

$("save_tk").onclick = async () => {
  $("tk_save_msg").textContent = "保存中…";
  const res = await fetch("/api/credentials/tiktok", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      access_token: $("tk_access_token").value.trim(),
      refresh_token: $("tk_refresh_token").value.trim(),
      client_key: $("tk_client_key").value.trim(),
      client_secret: $("tk_client_secret").value.trim(),
    }),
  }).then(r => r.json());
  $("tk_save_msg").textContent = res.ready ? "已保存,TikTok 就绪" : "已保存,但缺 access_token";
  loadPlatforms();
};

$("auth_yt").onclick = async () => {
  $("yt_auth_msg").textContent = "正在打开浏览器授权…";
  const res = await fetch("/api/youtube/authorize", { method: "POST" })
    .then(r => r.json());
  $("yt_auth_msg").textContent = res.ok ? "YouTube 已授权" : (res.message || "授权失败");
  loadPlatforms();
};

loadPlatforms();
