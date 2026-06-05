"""Publish to Twitter and Instagram. All endpoints reach graph.facebook.com for IG."""
import os
import time

import requests
import tweepy


# ---------------------------------------------------------------- Twitter
def publish_twitter_thread(tweets: list) -> int:
    """Post tweets as a connected thread. Returns count successfully posted."""
    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
        wait_on_rate_limit=False,
    )
    reply_to, posted = None, 0
    for i, text in enumerate(tweets, 1):
        try:
            kwargs = {"text": text}
            if reply_to:
                kwargs["in_reply_to_tweet_id"] = reply_to
            resp = client.create_tweet(**kwargs)
            reply_to = resp.data["id"]
            posted += 1
            print(f"   tweet {i}/{len(tweets)} ok id={reply_to}")
            time.sleep(2)
        except Exception as e:
            print(f"   tweet {i}/{len(tweets)} fail: {e}")
    if posted == 0:
        raise RuntimeError("all thread tweets failed")
    return posted


# ---------------------------------------------------------------- Instagram
# Per IG Graph API: container -> poll status -> publish.
# Endpoints under graph.facebook.com (NOT graph.instagram.com).
GRAPH = "https://graph.facebook.com/v21.0"


def publish_instagram(image_path: str, md_text: str, now) -> str:
    token = os.environ["IG_ACCESS_TOKEN"]
    ig_user = os.environ["IG_BUSINESS_ACCOUNT_ID"]

    image_url = _upload_image_to_public_host(image_path)
    print(f"   image hosted at: {image_url}")
    caption = _build_ig_caption(now)

    # Step 1: create container
    r1 = requests.post(
        f"{GRAPH}/{ig_user}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    )
    if not r1.ok:
        raise RuntimeError(f"create_media failed: {r1.status_code} {r1.text}")
    creation_id = r1.json()["id"]

    # Step 2: poll until FINISHED (image fetch + processing)
    for _ in range(15):
        time.sleep(3)
        s = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"container error: {s}")

    # Step 3: publish
    r3 = requests.post(
        f"{GRAPH}/{ig_user}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    if not r3.ok:
        raise RuntimeError(f"media_publish failed: {r3.status_code} {r3.text}")
    media_id = r3.json().get("id")
    print(f"   instagram media_id={media_id}")
    return media_id


def _upload_image_to_public_host(path: str) -> str:
    """Anonymous free image hosts. Tries 0x0.st then catbox.moe."""
    hosts = [
        ("https://0x0.st", "file"),
        ("https://catbox.moe/user/api.php", "fileToUpload"),
    ]
    last = None
    for url, field in hosts:
        try:
            with open(path, "rb") as f:
                files = {field: f}
                data = {"reqtype": "fileupload"} if "catbox" in url else None
                r = requests.post(
                    url, files=files, data=data,
                    headers={"User-Agent": "ai-daily-bot/1.0"},
                    timeout=60,
                )
            if r.ok and r.text.strip().startswith("http"):
                return r.text.strip()
            last = f"{url} -> {r.status_code} {r.text[:120]}"
        except Exception as e:
            last = f"{url} -> {e}"
    raise RuntimeError(f"all image hosts failed: {last}")


def _build_ig_caption(now) -> str:
    date_str = now.strftime("%Y.%m.%d")
    cap = (
        f"AI日报 · {date_str}\n\n"
        "今日聚焦：TechCrunch 头条 · X 舆论 · YouTube 焦点。\n"
        "完整深度日报详见个人主页链接。\n\n"
        "#AI #人工智能 #LLM #AIDaily #MachineLearning #大模型 #科技 #ChatGPT #AIGC #DeepLearning"
    )
    return cap[:2200]


# =================================================================
# === 付费平台扩展开始 ============================================
# 以下平台默认未启用。需要付费认证或企业资质后取消注释并配置凭证。
# =================================================================

# --- 微信公众号 -------------------------------------------------------------
# 启用条件：
#   1. 微信【服务号】（个人订阅号不开放群发 API）
#   2. 完成微信认证（年费 300 元，需企业/组织主体）
#   3. 在 GitHub Secrets 配置 WECHAT_APPID / WECHAT_APPSECRET
# 调用流程：access_token -> 上传永久素材(封面) -> add draft -> freepublish/submit
#
# def publish_wechat(article_md: str, cover_path: str) -> str:
#     import requests
#     appid = os.environ["WECHAT_APPID"]
#     secret = os.environ["WECHAT_APPSECRET"]
#     tok = requests.get(
#         "https://api.weixin.qq.com/cgi-bin/token",
#         params={"grant_type": "client_credential", "appid": appid, "secret": secret},
#         timeout=30,
#     ).json()["access_token"]
#     # upload cover -> get thumb_media_id
#     # POST /cgi-bin/draft/add  with html article
#     # POST /cgi-bin/freepublish/submit
#     raise NotImplementedError("启用付费认证后再实现")


# --- 知乎专栏 --------------------------------------------------------------
# 启用条件：
#   1. 账号等级 ≥ 5 才能开启赞赏
#   2. 通过 cookie 模拟登录调用 zhuanlan.zhihu.com/api/columns/{id}/articles
#   3. 长期跑会触发风控，封号风险较高
#
# def publish_zhihu(article_md: str) -> str:
#     cookie = os.environ["ZHIHU_COOKIE"]
#     column_id = os.environ["ZHIHU_COLUMN_ID"]
#     raise NotImplementedError("不推荐自动化，仅保留扩展点")


# --- 小红书 ----------------------------------------------------------------
# 官方未开放任何发布 API；客户端 X-S/X-T 签名 + 设备指纹 + 短信验证轮换；
# 开源方案普遍 3 个月内失效，封号率高。建议放弃自动化。
#
# def publish_xiaohongshu(image_path: str, caption: str) -> str:
#     raise NotImplementedError("技术上不可持续，建议放弃")


# --- 简书 ------------------------------------------------------------------
# 仅 cookie 鉴权可行；流量与变现能力大幅下滑，ROI 低。
#
# def publish_jianshu(article_md: str) -> str:
#     raise NotImplementedError("ROI 低，不建议接入")

# =================================================================
# === 付费平台扩展结束 ============================================
# =================================================================
