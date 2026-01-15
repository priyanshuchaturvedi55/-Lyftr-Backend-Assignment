from pydantic import BaseModel, Field
from typing import Optional

class WebhookMessage(BaseModel):
    message_id: str
    from_msisdn: str = Field(..., alias="from")
    to_msisdn: str = Field(..., alias="to")
    ts: str
    text: Optional[str] = Field(None, max_length=4096)
