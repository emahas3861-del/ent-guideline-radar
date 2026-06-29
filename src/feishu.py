from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.request


def _sign(timestamp: str, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(string_to_sign, b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_text_report(title: str, report: str) -> None:
    webhook = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("Missing FEISHU_WEBHOOK_URL")

    chunks = _split_text(f"{title}\n\n{report}", limit=15000)
    for idx, chunk in enumerate(chunks, start=1):
        payload = {
            "msg_type": "text",
            "content": {"text": chunk if len(chunks) == 1 else f"{chunk}\n\n({idx}/{len(chunks)})"},
        }
        secret = os.getenv("FEISHU_WEBHOOK_SECRET")
        if secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = _sign(timestamp, secret)

        req = urllib.request.Request(
            webhook,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body)
        if data.get("code") not in (0, None):
            raise RuntimeError(f"Feishu send failed: {body}")


def _split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    current = []
    size = 0
    for line in text.splitlines():
        extra = len(line) + 1
        if current and size + extra > limit:
            chunks.append("\n".join(current))
            current = [line]
            size = extra
        else:
            current.append(line)
            size += extra
    if current:
        chunks.append("\n".join(current))
    return chunks

