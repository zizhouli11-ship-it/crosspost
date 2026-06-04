# 跨平台内容发布工具 — 设计文档

- **日期**: 2026-06-04
- **定位**: 私人工具(单用户,自己用,不做多租户/不做商业化)
- **目标**: 一份产品内容(图文 / 视频) → 自动适配各平台格式 → 一键发布到多个平台,并在本地网页面板看到每个平台的实时发布结果。

---

## 1. 范围

### 1.1 目标平台(全量愿景)
X / LinkedIn / YouTube / 小红书 / 视频号 / B站 / 抖音 / TikTok

按发布机制分两类:

| 类型 | 平台 | 发布方式 |
|---|---|---|
| 有官方 API | X、LinkedIn、YouTube、TikTok、B站(半开放) | 调官方接口 |
| 无开放发布 API | 小红书、视频号、抖音 | 浏览器自动化(CDP) |

### 1.2 MVP 平台切片(第一版只做 3 个)

| 平台 | 引擎 | 内容类型 | 选它的原因 |
|---|---|---|---|
| 小红书 | Browser (CDP) | 图文 + 视频 | 复用现有 `post-to-xhs` 脚本,验证浏览器引擎 |
| X (Twitter) | API | 图文 | 验证 API 引擎 + 图文链路 |
| YouTube | API | 视频 | 验证 API 引擎 + 视频链路 |

这 3 个覆盖「两种引擎 × 两种内容形态」。骨架一次到位后,其余平台为增量:
- 抖音 / 视频号 → 照 `BrowserPublisher` 加
- LinkedIn / TikTok / B站 → 照 `ApiPublisher` 加

### 1.3 非目标(YAGNI)
- 不做多用户 / 登录系统 / 计费
- 不做内容生成(文案/图/视频由用户自己准备好)
- 不做定时发布(第一版只做"立即发",定时留作后续)
- 不做数据回收分析(阅读量/互动统计留作后续)

---

## 2. 技术栈

- **语言**: Python(与现有 `post-to-xhs` 同栈,直接复用)
- **后端**: FastAPI(本地服务,起网页面板 + 编排发布)
- **浏览器引擎**: CDP over websockets(沿用 `post-to-xhs` 模式,依赖 `requests` + `websockets`,不引入 Playwright)
- **前端**: 单页本地网页(原生 HTML/JS 即可,无需重框架),由 FastAPI 提供静态文件 + JSON API
- **运行环境**: Windows 11,本地运行,浏览器打开 `localhost`

---

## 3. 架构

```
┌─────────────────────────────────────────┐
│  本地网页面板 (localhost)                  │
│  填内容 → 选平台 → 发布 → 看每平台结果      │
└───────────────────┬─────────────────────┘
                    │ HTTP (JSON)
┌───────────────────▼─────────────────────┐
│  FastAPI 后端                             │
│  ┌─────────────────────────────────────┐ │
│  │ Orchestrator 编排器                  │ │
│  │  接收 Post → 逐平台调用 Publisher     │ │
│  │  每平台独立 try,互不阻塞,汇总结果    │ │
│  └──────────────┬──────────────────────┘ │
│       ┌─────────┴──────────┐             │
│  ┌────▼─────┐         ┌────▼──────┐       │
│  │ Adapter  │         │Credential │       │
│  │ 适配层    │         │ Store     │       │
│  └────┬─────┘         └───────────┘       │
│  ┌────▼──────────────────────────────┐    │
│  │ Publisher 插件 (统一接口)          │    │
│  │  publish(post) -> Result          │    │
│  │  BrowserPublisher | ApiPublisher  │    │
│  └───────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

### 3.1 组件职责

- **网页面板**: 收集内容、选平台、触发发布、展示结果。纯展示 + 交互,无业务逻辑。
- **Orchestrator(编排器)**: 接收一份 `Post`,对选中的每个平台依次/并发调用其 Publisher,逐平台独立捕获异常,汇总成结果列表返回。一个平台失败不影响其他平台。
- **Adapter(适配层)**: 把通用 `Post` 翻译成各平台所需字段;发布前做校验(字数/媒体数量/类型),不匹配的提前标记。
- **Credential Store(凭证存储)**: 管理 API token 与浏览器登录态状态查询。token 存本地文件(不进 git)。
- **Publisher(发布插件)**: 统一接口 `publish(post) -> Result`,分两个基类:
  - `BrowserPublisher`: 走 CDP,驱动已登录的 Chrome(小红书/抖音/视频号)
  - `ApiPublisher`: 走官方 API(X/YouTube/LinkedIn/TikTok/B站)

### 3.2 加平台 = 加一个文件

新平台只需新增一个 Publisher 子类 + 一份适配规则,注册到平台表即可,不改动编排器/前端骨架。

---

## 4. 数据模型

```python
Post:
  title:     str                 # 标题(部分平台用;X 无标题概念)
  body:      str                 # 正文 / 文案
  media:     list[Media]         # 图片或视频
  tags:      list[str]           # 话题标签,如 ["AI", "出海"]
  overrides: dict[str, dict]     # 平台级覆盖: platform -> {title?, body?, tags?}

Media:
  path: str                      # 本地文件路径
  type: "image" | "video"

Result:                          # 每平台发布结果
  platform: str
  status:   "success" | "failed" | "skipped" | "needs_login"
  url:      str | None           # 成功时的帖子链接
  message:  str | None           # 失败原因 / 跳过说明 / 操作指引
```

---

## 5. 适配层规则(举例)

| 平台 | 适配规则 |
|---|---|
| X | 无标题;正文作为 tweet,超 280 字报错;tags→ `#AI #出海` 拼到文末;图最多 4 张 |
| 小红书 | 标题 ≤20 字;正文 + tags 拼成笔记;图最多 18 张;视频走视频流程 |
| YouTube | title→视频标题;body→description;tags→ tags 字段;**必须有 video**,无 video 则跳过 |

**设计要点:**
1. **校验前置**: 发布前对每个选中平台校验,不匹配的在面板提前标黄警告,不盲发。
2. **内容类型不匹配自动跳过**: 例如只传图文未传视频,YouTube 标记为 `skipped`(需要视频),不报错。
3. **overrides 可选**: 默认一份文案全平台通用;需要单独版本时在面板对应平台展开编辑。

---

## 6. 凭证管理

### 6.1 浏览器引擎(小红书/抖音/视频号)— 靠 Chrome 登录态
- 连接一个**已登录的 Chrome**(CDP),复用现有标签页登录 cookie。
- 工具**不存储账号密码**,只借用已登录的浏览器会话。
- 面板显示各浏览器平台登录状态;未登录时提示用户先在 Chrome 登录。
- **已知坑(复用 `post-to-xhs` 已修逻辑规避):**
  - 跑之前清除代理环境变量(`HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` 等),否则本地 CDP 走 SOCKS5 卡死。
  - `--reuse-existing-tab` 遇到 update 页会卡死 —— 沿用现有处理。
  - 上传图文 tab 的 Vue 异步渲染时序问题 —— 沿用现有的轮询重试。

### 6.2 API 引擎(X/YouTube)— 存 token,本地隔离
- API key / OAuth token 存 `config/credentials.json`,**加入 `.gitignore`,不进 git**。
- YouTube 走 Google OAuth(一次授权,自动刷新 token);X 走 API key。
- 面板提供"连接账号"按钮,首次走授权流程,之后自动复用。

### 6.3 待查证(落地时确认,不凭记忆)
- **X API 访问层级**: 免费层是否有写(发推)权限、月限额多少、是否需付费层。做之前先查证官方文档。
- **YouTube Data API 配额**: 上传视频消耗的配额单位与每日上限。
- **TikTok Content Posting API**: 审核与权限门槛(后续平台,非 MVP)。

---

## 7. 错误处理

| 场景 | 处理 |
|---|---|
| 某平台发布失败 | 独立捕获,其他平台照常发;面板标红 + 显示原因 |
| 未登录 / token 过期 | 标 `needs_login`,给操作指引,不算崩溃 |
| 内容不匹配(如无视频发 YouTube) | 发布前标 `skipped`,不尝试 |
| 浏览器引擎超时/卡死 | 复用脚本退出码 + 超时控制,回传明确原因 |
| 全部完成 | 面板汇总:✅ 成功(给链接) / ❌ 失败(给原因) / ⊘ 跳过(给说明) |

- **结果反馈**: 发布后面板每平台一行 —— 状态图标 + 链接或错误原因。
- **单平台重试**: 失败的平台可单独重试,不必全部重发。
- **核心原则**: 永不黑盒。每个平台发没发成、为什么失败、怎么补救,都明确告诉用户。

---

## 8. 目录结构(初步)

```
crosspost/
  app.py                  # FastAPI 入口
  orchestrator.py         # 编排器
  models.py               # Post / Media / Result 数据模型
  adapters/               # 各平台适配规则
  publishers/
    base.py               # BrowserPublisher / ApiPublisher 基类
    xhs.py                # 小红书(复用 post-to-xhs)
    x.py                  # X
    youtube.py            # YouTube
  credentials/            # 凭证读写(credentials.json 不进 git)
  web/                    # 前端静态页
  config/
    credentials.json      # (gitignored)
  docs/specs/             # 本设计文档
  .gitignore
  requirements.txt
```

---

## 9. 验收标准(MVP)

- [ ] 本地起服务,浏览器打开面板可填写标题/正文/标签、上传图片或选择视频文件。
- [ ] 勾选小红书 + X + YouTube,点发布。
- [ ] 发布前面板正确标出各平台校验状态(可发 / 标黄警告 / 跳过)。
- [ ] 小红书成功发布(复用现有脚本,图文与视频各验证一次)。
- [ ] X 成功发布图文(待 API 层级查证后)。
- [ ] YouTube 成功上传视频(走 OAuth)。
- [ ] 任一平台失败不影响其他平台;面板汇总每平台状态 + 链接/原因。
- [ ] 失败平台可单独重试。

---

## 10. 后续扩展(非 MVP)

- 增量加平台:抖音、视频号(Browser);LinkedIn、TikTok、B站(API)
- 定时发布
- 数据回收(阅读量/互动统计)
- 多账号切换
