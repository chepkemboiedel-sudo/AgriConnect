"""FastAPI application: the single integrated boundary for AgriConnect.

Serves the customer chat UI, the staff inbox UI, and the JSON API. Every
request that touches tenant data goes through ``require_tenant`` /
``require_conversation``, which is where tenant isolation is enforced.
"""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, config, db

app = FastAPI(title="AgriConnect AI", version="0.1.0")


@app.on_event("startup")
def _ensure_db() -> None:
    db.init_db(reset=False)


# ---------------------------------------------------------------------------
# Tenant boundary helpers
# ---------------------------------------------------------------------------
def require_tenant(tenant: str | None) -> str:
    """Validate the tenant id. This is the 'verify tenant access' boundary."""
    if not tenant:
        raise HTTPException(status_code=400, detail="Missing tenant")
    conn = db.get_conn()
    try:
        if not db.tenant_exists(conn, tenant):
            raise HTTPException(status_code=404, detail="Unknown tenant")
    finally:
        conn.close()
    return tenant


def require_conversation(tenant: str, conversation_id: int) -> dict:
    """Fetch a conversation, refusing cross-tenant access with 403."""
    convo = db.get_conversation(tenant, conversation_id)
    if convo is None:
        # Exists under another tenant? Still a 403 -> no information leak.
        raise HTTPException(status_code=403, detail="Not authorized for this conversation")
    return convo


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class NewConversation(BaseModel):
    tenant: str
    customer_name: str = "Guest"


class CustomerMessage(BaseModel):
    tenant: str
    text: str


class StaffReply(BaseModel):
    tenant: str
    staff_name: str = "Staff"
    text: str


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "provider": config.PROVIDER}


@app.get("/api/tenants")
def tenants() -> list[dict]:
    return db.list_tenants()


@app.post("/api/conversations")
def new_conversation(body: NewConversation) -> dict:
    tenant = require_tenant(body.tenant)
    cid = db.create_conversation(tenant, body.customer_name.strip() or "Guest")
    return {"conversation_id": cid, "tenant": tenant, "status": "bot"}


@app.get("/api/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: int, tenant: str) -> dict:
    tenant = require_tenant(tenant)
    convo = require_conversation(tenant, conversation_id)
    return {"status": convo["status"], "messages": db.get_messages(tenant, conversation_id)}


@app.post("/api/conversations/{conversation_id}/message")
def post_message(conversation_id: int, body: CustomerMessage) -> dict:
    tenant = require_tenant(body.tenant)
    require_conversation(tenant, conversation_id)
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    reply = agent.run_agent(tenant, conversation_id, text)
    convo = db.get_conversation(tenant, conversation_id)
    return {"reply": reply, "status": convo["status"]}


# ---- Staff inbox ----------------------------------------------------------
@app.get("/api/inbox")
def inbox(tenant: str) -> list[dict]:
    tenant = require_tenant(tenant)
    return db.inbox_conversations(tenant)


@app.get("/api/inbox/{conversation_id}")
def inbox_detail(conversation_id: int, tenant: str) -> dict:
    tenant = require_tenant(tenant)
    convo = require_conversation(tenant, conversation_id)
    messages = db.get_messages(tenant, conversation_id)
    # Surface the evidence the assistant had, for the staff member.
    context_sources: list[dict] = []
    reason = ""
    for m in messages:
        meta = m.get("meta") or {}
        if meta.get("sources"):
            context_sources = meta["sources"]
        if meta.get("reason"):
            reason = meta["reason"]
    return {
        "conversation": convo,
        "messages": messages,
        "handoff_reason": reason,
        "assistant_evidence": context_sources,
    }


@app.post("/api/inbox/{conversation_id}/reply")
def inbox_reply(conversation_id: int, body: StaffReply) -> dict:
    tenant = require_tenant(body.tenant)
    require_conversation(tenant, conversation_id)
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty reply")
    msg = db.add_message(tenant, conversation_id, "staff", text,
                         meta={"staff_name": body.staff_name})
    db.set_conversation_status(tenant, conversation_id, "staff")
    return {"reply": msg, "status": "staff"}


# ---------------------------------------------------------------------------
# Static UI
# ---------------------------------------------------------------------------
STATIC = Path(config.STATIC_DIR)


@app.get("/")
def chat_ui() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/inbox")
def inbox_ui() -> FileResponse:
    return FileResponse(STATIC / "inbox.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
