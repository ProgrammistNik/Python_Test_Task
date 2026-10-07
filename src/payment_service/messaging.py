from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from payment_service.config import settings

payments_exchange = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)
dead_letter_exchange = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, durable=True)
payment_queue = RabbitQueue(
    "payments.new",
    routing_key="payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.failed",
    },
)
dead_letter_queue = RabbitQueue(
    "payments.dead",
    routing_key="payments.failed",
    durable=True,
)
broker = RabbitBroker(settings.rabbitmq_url)


async def declare_topology() -> None:
    declared_payments_exchange = await broker.declare_exchange(payments_exchange)
    declared_dead_letter_exchange = await broker.declare_exchange(dead_letter_exchange)
    declared_payment_queue = await broker.declare_queue(payment_queue)
    declared_dead_letter_queue = await broker.declare_queue(dead_letter_queue)
    await declared_payment_queue.bind(declared_payments_exchange, routing_key="payments.new")
    await declared_dead_letter_queue.bind(
        declared_dead_letter_exchange,
        routing_key="payments.failed",
    )
