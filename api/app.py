from __future__ import annotations

import json
import os
import threading
import urllib.parse
import urllib.request
from typing import Any

from fastapi import FastAPI, Request

from src.query_bot import answer_query, help_text

app = FastAPI(title="ENT Guideline Radar Feishu Bot")


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ent-guideline-radar"}


@app.post("/feishu/events")
async def feishu_events(request: Request) -> dict[str, Any]:
    payload = await request.json()

    if payload.get("challenge"):
        return {"challenge": payload.get("challenge")}
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    if not verify_token(payload):
        return {"code": 403, "msg": "verification token mismatch"}

    event = payload.get("event") or {}
    header = payload.get("header") or {}
    event_type = header.get("event_type") or payload.get("type")

    if event_type == "im.message.receive_v1" or "message" in event:
        message = event.get("message") or {}
        chat_id = message.get("chat_id")
        text = extract_text(message.get("content"))
        if chat_id:
            threading.Thread(target=handle_message, args=(chat_id, text), daemon=True).start()

    return {"code": 0, "msg": "ok"}


def verify_token(payload: dict[str, Any]) -> bool:
    expected = os.getenv("FEISHU_VERIFICATION_TOKEN", "").strip()
    if not expected:
        return True
    token = payload.get("token") or (payload.get("header") or {}).get("token")
    return token == expected


def extract_text(content: Any) -> str:
    if isinstance(content, dict):
        return str(content.get("text", "")).strip()
    if isinstance(content, str):
        try:
            data = json.loads(content)
            return str(data.get("text", content)).strip()
        except json.JSONDecodeError:
            return content.strip()
    return ""


def handle_message(chat_id: str, text: str) -> None:
    try:
        answer = answer_query(text)
    except Exception as exc:
        answer = f"查询失败：{exc}\n\n" + help_text()
    send_feishu_message(chat_id, answer)


def get_tenant_access_token() -> str:
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise RuntimeError("Missing FEISHU_APP_ID or FEISHU_APP_SECRET")
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"Failed to get tenant_access_token: {data}")
    return token


def send_feishu_message(chat_id: str, text: str) -> None:
    token = get_tenant_access_token()
    for chunk in split_text(text, 12000):
        body = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": chunk}, ensure_ascii=False),
        }
        url = "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode({"receive_id_type": "chat_id"})
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("code") != 0:
            raise RuntimeError(f"Feishu message send failed: {result}")


def split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
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