# AI Daily Bot — Automated AI News Digest Bot

> Automatically fetches the latest AI news from YouTube / TechCrunch / Twitter every day at 20:00 Beijing time, translates and summarizes them via Groq LLM, and posts the final digest to your **Telegram channel** (or optionally Twitter / Instagram).  
> Runs entirely on GitHub Actions free tier.

---

## ✨ Features

- 🧠 **Smart Scraping** – Uses [Jina AI Reader](https://jina.ai/reader) (free, no API key required) to extract clean content from any webpage.
- 🤖 **AI Processing** – Groq's free LLM (`llama-3.3-70b-versatile`) performs translation, 5 key takeaways per video, 100-word article summaries, tweet-by-tweet analysis, and overall sentiment.
- 📄 **Rich Output** – Generates a Markdown report + a 1080×1350 PNG image (suitable for Instagram / Telegram).
- 📤 **Publishing**:
  - Primary (recommended): **Telegram channel** – completely free, no limits.
  - Optional: Twitter (requires $5 prepaid credits) / Instagram (requires Business account + Facebook Page).
- ⏰ **Scheduled** – Runs daily at UTC 12:00 (Beijing 20:00) via GitHub Actions.

---

## 🧱 Tech Stack

| Component | Purpose | Cost |
|-----------|---------|------|
| GitHub Actions | Scheduled runs + code hosting | Free (2000 min/month) |
| Jina AI Reader | Web → Markdown extraction | Free (no API key) |
| Groq | LLM translation + summarization | Free (registration required) |
| ImgBB | Image hosting fallback | Free (API key after registration) |
| Telegram Bot API | Publish to channel | Completely free |
| (Optional) Twitter API | Post tweet threads | $0.01/tweet, $5 prepaid |
| (Optional) Instagram Graph API | Post image to feed | Free (Business account required) |

---

# AI Daily Bot

每日北京时间 **20:00** 自动抓取 YouTube / TechCrunch / Twitter 上的 AI 资讯，
经 Groq LLM 翻译加工成中文日报，并同步发布到 **Twitter（线程）** 和
**Instagram（图文）**。运行在 GitHub Actions 免费额度内。

---

## 目录结构

```
.
├── main.py                       # 流程入口
├── fetcher.py                    # Jina AI Reader 抓取
├── processor.py                  # Groq LLM 翻译 + 摘要
├── renderer.py                   # Markdown / Twitter thread / IG 图片
├── publishers.py                 # Twitter + Instagram 发布（含付费平台扩展点）
├── requirements.txt
├── .github/workflows/daily.yml   # cron + workflow_dispatch
└── output/                       # 运行产物（Markdown + PNG）
```

---

## 一、需要注册的免费账号

| 服务 | 注册地址 | 用途 | 费用 |
|---|---|---|---|
| Jina AI Reader | https://jina.ai/reader | 抓取页面纯文本 | 免费，无需 key |
| Groq | https://console.groq.com | LLM 翻译/摘要 | 免费额度 |
| Twitter Developer | https://developer.twitter.com | 发布推文线程 | Free 套餐 500 推/月 |
| Meta for Developers | https://developers.facebook.com | Instagram 图文发布 | 免费 |

---

## 二、获取每个 Secret 的具体步骤

### 1. `GROQ_API_KEY`
1. 登录 https://console.groq.com
2. 左侧菜单 **API Keys** → **Create API Key**
3. 命名后复制以 `gsk_` 开头的字符串

### 2. Twitter 4 件套
`X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_SECRET`
1. https://developer.twitter.com → **Projects & Apps** → 进入你的 App
2. **Keys and tokens** 页：
   - 上方 **Consumer Keys** → 复制 `API Key` 与 `API Key Secret`
   - 下方 **Authentication Tokens → Access Token and Secret** → **Generate**
3. 必须确保 App 在 **User authentication settings** 里开启了 **Read and write**

### 3. Instagram 2 件
- `IG_BUSINESS_ACCOUNT_ID`
- `IG_ACCESS_TOKEN`（长期 Page Access Token）

前置：IG 账号已切换为 **Business** 并绑定一个 **Facebook Page**。

获取流程：
1. https://developers.facebook.com → **My Apps** → 新建 App（Type: Business）
2. 添加产品 **Instagram Graph API**
3. **Tools → Graph API Explorer**：
   - 选你的 App，生成 **User Access Token**，勾选权限：
     `pages_show_list, pages_read_engagement, instagram_basic, instagram_content_publish, business_management`
   - 查询 `me/accounts` → 拿到 Page 的 `access_token`（短期）
   - 用 https://developers.facebook.com/tools/debug/accesstoken/ → **Extend Access Token** → 获得长期 Page Access Token，填入 `IG_ACCESS_TOKEN`
4. 拿 IG Business Account ID：Graph API Explorer 查询 `{page-id}?fields=instagram_business_account` → 返回的 id 填入 `IG_BUSINESS_ACCOUNT_ID`

> 注意：本项目所有 IG 调用走 `graph.facebook.com`，**不要**用 `graph.instagram.com`。

### 4. （可选）`GROQ_MODEL`
作为 GitHub repository variable（不是 secret）配置，默认 `llama-3.3-70b-versatile`。
也可改为 `llama-3.1-8b-instant` 节省额度。

---

## 三、在 GitHub 设置 Secrets

1. 仓库主页 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**，逐个新建以下 7 个：

```
GROQ_API_KEY
X_API_KEY
X_API_SECRET
X_ACCESS_TOKEN
X_ACCESS_SECRET
IG_ACCESS_TOKEN
IG_BUSINESS_ACCOUNT_ID
```

3. （可选）切到 **Variables** 标签新建 `GROQ_MODEL`

---

## 四、手动触发一次测试

1. 仓库 → **Actions** → 左侧 **AI Daily Report**
2. 右上 **Run workflow** → 选择分支 → **Run workflow**
3. 等待 ~3-5 分钟，日志最后一行应输出：
   ```
   日报已发布到 Twitter 和 Instagram
   ```
4. 运行产物（Markdown + PNG）可在底部 **Artifacts → ai-daily-output** 下载

cron 计划：每天 UTC `12:00` = **北京时间 20:00** 自动运行。

---

## 五、付费平台扩展

`publishers.py` 末尾 `=== 付费平台扩展开始 ===` 段落中已写出
**微信公众号 / 知乎 / 小红书 / 简书** 的扩展框架与启用条件。默认未启用，注释状态。

如未来愿意付费/出认证主体，按各段说明取消注释并补充对应 secrets 即可。

---

## 六、本地调试

```bash
pip install -r requirements.txt
export GROQ_API_KEY=...
export X_API_KEY=...  X_API_SECRET=...  X_ACCESS_TOKEN=...  X_ACCESS_SECRET=...
export IG_ACCESS_TOKEN=...  IG_BUSINESS_ACCOUNT_ID=...
python main.py
```

输出会写入 `output/AI_Daily_YYYYMMDD.{md,png}`。

---

## 七、故障排查

| 现象 | 排查方向 |
|---|---|
| Jina 返回为空 | Jina 偶发限速，重试一次即可；workflow 已内置重试 |
| Groq 报 model not found | 切换 `GROQ_MODEL` 为 `llama-3.1-8b-instant` |
| Twitter 403 | App 未开 **Read and write** 权限，或 Free 套餐 500/月 用尽 |
| IG container 一直 ERROR | 图床 URL 不可达 / 图片格式非 JPG/PNG / IG 账号未切 Business |
| 中文显示为方块 | workflow 没装 `fonts-noto-cjk`，检查日志中 apt-get 是否成功 |


## 📁 Repository Structure
