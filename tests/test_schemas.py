from decimal import Decimal

import pytest
from pydantic import ValidationError

from payment_service.models import Currency
from payment_service.schemas import PaymentCreate


def test_payment_create_accepts_valid_data() -> None:
    payment = PaymentCreate(
        amount="1250.50",
        currency="RUB",
        description="Order 42",
        metadata={"order_id": 42},
        webhook_url="https://example.com/webhooks/payments",
    )

    assert payment.amount == Decimal("1250.50")
    assert payment.currency is Currency.RUB


@pytest.mark.parametrize("amount", ["0", "-1", "1.999"])
def test_payment_create_rejects_invalid_amount(amount: str) -> None:
    with pytest.raises(ValidationError):
        PaymentCreate(
            amount=amount,
            currency="USD",
            description="Order 42",
            webhook_url="https://example.com/webhooks/payments",
        )
