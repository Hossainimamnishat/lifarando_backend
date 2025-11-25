Backend service for the Lifarando food delivery ecosystem. Built with FastAPI, PostgreSQL, Alembic, Docker, and JWT authentication. Includes modules for user accounts, restaurants, menu items, orders, drivers, shifts, payments, and geo-based delivery logic.
📦 FOOD (Lifarando) Backend

A scalable FastAPI + PostgreSQL backend powering the Lifarando food delivery platform.
Includes full modules for authentication, restaurant management, menu inventory,
order processing, driver delivery system, shift tracking, geofencing, and payments.

Designed for production with Docker, async SQLAlchemy, Alembic migrations,
PyJWT authentication, and a clean service-layer architecture.

🚀 Features
🔐 Authentication & Users

Email/phone signup & login

Hashed passwords (bcrypt)

Access & refresh tokens (PyJWT)

Role support (customer, driver, admin)

🍽️ Restaurants & Menu

Restaurant registration

Valid license system

Opening/closing hours

Menu items (name, ingredients, price, image, quantity)

Business hours & availability

🛒 Orders & Cart

Add/remove items to cart

Price calculation: item price, service fee, delivery fee, subtotal

Pickup or delivery options

Delivery notes & tips

Order status workflow

🚴 Delivery & Drivers

Driver profile + vehicle type (car/bike)

Geo-boundaries for delivery zones

Distance calculation & limits:

Bicycle max 8 km

Car max 15 km

Shift system (start/end/time tracking)

Hourly pay + bonuses after 25 completed orders

💳 Payments

Online payments (PayPal, MasterCard, Bank)

Refunds if order is canceled

Restaurant commission

Rider per-km payout

🗄️ Tech Stack

FastAPI (async)

PostgreSQL

SQLAlchemy 2.0 async

Alembic (migrations)

Docker / Docker Compose

PyJWT (secure JWT auth)

Pydantic v2

asyncpg
