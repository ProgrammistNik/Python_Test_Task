import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime

import httpx
from faststream import FastStream
from sqlalchemy import select

from payment_service.config import settings
from payment_service.database import session_factory
from payment_service.messaging import (
    broker,
    dead_letter_exchange,
    dead_letter_queue,
    declare_topology,
    payment_queue,
    payments_exchange,
)
from payment_service.models import Payment, PaymentStatus
from payment_service.schemas import DeadLetterEvent, PaymentEvent, WebhookPayload

logger = logging.getLogger(__name__)
app = FastStream(broker)


@app.after_startup
async def setup() -> None:
    await declare_topology()


async def process_payment(payment_id: uuid.UUID) -> None:
    await asyncio.sleep(random.uniform(settings.processing_delay_min, settings.processing_delay_max))

    async with session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id).with_for_update()
            )
            payment = result.scalar_one_or_none()
            if payment is None:
                raise LookupError(f"Payment {payment_id} not found")
            if payment.status is not PaymentStatus.PENDING:
                return

            payment.status = (
                PaymentStatus.SUCCEEDED if random.random() < 0.9 else PaymentStatus.FAILED
            )
            payment.processed_at = datetime.now(UTC)
            webhook = WebhookPayload(
                payment_id=payment.id,
                status=payment.status,
                processed_at=payment.processed_at,
            )

            async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
                response = await client.post(payment.webhook_url, json=webhook.model_dump(mode="json"))
                response.raise_for_status()


@broker.subscriber(payment_queue, payments_exchange)
async def consume_payment(event: PaymentEvent) -> None:
    try:
        await process_payment(event.payment_id)
    except Exception as exc:
        if event.attempt >= 3:
            dead_event = DeadLetterEvent(
                payment_id=event.payment_id,
                attempts=event.attempt,
                error=str(exc),
                failed_at=datetime.now(UTC),
            )
            await broker.publish(
                dead_event.model_dump(mode="json"),
                queue=dead_letter_queue,
                exchange=dead_letter_exchange,
            )
            logger.exception("Payment %s moved to the dead-letter queue", event.payment_id)
            return

        await asyncio.sleep(2 ** (event.attempt - 1))
        retry_event = event.model_copy(update={"attempt": event.attempt + 1})
        await broker.publish(
            retry_event.model_dump(mode="json"),
            queue=payment_queue,
            exchange=payments_exchange,
        )
        logger.warning("Payment %s scheduled for retry %s", event.payment_id, retry_event.attempt)
