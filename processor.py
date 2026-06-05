"""Process raw items via Groq LLM (translation, summaries, tags)."""
import json
import os
import re
import time

from groq import Groq

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
_client = None


def _client_lazy():
    global _client
    if _client is None:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY env var is required")
        _client = Groq(api_key=key)
    return _client


def _chat(system: str, user: str, json_mode: bool = False, retries: int = 2) -> str:
    last_err = None
    for attempt in range(retries + 1):
        try:
            kwargs = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.3,
                "max_tokens": 1200,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = _client_lazy().chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    print(f"   [warn] groq call failed after retries: {last_err}")
    return ""


def _safe_json(raw: str) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


# ---------------------------------------------------------------- YouTube
def process_youtube(v: dict) -> dict:
    sys_p = "你是专业的中英翻译与内容分析助手。只输出合法JSON对象，不要任何额外文字或代码块标记。"
    user_p = (
        "请处理以下YouTube视频，输出JSON对象，字段：\n"
        "- translated_title: 标题的中文翻译，通俗流畅\n"
        "- translated_description: 简介的中文翻译，200-300字\n"
        "- key_points: 数组，5个核心看点，每个15字以内\n"
        "- tags: 数组，3-5个中文标签\n\n"
        f"标题：{v.get('title', '')}\n"
        f"简介：{(v.get('description', '') or '')[:1500]}"
    )
    data = _safe_json(_chat(sys_p, user_p, json_mode=True))
    v["translated_title"] = data.get("translated_title") or v.get("title", "")
    v["translated_description"] = data.get("translated_description") or ""
    v["key_points"] = (data.get("key_points") or [])[:5]
    v["tags"] = (data.get("tags") or [])[:5]
    if v.get("description") and not v["key_points"]:
        v["key_points"] = ["生成失败"]
    return v


# ---------------------------------------------------------------- TechCrunch
def process_techcrunch(a: dict) -> dict:
    sys_p = "你是专业的中英翻译与内容分析助手。只输出合法JSON对象，不要任何额外文字或代码块标记。"
    user_p = (
        "请处理以下TechCrunch文章，输出JSON对象，字段：\n"
        "- translated_title: 标题中文翻译\n"
        "- translated_body: 正文前500字的中文翻译段落\n"
        "- deep_summary: 不超过100字的中文深度摘要，涵盖核心论点、关键数据与结论\n"
        "- tags: 数组，3-5个中文标签\n\n"
        f"标题：{a.get('title', '')}\n"
        f"正文：{(a.get('body', '') or '')[:1800]}"
    )
    data = _safe_json(_chat(sys_p, user_p, json_mode=True))
    a["translated_title"] = data.get("translated_title") or a.get("title", "")
    a["translated_body"] = data.get("translated_body") or ""
    a["deep_summary"] = data.get("deep_summary") or "生成失败"
    a["tags"] = (data.get("tags") or [])[:5]
    return a


# ---------------------------------------------------------------- Twitter
def process_twitter(t: dict) -> dict:
    sys_p = "你是专业的中英翻译与社交内容分析助手。只输出合法JSON对象，不要任何额外文字。"
    user_p = (
        "请处理以下推文，输出JSON对象，字段：\n"
        "- translated_text: 中文翻译\n"
        "- one_sentence_summary: 10-20字一句话核心观点\n"
        "- tags: 数组，2-3个中文标签\n\n"
        f"原文：{t.get('text', '')[:600]}"
    )
    data = _safe_json(_chat(sys_p, user_p, json_mode=True))
    t["translated_text"] = data.get("translated_text") or t.get("text", "")
    t["one_sentence_summary"] = data.get("one_sentence_summary") or "生成失败"
    t["tags"] = (data.get("tags") or [])[:3]
    return t


# ---------------------------------------------------------------- aggregate
def twitter_sentiment(tweets: list) -> str:
    if not tweets:
        return ""
    sys_p = "你是社交媒体舆论分析师。输出一段50-100字的中文分析，客观中立，不要列表，不要标题，不要前后客套话。"
    body = "\n".join(
        f"- 原文: {t.get('text', '')[:200]}\n  总结: {t.get('one_sentence_summary', '')}"
        for t in tweets[:10]
    )
    user_p = (
        "以下推文为今日AI话题热门内容。请分析整体舆论风向（主流情绪、讨论焦点、趋势），"
        "输出一段50-100字中文：\n\n" + body
    )
    out = _chat(sys_p, user_p)
    return out or "舆论分析生成失败"
