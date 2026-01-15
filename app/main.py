from fastapi import FastAPI, Request, Header, HTTPException
from datetime import datetime
import sqlite3
import hmac
import hashlib

from app.config import DATABASE_URL, WEBHOOK_SECRET
from app.models import WebhookMessage
from app.storage import init_db, get_conn
from app.logging_utils import log_request
from app.metrics import record_http, record_webhook, render_metrics

app = FastAPI()

# -------- LOGGING MIDDLEWARE --------
app.middleware("http")(log_request)


# -------- STARTUP --------
@app.on_event("startup")
def startup():
    if not DATABASE_URL or not WEBHOOK_SECRET:
        return
    init_db()


# -------- UTILS --------
def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    computed = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


# -------- HEALTH --------
@app.get("/health/live")
def live():
    return {"status": "alive"}


@app.get("/health/ready")
def ready():
    if not DATABASE_URL or not WEBHOOK_SECRET:
        raise HTTPException(status_code=503)

    try:
        conn = get_conn()
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        raise HTTPException(status_code=503)

    return {"status": "ready"}


# -------- WEBHOOK --------
@app.post("/webhook")
async def webhook(request: Request, x_signature: str = Header(None)):
    body = await request.body()

    if not x_signature or not verify_signature(WEBHOOK_SECRET, body, x_signature):
        record_http("/webhook", 401)
        record_webhook("invalid_signature")
        raise HTTPException(status_code=401, detail="invalid signature")

    data = await request.json()
    msg = WebhookMessage(**data)

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
            (
                msg.message_id,
                msg.from_msisdn,
                msg.to_msisdn,
                msg.ts,
                msg.text,
                datetime.utcnow().isoformat() + "Z"
            )
        )
        conn.commit()
        record_webhook("created")
    except sqlite3.IntegrityError:
        record_webhook("duplicate")
    finally:
        conn.close()

    record_http("/webhook", 200)
    return {"status": "ok"}


# -------- MESSAGES --------
@app.get("/messages")
def list_messages(
    limit: int = 50,
    offset: int = 0,
    from_: str = None,
    since: str = None,
    q: str = None
):
    conn = get_conn()
    conditions = []
    params = []

    if from_:
        conditions.append("from_msisdn = ?")
        params.append(from_)
    if since:
        conditions.append("ts >= ?")
        params.append(since)
    if q:
        conditions.append("LOWER(text) LIKE ?")
        params.append(f"%{q.lower()}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = conn.execute(
        f"SELECT COUNT(*) FROM messages {where}",
        params
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        SELECT message_id,
               from_msisdn as 'from',
               to_msisdn as 'to',
               ts,
               text
        FROM messages
        {where}
        ORDER BY ts ASC, message_id ASC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset]
    ).fetchall()

    conn.close()
    record_http("/messages", 200)

    return {
        "data": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset
    }


# -------- STATS --------
@app.get("/stats")
def stats():
    conn = get_conn()

    total = conn.execute(
        "SELECT COUNT(*) FROM messages"
    ).fetchone()[0]

    senders = conn.execute(
        """
        SELECT from_msisdn as 'from', COUNT(*) as count
        FROM messages
        GROUP BY from_msisdn
        ORDER BY count DESC
        LIMIT 10
        """
    ).fetchall()

    first_ts, last_ts = conn.execute(
        "SELECT MIN(ts), MAX(ts) FROM messages"
    ).fetchone()

    conn.close()
    record_http("/stats", 200)

    return {
        "total_messages": total,
        "senders_count": len(senders),
        "messages_per_sender": [dict(s) for s in senders],
        "first_message_ts": first_ts,
        "last_message_ts": last_ts
    }


# -------- METRICS --------
@app.get("/metrics")
def metrics():
    return render_metrics()
