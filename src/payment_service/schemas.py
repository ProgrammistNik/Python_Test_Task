import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from payment_service.models import Currency, PaymentStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Currency
    description: str = Field(min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: AnyHttpUrl


class PaymentCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime


class PaymentDetails(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None


class PaymentEvent(BaseModel):
    payment_id: uuid.UUID
    attempt: int = Field(default=1, ge=1)


class DeadLetterEvent(BaseModel):
    payment_id: uuid.UUID
    attempts: int
    error: str
    failed_at: datetime


class WebhookPayload(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
    processed_at: datetime
