"""Fetch raw content via Jina AI Reader (https://r.jina.ai/).

No API key required. Returns plaintext / markdown-flavoured text.
"""
import re
import time
import requests

JINA_PREFIX = "https://r.jina.ai/"
HEADERS = {
    "Accept": "text/plain",
    "User-Agent": "ai-daily-bot/1.0 (+github actions)",
}
TIMEOUT = 60
RETRIES = 2


def _get(target_url: str) -> str:
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            r = requests.get(JINA_PREFIX + target_url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200 and r.text:
                return r.text
            last_err = f"http {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(2 * (attempt + 1))
    print(f"   [warn] jina fetch failed for {target_url}: {last_err}")
    return ""


# ---------------------------------------------------------------- YouTube
_YT_LINK = re.compile(
    r"\[([^\]\n]{8,200})\]\(https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})[^\)]*\)"
)


def fetch_youtube(limit: int = 5) -> list:
    raw = _get("https://www.youtube.com/results?search_query=AI+news+today&sp=CAI%253D")
    if not raw:
        return []
    videos, seen = [], set()
    for m in _YT_LINK.finditer(raw):
        vid = m.group(2)
        title = _clean(m.group(1))
        if vid in seen or _is_navigational(title):
            continue
        seen.add(vid)
        videos.append({
            "video_id": vid,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
        if len(videos) >= limit:
            break

    # Fetch each detail page to enrich description + channel
    for v in videos:
        page = _get(v["url"])
        v["description"] = _yt_extract_description(page)
        v["channel"] = _yt_extract_channel(page)
    return videos


def _yt_extract_description(text: str) -> str:
    if not text:
        return ""
    # Jina output often labels description section
    m = re.search(
        r"(?:^|\n)(?:Description|描述)\s*[:：\n]+(.+?)(?:\n\n(?:Transcript|Comments|Music|Suggested|Show less)|\Z)",
        text, re.IGNORECASE | re.DOTALL,
    )
    if m:
        return _clean(m.group(1))[:1500]
    # Fallback: longest paragraph not starting with markdown link
    best = ""
    for para in text.split("\n\n"):
        p = para.strip()
        if len(p) > 120 and not p.startswith("[") and "http" not in p[:30]:
            if len(p) > len(best):
                best = p
    return _clean(best)[:1500]


def _yt_extract_channel(text: str) -> str:
    m = re.search(r"\[@?([A-Za-z0-9_.\u4e00-\u9fff-]+)\]\(https://www\.youtube\.com/@", text)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- TechCrunch
_TC_LINK = re.compile(
    r"\[([^\]\n]{15,200})\]\((https://techcrunch\.com/\d{4}/\d{2}/\d{2}/[^\)\s]+/)\)"
)


def fetch_techcrunch(limit: int = 5) -> list:
    raw = _get("https://techcrunch.com/category/artificial-intelligence/")
    if not raw:
        return []
    articles, seen = [], set()
    for m in _TC_LINK.finditer(raw):
        url = m.group(2)
        title = _clean(m.group(1))
        if url in seen or _is_navigational(title):
            continue
        seen.add(url)
        articles.append({"title": title, "url": url})
        if len(articles) >= limit:
            break

    for a in articles:
        page = _get(a["url"])
        a["body"] = _tc_extract_body(page)
    return articles


def _tc_extract_body(text: str) -> str:
    if not text:
        return ""
    paras = [p.strip() for p in text.split("\n\n")]
    # Skip site chrome (first few short lines), pick substantive paragraphs
    body_paras = [
        p for p in paras
        if len(p) > 100 and not p.startswith(("![", "#", "[", "* "))
    ]
    body = "\n\n".join(body_paras[:6])
    return _clean(body)[:2200]


# ---------------------------------------------------------------- Twitter
# Without paid X API search, use Google site-search proxied via Jina.
_TW_LINK = re.compile(
    r"\[([^\]\n]{20,400})\]\((https://(?:x|twitter)\.com/[^\)/\s]+/status/\d+)[^\)]*\)"
)


def fetch_twitter(limit: int = 10) -> list:
    queries = [
        "https://www.google.com/search?q=%23AI+OR+%23MachineLearning+OR+%23LLM+site%3Ax.com&tbs=qdr:d",
        "https://www.google.com/search?q=%23AI+OR+%23GenAI+site%3Atwitter.com&tbs=qdr:d",
    ]
    tweets, seen = [], set()
    for url in queries:
        raw = _get(url)
        if not raw:
            continue
        for m in _TW_LINK.finditer(raw):
            link = m.group(2).replace("twitter.com", "x.com")
            text = _clean(m.group(1))
            if link in seen or len(text) < 25:
                continue
            seen.add(link)
            handle = re.search(r"x\.com/([^/]+)/status", link)
            tweets.append({
                "text": text,
                "url": link,
                "author": "@" + handle.group(1) if handle else "",
            })
            if len(tweets) >= limit:
                return tweets
        if len(tweets) >= limit:
            break
    return tweets


# ---------------------------------------------------------------- helpers
def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


_NAV_TOKENS = {
    "home", "shorts", "subscriptions", "library", "history", "trending",
    "next page", "previous", "sign in", "更多", "首页", "登录",
}


def _is_navigational(t: str) -> bool:
    return t.strip().lower() in _NAV_TOKENS
