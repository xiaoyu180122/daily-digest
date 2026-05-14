"""
轻量 Google Translate 封装（免费，无需 API key）。
使用同步 httpx 调用 Google Translate 公共 AJAX 接口。
翻译结果持久化到 JSON 缓存文件，避免重复请求。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import httpx

_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-CN&dt=t&q={}"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"
_HAS_CJK = re.compile(r"[一-鿿]")

# 缓存：内存 + 文件
_cache: dict[str, str] = {}
_loaded = False


def _cache_path() -> Path:
    return Path(os.getenv("TRANSLATE_CACHE", "data/translate_cache.json"))


def _ensure_loaded():
    global _cache, _loaded
    if _loaded:
        return
    p = _cache_path()
    try:
        if p.exists():
            _cache = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        _cache = {}
    _loaded = True


def _save_cache():
    try:
        p = _cache_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        import sys
        print(f"  [translate] cache write failed: {e}", file=sys.stderr)


def translate(text: str, timeout: float = 10.0) -> str:
    """翻译英文为中文。包含中文或太短的文本跳过。"""
    if not text or len(text) < 4:
        return text

    _ensure_loaded()

    key = hashlib.md5(text.encode()).hexdigest()
    if key in _cache:
        return _cache[key]

    # 已含中文，不需要翻译
    if _HAS_CJK.search(text):
        _cache[key] = text
        return text

    target = text[:200]
    try:
        url = _TRANSLATE_URL.format(httpx.URL(target))
        resp = httpx.get(
            url, headers={"User-Agent": _UA},
            timeout=timeout, follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        result = "".join(part[0] for part in data[0] if part[0]) if data and data[0] else ""
        if result:
            _cache[key] = result
            _save_cache()
            return result
    except Exception:
        pass

    _cache[key] = text
    return text


def clear_cache():
    """清空翻译缓存（调试用）。"""
    global _cache, _loaded
    _cache = {}
    _loaded = False
    try:
        _cache_path().unlink(missing_ok=True)
    except Exception:
        pass
