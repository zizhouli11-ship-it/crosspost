# crosspost — 跨平台内容发布工具(MVP)

一份内容(图文/视频)→ 自动适配各平台 → 一键发布,并在本地网页面板看每个平台的发布结果。

当前支持五个平台,覆盖两种引擎、两种内容形态:

| 平台 | 引擎 | 内容 |
|---|---|---|
| 小红书 | 浏览器自动化(复用 post-to-xhs) | 图文 + 视频 |
| X (Twitter) | 官方 API | 图文 |
| YouTube | 官方 API | 视频 |
| 抖音 | 浏览器自动化(CDP,本工具自带 cdp.py) | 视频 |
| TikTok | 官方 API(草稿箱) | 视频 |

## 启动

双击 `run.bat`(会自动清代理、起服务、打开浏览器),或手动:

```
cd C:\Users\30488\crosspost
.venv\Scripts\python.exe -m uvicorn app:app --port 8765
```

然后浏览器打开 http://127.0.0.1:8765 。

## 三个平台各自的前置条件

- **小红书**:像平时用 post-to-xhs 一样,先用带 CDP 调试端口的 Chrome 登录小红书。面板里小红书显示「就绪」即可发。
- **X**:在面板「设置 / 连接账号」里填 4 个密钥(api_key / api_secret / access_token / access_token_secret),保存即生效。
  - 注意:X 发推需要有写权限的 API 套餐(免费层据传只读),发之前请到 X 开发者后台确认你的 App 有写权限,否则会返回 403。
- **YouTube**:到 Google Cloud Console 建项目 → 启用 YouTube Data API v3 → 建 OAuth 客户端(桌面应用)→ 下载 JSON 放到 `config/youtube_client_secret.json`,然后在面板点「连接 YouTube」走一次授权。
  - 上传默认设为 private,可在 YouTube 工作室改公开。每次上传约耗 1600 配额单位(默认日配额 1 万,约 6 次/天)。
- **抖音**:不需要密钥。用带远程调试端口的 Chrome 打开并登录抖音创作者后台(和小红书同一个调试 Chrome,端口 9222)即可。
  - 抖音页面经常改版,首次跑大概率要对着真实页面调一轮选择器(选择器都集中在 `crosspost/publishers/douyin.py` 顶部的 `SELECTORS`)。第一轮可先跑 `DouyinPublisher(...).probe()` 看页面/选择器命中情况。
- **TikTok**:在 TikTok 开发者后台建应用,拿到 access_token(以及可选 refresh_token / client_key / client_secret),在面板「设置」里填好保存。
  - 应用未过审时只能上传到**草稿箱**(视频进你 TikTok App 的草稿,在 App 里完成发布);过审后可改直发。

## 已验证(自动化层面)

- 48 个单元测试全绿:数据模型、五个平台适配与校验、凭证存储、编排器隔离、各发布器(API 调用以 mock 验证请求构造,CDP 客户端以 fake socket 验证消息收发)。
- 服务端 HTTP 冒烟:`/api/platforms`(列出 5 平台)、`/api/validate`(带视频→ 五平台均 ok;纯文字→ 视频类平台 skip)、`/api/credentials/x`、`/api/credentials/tiktok`(保存后由未连接→就绪)均符合预期。

## 待你做真实发布验证(需要真实登录态/密钥,我无法代做)

1. 小红书图文 + 视频各发一次。
2. X 配好密钥后发一条图文。
3. YouTube 授权后传一个视频。
4. **抖音**:开着已登录的调试 Chrome,先跑一次 probe 确认能连上、再发一个视频(大概率要一起调一轮选择器)。
5. **TikTok**:填好 access_token 后传一个视频到草稿箱,在 App 里确认。
6. 多平台合并发布:任一失败不影响其他,结果分别带链接/原因。

## 加新平台(扩展)

照现有模式:
- 浏览器类(抖音/视频号)→ 新增一个 `crosspost/publishers/xxx.py` + `crosspost/adapters/xxx.py`,在 `crosspost/registry.py` 注册。
- API 类(LinkedIn/TikTok/B站)→ 同上,publisher 走官方 API。

设计文档见 `docs/specs/`,实现计划见 `docs/plans/`。

## 已知未做(MVP 范围外 / 后续)

- 失败平台的「单独重试」按钮:当前可手动只勾选失败的那个平台再发一次(等效重试)。
- 定时发布、数据回收(阅读量/互动)、多账号切换。
