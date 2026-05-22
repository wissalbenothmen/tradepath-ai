"""Live API probe: DeepInfra Whisper Large v3, OpenAI GPT-4.1 Mini, Azure DI.

Project-agnostic — reads env vars directly so it works across projects
regardless of whether their Settings class uses UPPER or lowercase fields.

Run from any project's backend folder:
    python probe_apis.py

Reports OK / FAIL / SKIP with one-line reason. Keys are read from the
project's `.env` and never printed.
"""
from __future__ import annotations

import asyncio
import io
import os
import tempfile
import time
import wave
from pathlib import Path

# Load .env from the script's directory (each project's backend has one)
from dotenv import load_dotenv  # type: ignore
load_dotenv(Path(__file__).parent / ".env")

import httpx
import openai


def _env(name: str) -> str:
    """Case-insensitive env lookup."""
    for variant in (name, name.lower(), name.upper()):
        v = os.environ.get(variant)
        if v:
            return v
    return ""


def _tiny_wav() -> bytes:
    """1-second 8 kHz mono silence WAV — minimum payload for Whisper."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 8000)
    return buf.getvalue()


async def probe_deepinfra() -> dict:
    key = _env("DEEPINFRA_API_KEY")
    if not key:
        return {"name": "DeepInfra Whisper Large v3", "status": "SKIP", "reason": "no DEEPINFRA_API_KEY"}
    base_url = _env("DEEPINFRA_BASE_URL") or "https://api.deepinfra.com/v1/openai"
    model = _env("WHISPER_MODEL") or "openai/whisper-large-v3"
    client = openai.AsyncOpenAI(api_key=key, base_url=base_url)
    t0 = time.perf_counter()
    audio_bytes = _tiny_wav()
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            audio_path = f.name
        try:
            with open(audio_path, "rb") as fh:
                resp = await client.audio.transcriptions.create(
                    model=model, file=fh, language="en", temperature=0.0,
                )
            ms = (time.perf_counter() - t0) * 1000
            text = getattr(resp, "text", "") or ""
            return {
                "name": "DeepInfra Whisper Large v3",
                "status": "OK",
                "model": model,
                "latency_ms": int(ms),
                "transcript_chars": len(text),
            }
        finally:
            try:
                os.unlink(audio_path)
            except OSError:
                pass
    except openai.APIStatusError as e:
        return {"name": "DeepInfra Whisper Large v3", "status": "FAIL",
                "http_status": e.status_code, "reason": _summarize_error(e)}
    except Exception as e:
        return {"name": "DeepInfra Whisper Large v3", "status": "FAIL", "reason": str(e)[:200]}


async def probe_openai_gpt() -> dict:
    key = _env("OPENAI_API_KEY")
    if not key:
        return {"name": "OpenAI GPT", "status": "SKIP", "reason": "no OPENAI_API_KEY"}
    model = _env("OPENAI_MODEL") or "gpt-4.1-mini-2025-04-14"
    client = openai.AsyncOpenAI(api_key=key)
    t0 = time.perf_counter()
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with just OK"}],
            temperature=0.0,
            max_tokens=4,
        )
        ms = (time.perf_counter() - t0) * 1000
        text = resp.choices[0].message.content or ""
        return {
            "name": "OpenAI GPT",
            "status": "OK",
            "model": model,
            "latency_ms": int(ms),
            "reply": text.strip(),
        }
    except openai.APIStatusError as e:
        return {"name": "OpenAI GPT", "status": "FAIL",
                "http_status": e.status_code, "reason": _summarize_error(e)}
    except Exception as e:
        return {"name": "OpenAI GPT", "status": "FAIL", "reason": str(e)[:200]}


async def probe_azure_di() -> dict:
    endpoint = _env("AZURE_DI_ENDPOINT")
    key = _env("AZURE_DI_KEY")
    if not endpoint or not key:
        return {"name": "Azure Document Intelligence", "status": "SKIP", "reason": "missing AZURE_DI_*"}
    base = endpoint.rstrip("/")
    url = f"{base}/documentintelligence/documentModels?api-version=2024-11-30"
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, headers={"Ocp-Apim-Subscription-Key": key})
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            n = len(r.json().get("value", []))
            return {"name": "Azure Document Intelligence", "status": "OK",
                    "latency_ms": int(ms), "model_count": n}
        url_fallback = f"{base}/formrecognizer/documentModels?api-version=2023-07-31"
        async with httpx.AsyncClient(timeout=15.0) as c:
            r2 = await c.get(url_fallback, headers={"Ocp-Apim-Subscription-Key": key})
        if r2.status_code == 200:
            n = len(r2.json().get("value", []))
            return {"name": "Azure Document Intelligence", "status": "OK",
                    "latency_ms": int(ms), "model_count": n,
                    "api_version": "2023-07-31 (fallback)"}
        return {"name": "Azure Document Intelligence", "status": "FAIL",
                "http_status": r.status_code, "fallback_http_status": r2.status_code,
                "reason": (r.text or "")[:200]}
    except Exception as e:
        return {"name": "Azure Document Intelligence", "status": "FAIL", "reason": str(e)[:200]}


def _summarize_error(e: openai.APIStatusError) -> str:
    try:
        body = e.body or {}
        if isinstance(body, dict):
            inner = body.get("error") or body.get("detail") or body
            if isinstance(inner, dict):
                msg = inner.get("message") or inner.get("error") or str(inner)
            else:
                msg = str(inner)
        else:
            msg = str(body)
    except Exception:
        msg = str(e)
    return msg[:300]


async def main() -> int:
    results = await asyncio.gather(probe_deepinfra(), probe_openai_gpt(), probe_azure_di())
    print("\n=== API PROBE RESULTS ===")
    for r in results:
        mark = {"OK": "[OK]", "FAIL": "[X ]", "SKIP": "[--]"}.get(r.get("status"), "[? ]")
        line = f"{mark} {r['name']}"
        extras = []
        for k in ("model", "model_count", "latency_ms", "http_status",
                  "fallback_http_status", "transcript_chars", "reply", "api_version"):
            if k in r:
                extras.append(f"{k}={r[k]}")
        if r.get("status") == "FAIL" and r.get("reason"):
            extras.append(f"reason={r['reason']}")
        if extras:
            line += "  " + " · ".join(extras)
        print(line)
    print()
    return 0 if all(r["status"] == "OK" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
