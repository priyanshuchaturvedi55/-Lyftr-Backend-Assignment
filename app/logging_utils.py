import json
import time
import uuid
from datetime import datetime
from fastapi import Request

async def log_request(request: Request, call_next):
    start = time.time()
    request_id = str(uuid.uuid4())

    response = await call_next(request)
    latency = int((time.time() - start) * 1000)

    log = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": latency
    }

    print(json.dumps(log))
    return response
