# Async Payment Service

Микросервис принимает платежи, асинхронно обрабатывает их через эмулятор платёжного шлюза и отправляет результат на webhook клиента.

## Возможности

- асинхронный API на FastAPI;
- защита от повторного создания платежа через `Idempotency-Key`;
- атомарная запись платежа и события в outbox;
- публикация событий в RabbitMQ отдельным outbox relay;
- обработка платежа с вероятностью успеха 90%;
- три попытки обработки с экспоненциальной задержкой;
- перенос окончательно упавших сообщений в `payments.dead`;
- PostgreSQL и асинхронный SQLAlchemy 2.0;
- миграции Alembic;
- полное окружение в Docker Compose.

## Запуск

```bash
docker compose up --build
```

После запуска доступны:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- RabbitMQ Management: <http://localhost:15672>

Данные для RabbitMQ Management: `payments` / `payments`.

По умолчанию API использует ключ `test-api-key`. Для другого значения создайте `.env` из `.env.example` и задайте `API_KEY`.

## API

Создание платежа:

```bash
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: test-api-key' \
  -H 'Idempotency-Key: order-42' \
  -d '{
    "amount": "1250.50",
    "currency": "RUB",
    "description": "Order 42",
    "metadata": {"order_id": 42},
    "webhook_url": "https://webhook.site/replace-with-your-id"
  }'
```

Сервис отвечает `202 Accepted`:

```json
{
  "payment_id": "4513e10b-cab8-4c8e-bc98-2ee625794c53",
  "status": "pending",
  "created_at": "2026-10-07T20:00:00Z"
}
```

Получение платежа:

```bash
curl http://localhost:8000/api/v1/payments/4513e10b-cab8-4c8e-bc98-2ee625794c53 \
  -H 'X-API-Key: test-api-key'
```

Повторный запрос на создание с тем же `Idempotency-Key` вернёт ранее созданный платёж и не добавит новое событие в outbox.

## Как работает обработка

API сохраняет платёж со статусом `pending` и событие `payment.created` одной транзакцией. Outbox relay блокирует очередную неопубликованную запись через `FOR UPDATE SKIP LOCKED`, публикует её в `payments.new` и отмечает опубликованной только после подтверждения RabbitMQ.

Consumer ждёт 2–5 секунд, выбирает результат обработки и отправляет webhook. При ошибке вся обработка повторяется до трёх раз с задержками 1 и 2 секунды. После третьей ошибки событие попадает в `payments.dead`. Повторно доставленное событие не обрабатывает уже завершённый платёж.

## Проверка

```bash
python -m pip install -e '.[dev]'
pytest -q
docker compose ps
docker compose logs api consumer
```

Для проверки webhook удобно создать временный адрес на <https://webhook.site>, указать его в запросе и дождаться JSON с `payment_id`, `status` и `processed_at`.
