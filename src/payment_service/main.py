import asyncio
import uuid
from contextlib import asynccontextmanager, suppress
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.auth import require_api_key
from payment_service.database import get_session
from payment_service.messaging import broker, declare_topology
from payment_service.outbox import run_outbox_relay
from payment_service.schemas import PaymentCreate, PaymentCreated, PaymentDetails
from payment_service.service import create_payment, get_payment, to_details


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with broker:
        await declare_topology()
        relay = asyncio.create_task(run_outbox_relay())
        try:
            yield
        finally:
            relay.cancel()
            with suppress(asyncio.CancelledError):
                await relay


app = FastAPI(
    title="Payment Processing Service",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
)


@app.post(
    "/api/v1/payments",
    response_model=PaymentCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_payment_endpoint(
    data: PaymentCreate,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentCreated:
    payment = await create_payment(session, data, idempotency_key)
    return PaymentCreated(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@app.get("/api/v1/payments/{payment_id}", response_model=PaymentDetails)
async def get_payment_endpoint(
    payment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentDetails:
    payment = await get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return to_details(payment)
