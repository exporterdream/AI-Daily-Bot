"""Render outputs: Markdown daily report, Twitter thread, Instagram image."""
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------- Markdown
def render_markdown(yt: list, tc: list, tw: list, sentiment: str, now) -> str:
    date_str = now.strftime("%Y年%m月%d日")
    L = [f"# 今日AI日报（{date_str}）", ""]

    if tc:
        L += ["## TechCrunch · 人工智能头条", ""]
        for i, a in enumerate(tc, 1):
            tags = " ".join(f"`{t}`" for t in a.get("tags", []))
            L += [
                f"### {i}. {a.get('translated_title', '')}",
                f"- **标签**：{tags}",
                f"- **核心看点**：{a.get('deep_summary', '')}",
                f"- **简介提取**：{a.get('translated_body', '')}",
                f"- **链接**：{a.get('url', '')}",
                "", "---", "",
            ]

    if tw:
        L += ["## Twitter · 热门推文舆论场", "",
              "### 推文逐条摘要", "",
              "| # | 单条总结 | 标签 |",
              "|---|---------|------|"]
        for i, t in enumerate(tw, 1):
            tags = " ".join(f"`{x}`" for x in t.get("tags", []))
            summ = (t.get("one_sentence_summary", "") or "").replace("|", "\\|")
            L.append(f"| {i} | {summ} | {tags} |")
        L += ["", "### 整体舆论风向", "", f"> {sentiment}", "", "---", ""]

    if yt:
        L += ["## YouTube 流量秘密", ""]
        for i, v in enumerate(yt, 1):
            tags = " ".join(f"`{x}`" for x in v.get("tags", []))
            L += [
                f"### {i}. {v.get('translated_title', '')}",
                f"- **标签**：{tags}",
                "- **核心看点**：",
            ]
            for j, kp in enumerate(v.get("key_points", []), 1):
                L.append(f"  {j}. {kp}")
            L += [
                f"- **简介提取**：{v.get('translated_description', '')}",
                f"- **链接**：{v.get('url', '')}",
                "", "---", "",
            ]
    return "\n".join(L)


# ---------------------------------------------------------------- Twitter thread
def render_twitter_thread(yt: list, tc: list, tw: list, sentiment: str, now) -> list:
    date_str = now.strftime("%m月%d日")
    out = []

    # Tweet 1: overview
    out.append(
        f"AI日报 · {date_str}\n\n"
        f"今日速览：\n"
        f"• TechCrunch 头条 {len(tc)} 篇\n"
        f"• 热门推文舆论 {len(tw)} 条\n"
        f"• YouTube AI 视频 {len(yt)} 支\n\n"
        f"线索 👇"
    )

    for a in tc[:3]:
        title = (a.get("translated_title") or "")[:60]
        summ = (a.get("deep_summary") or "")[:140]
        out.append(f"📰 {title}\n\n{summ}\n\n{a.get('url', '')}")

    if sentiment:
        out.append(f"🧭 今日X舆论风向\n\n{sentiment[:240]}")

    for v in yt[:2]:
        title = (v.get("translated_title") or "")[:60]
        kps = "\n".join(f"• {k}" for k in (v.get("key_points") or [])[:3])
        out.append(f"📹 {title}\n\n{kps}\n\n{v.get('url', '')}")

    # Twitter v2 limit is 280 chars; keep margin for unicode + reply context
    return [t[:270] for t in out if t.strip()]


# ---------------------------------------------------------------- Instagram image
def render_instagram_image(yt: list, tc: list, tw: list, now, out_path: str) -> str:
    W, H = 1080, 1350
    BG = (18, 18, 26)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    font_path = _find_cjk_font()

    def F(size):
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

    f_title = F(64)
    f_h2 = F(38)
    f_body = F(28)
    f_small = F(22)

    # Header
    d.text((60, 60), "AI 日报", fill=(255, 255, 255), font=f_title)
    d.text((60, 150), now.strftime("%Y.%m.%d"), fill=(180, 180, 200), font=f_small)
    d.line([(60, 200), (W - 60, 200)], fill=(80, 80, 120), width=2)

    y = 230

    # TechCrunch (up to 2)
    if tc:
        d.text((60, y), "📰 TechCrunch 头条", fill=(255, 180, 80), font=f_h2)
        y += 60
        for a in tc[:2]:
            y = _draw_block(
                d, (60, y), W - 120,
                title=a.get("translated_title", ""),
                body=a.get("deep_summary", ""),
                f_title=f_body, f_body=f_small,
                title_color=(255, 255, 255), body_color=(200, 200, 210),
            )
            y += 14

    # YouTube (up to 2)
    if yt:
        y += 10
        d.text((60, y), "📹 YouTube 焦点", fill=(255, 110, 130), font=f_h2)
        y += 60
        for v in yt[:2]:
            kp_lines = "\n".join(f"• {k}" for k in (v.get("key_points") or [])[:2])
            y = _draw_block(
                d, (60, y), W - 120,
                title=v.get("translated_title", ""),
                body=kp_lines,
                f_title=f_body, f_body=f_small,
                title_color=(255, 255, 255), body_color=(200, 200, 210),
            )
            y += 14

    # Twitter mini (up to 3)
    if tw:
        y += 10
        d.text((60, y), "🐦 X 舆论摘要", fill=(120, 200, 255), font=f_h2)
        y += 56
        for t in tw[:3]:
            s = t.get("one_sentence_summary", "")
            for line in _wrap(f"• {s}", 26)[:1]:
                d.text((60, y), line, fill=(220, 220, 230), font=f_small)
                y += 34

    d.text((60, H - 60), "daily AI intel · follow for more", fill=(120, 120, 140), font=f_small)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def _draw_block(d, origin, max_w, title, body, f_title, f_body, title_color, body_color):
    x, y = origin
    for line in _wrap(title, 24)[:2]:
        d.text((x, y), line, fill=title_color, font=f_title)
        y += 38
    for line in _wrap(body, 28)[:3]:
        d.text((x, y), line, fill=body_color, font=f_body)
        y += 30
    return y


def _wrap(text: str, width: int) -> list:
    out = []
    for para in (text or "").split("\n"):
        para = para.strip()
        if not para:
            continue
        # textwrap handles CJK as 1 unit wide each; tune width per font visually
        wrapped = textwrap.wrap(para, width=width, break_long_words=True)
        out.extend(wrapped or [para[:width]])
    return out


def _find_cjk_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None
