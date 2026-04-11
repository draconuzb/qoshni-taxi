# TaxiBek — Setup Guide

## Tez ishga tushirish (3 qadam)

### 1. Python kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2. .env faylni sozlash
```bash
cp .env.example .env
```
`.env` faylni ochib quyidagilarni to'ldiring:
```
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=[your_telegram_id]
```

> Telegram ID bilish uchun botga `/myid` yuboring

### 3. Botni ishga tushirish
```bash
python main.py
```

---

## Birinchi sozlash

1. Telegram da botga `/start` yuboring — ro'yxatdan o'ting
2. `/admin` — admin panel ochiladi
3. `/role YOUR_TELEGRAM_ID` — o'zingizni Manager qiling
4. `/manager` — Manager panel
5. Yo'nalish qo'shing (masalan: Chinoz → Toshkent, 25000 so'm)

---

## Talablar

- Python 3.10+
- pip

## Texnologiyalar

- **aiogram 3.15** — Telegram Bot Framework
- **SQLAlchemy 2.0** — ORM (SQLite)
- **aiosqlite** — Async SQLite
- **pydantic-settings** — Config management

## Loyiha strukturasi

```
taxibek/
├── main.py                  # Entry point
├── bot/
│   ├── handlers/
│   │   ├── user/            # Yo'lovchi (start, order, trip, rating)
│   │   ├── driver/          # Haydovchi (registration, orders, trip)
│   │   ├── dispatcher/      # Dispatcher panel
│   │   ├── manager/         # Manager panel (routes, drivers, stats)
│   │   └── admin.py         # Admin buyruqlari
│   ├── keyboards/
│   │   └── inline.py        # Barcha inline tugmalar
│   ├── middlewares/          # DB session, Auth
│   ├── states/               # FSM holatlar
│   └── filters/              # Role filter
├── core/
│   ├── models/               # User, Driver, Route, Order, Trip, Review
│   ├── services/             # Order, Review, Scheduler
│   ├── repositories/         # CRUD
│   └── enums.py              # Rollar, Statuslar
├── infrastructure/           # Config, Database, Cache
├── .env.example
├── requirements.txt
└── docker-compose.yml        # PostgreSQL + Redis (production uchun)
```

## Xususiyatlar

- Inline tugmalar bilan premium UX
- Carpool (joy to'plash) tizimi
- Oldindan buyurtma (scheduled)
- Eng yaqin haydovchi aniqlash (geo)
- Realtime bildirishnomalar
- 5 daqiqada javob bo'lmasa avtomatik qayta yuborish
- Haydovchi skip counter + ogohlantirish
- Live location haydovchiga forward
- Rating tizimi (1-5 yulduz)
- Admin / Manager / Dispatcher / Driver / User rollari
