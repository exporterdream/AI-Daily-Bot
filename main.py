"""AI Daily Report — orchestrator.
Runs once per invocation: fetch → process → render → publish.
"""
import os
import sys
from datetime import datetime, timezone, timedelta

from fetcher import fetch_youtube, fetch_techcrunch, fetch_twitter
from processor import (
    process_youtube,
    process_techcrunch,
    process_twitter,
    twitter_sentiment,
)
from renderer import render_markdown, render_twitter_thread, render_instagram_image
from publishers import publish_twitter_thread, publish_instagram

BEIJING = timezone(timedelta(hours=8))


def main() -> int:
    now = datetime.now(BEIJING)
    print(f"[start] {now.isoformat()} (Asia/Shanghai)")

    print("[1/5] Fetching sources via Jina AI Reader ...")
    yt_raw = _safe(fetch_youtube, default=[])
    tc_raw = _safe(fetch_techcrunch, default=[])
    tw_raw = _safe(fetch_twitter, default=[])
    print(f"   YouTube={len(yt_raw)} TechCrunch={len(tc_raw)} Twitter={len(tw_raw)}")

    if not (yt_raw or tc_raw or tw_raw):
        print("[fatal] All sources empty. Aborting.")
        return 1

    print("[2/5] Processing with Groq LLM ...")
    yt = [process_youtube(v) for v in yt_raw]
    tc = [process_techcrunch(a) for a in tc_raw]
    tw = [process_twitter(t) for t in tw_raw]
    sentiment = twitter_sentiment(tw) if tw else ""

    print("[3/5] Rendering outputs ...")
    os.makedirs("output", exist_ok=True)
    stamp = now.strftime("%Y%m%d")
    md = render_markdown(yt, tc, tw, sentiment, now)
    md_path = f"output/AI_Daily_{stamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"   markdown -> {md_path}")

    img_path = f"output/AI_Daily_{stamp}.png"
    try:
        render_instagram_image(yt, tc, tw, now, img_path)
        print(f"   image -> {img_path}")
    except Exception as e:
        print(f"   image render failed: {e}")
        img_path = None

    thread = render_twitter_thread(yt, tc, tw, sentiment, now)

    print("[4/5] Publishing Twitter thread ...")
    tw_ok = False
    try:
        publish_twitter_thread(thread)
        tw_ok = True
    except Exception as e:
        print(f"   twitter publish failed: {e}")

    print("[5/5] Publishing Instagram post ...")
    ig_ok = False
    if img_path:
        try:
            publish_instagram(img_path, md, now)
            ig_ok = True
        except Exception as e:
            print(f"   instagram publish failed: {e}")
    else:
        print("   skipped (no image)")

    targets = []
    if tw_ok:
        targets.append("Twitter")
    if ig_ok:
        targets.append("Instagram")
    msg = " 和 ".join(targets) if targets else "（无平台成功）"
    print(f"日报已发布到 {msg}")
    return 0 if (tw_ok or ig_ok) else 2


def _safe(fn, default):
    try:
        return fn()
    except Exception as e:
        print(f"   [warn] {fn.__name__} failed: {e}")
        return default


if __name__ == "__main__":
    sys.exit(main())
