import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.models import OutboxEvent, Payment
from payment_service.schemas import PaymentCreate, PaymentDetails


async def create_payment(
    session: AsyncSession,
    data: PaymentCreate,
    idempotency_key: str,
) -> Payment:
    payment_id = uuid.uuid4()
    payment = Payment(
        id=payment_id,
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        payment_metadata=data.metadata,
        idempotency_key=idempotency_key,
        webhook_url=str(data.webhook_url),
    )
    event = OutboxEvent(
        aggregate_id=payment_id,
        event_type="payment.created",
        payload={"payment_id": str(payment_id), "attempt": 1},
    )
    session.add_all((payment, event))

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one()

    await session.refresh(payment)
    return payment


async def get_payment(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return await session.get(Payment, payment_id)


def to_details(payment: Payment) -> PaymentDetails:
    return PaymentDetails(
        id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.payment_metadata,
        status=payment.status,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
