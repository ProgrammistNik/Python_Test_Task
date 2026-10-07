import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from payment_service.config import settings
from payment_service.database import session_factory
from payment_service.messaging import broker, payment_queue, payments_exchange
from payment_service.models import OutboxEvent

logger = logging.getLogger(__name__)


async def publish_next_event() -> bool:
    async with session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            event = result.scalar_one_or_none()
            if event is None:
                return False

            try:
                await broker.publish(
                    event.payload,
                    queue=payment_queue,
                    exchange=payments_exchange,
                )
            except Exception as exc:
                event.attempts += 1
                event.last_error = str(exc)
                logger.exception("Outbox event %s could not be published", event.id)
                return False

            event.attempts += 1
            event.last_error = None
            event.published_at = datetime.now(UTC)
            return True


async def run_outbox_relay() -> None:
    while True:
        published = await publish_next_event()
        if not published:
            await asyncio.sleep(settings.outbox_poll_interval)
