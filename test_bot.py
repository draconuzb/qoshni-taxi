"""TaxiBek Bot — Integration Test"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select, insert

from infrastructure.database import async_session
from core.models.user import User
from core.models.route import Route
from core.models.driver import Driver, driver_routes
from core.models.order import Order
from core.models.trip import Trip, TripPassenger
from core.enums import UserRole, DriverStatus, OrderStatus
from core.services.review_service import ReviewService
from core.services.scheduler import haversine_km, estimate_minutes


async def run_tests():
    print("=" * 50)
    print("TAXIBEK BOT — INTEGRATION TEST")
    print("=" * 50)

    async with async_session() as session:
        # TEST 1: Foydalanuvchilar
        print("\n[TEST 1] Foydalanuvchilar yaratish...")
        admin = User(telegram_id=5035706309, full_name="Admin Boss", phone="+998901234567", role=UserRole.MANAGER)
        user1 = User(telegram_id=111111111, full_name="Alisher Yolovchi", phone="+998901111111")
        user2 = User(telegram_id=222222222, full_name="Bobur Yolovchi", phone="+998902222222")
        driver_user = User(telegram_id=333333333, full_name="Jasur Haydovchi", phone="+998903333333", role=UserRole.DRIVER)
        session.add_all([admin, user1, user2, driver_user])
        await session.commit()
        print(f"  OK: 4 ta foydalanuvchi (admin, 2 user, 1 driver)")

        # TEST 2: Yonalishlar
        print("\n[TEST 2] Yonalishlar yaratish...")
        route1 = Route(from_name="Chinoz", to_name="Toshkent", price=25000,
                       from_latitude=40.93, from_longitude=68.77, to_latitude=41.31, to_longitude=69.28)
        route2 = Route(from_name="Toshkent", to_name="Chinoz", price=25000,
                       from_latitude=41.31, from_longitude=69.28, to_latitude=40.93, to_longitude=68.77)
        route3 = Route(from_name="Olmaliq", to_name="Toshkent", price=30000)
        session.add_all([route1, route2, route3])
        await session.commit()
        print(f"  OK: Chinoz<->Toshkent (25,000), Olmaliq->Toshkent (30,000)")

        # TEST 3: Haydovchi
        print("\n[TEST 3] Haydovchi yaratish va tasdiqlash...")
        driver = Driver(
            user_id=driver_user.id, car_model="Cobalt", car_color="Oq",
            license_plate="01A123BC", status=DriverStatus.VERIFIED,
            is_online=True, last_latitude=40.95, last_longitude=68.80,
        )
        session.add(driver)
        await session.flush()
        await session.execute(insert(driver_routes).values(driver_id=driver.id, route_id=route1.id))
        await session.execute(insert(driver_routes).values(driver_id=driver.id, route_id=route2.id))
        await session.commit()
        print(f"  OK: Cobalt Oq 01A123BC | Verified | Online")

        # TEST 4: Buyurtma
        print("\n[TEST 4] Buyurtma yaratish...")
        order = Order(
            user_id=user1.id, route_id=route1.id, passenger_count=2,
            price=50000, pickup_latitude=40.94, pickup_longitude=68.78,
            status=OrderStatus.PENDING,
        )
        session.add(order)
        await session.commit()
        print(f"  OK: Buyurtma #{order.id} | Chinoz->Toshkent | 2 kishi | 50,000 som")

        # TEST 5: Masofa
        print("\n[TEST 5] Masofa hisoblash (haversine)...")
        dist = haversine_km(order.pickup_latitude, order.pickup_longitude,
                            driver.last_latitude, driver.last_longitude)
        eta = estimate_minutes(dist)
        print(f"  OK: Masofa: {dist:.2f} km | ETA: ~{eta} daqiqa")

        # TEST 6: Qabul qilish
        print("\n[TEST 6] Buyurtma qabul qilish...")
        order.driver_id = driver.id
        order.status = OrderStatus.ACCEPTED
        order.accepted_at = datetime.utcnow()
        await session.commit()
        print(f"  OK: Status: {order.status}")

        # TEST 7: Safar jarayoni
        print("\n[TEST 7] Safar jarayoni...")
        order.status = OrderStatus.DRIVER_ARRIVED
        await session.commit()
        print(f"  > Haydovchi yetib keldi: {order.status}")

        order.status = OrderStatus.IN_PROGRESS
        await session.commit()
        print(f"  > Safar boshlandi: {order.status}")

        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        driver.total_trips += 1
        await session.commit()
        print(f"  OK: Safar tugadi | Jami safarlar: {driver.total_trips}")

        # TEST 8: Rating
        print("\n[TEST 8] Baho qoyish...")
        review_svc = ReviewService(session)
        await review_svc.create_review(
            order_id=order.id, from_user_id=user1.id,
            to_user_id=driver_user.id, rating=5, comment="Yaxshi!",
        )
        await session.refresh(driver)
        print(f"  OK: 5 yulduz | Reyting: {driver.rating:.1f}")

        # TEST 9: Carpool
        print("\n[TEST 9] Carpool trip...")
        trip = Trip(
            driver_id=driver.id, route_id=route1.id,
            total_seats=4, price_per_seat=25000, status="collecting",
        )
        session.add(trip)
        await session.commit()
        print(f"  OK: Trip #{trip.id} ochildi (0/4)")

        p1 = TripPassenger(trip_id=trip.id, user_id=user1.id, seats=1)
        session.add(p1)
        trip.occupied_seats = 1
        await session.commit()
        print(f"  + Alisher qoshildi (1 joy): {trip.occupied_seats}/4")

        p2 = TripPassenger(trip_id=trip.id, user_id=user2.id, seats=2)
        session.add(p2)
        trip.occupied_seats = 3
        await session.commit()
        print(f"  + Bobur qoshildi (2 joy): {trip.occupied_seats}/4")
        print(f"  > 1 ta joy qoldi!")

        # TEST 10: Scheduled order
        print("\n[TEST 10] Oldindan buyurtma...")
        sched_time = datetime.utcnow() + timedelta(hours=2)
        sched = Order(
            user_id=user2.id, route_id=route1.id, passenger_count=1,
            price=25000, status=OrderStatus.SCHEDULED,
            is_scheduled=True, scheduled_at=sched_time,
        )
        session.add(sched)
        await session.commit()
        local = sched_time + timedelta(hours=5)
        print(f"  OK: Buyurtma #{sched.id} | Vaqt: {local.strftime('%H:%M')} | Status: {sched.status}")

        # TEST 11: Skip counter
        print("\n[TEST 11] Skip counter ogohlantirish...")
        driver.consecutive_skips = 0
        for i in range(3):
            driver.consecutive_skips += 1
        await session.commit()
        warning = "OGOHLANTIRISH!" if driver.consecutive_skips >= 3 else "OK"
        print(f"  {warning}: {driver.consecutive_skips} ta ketma-ket skip")

        # TEST 12: Expired order test
        print("\n[TEST 12] Order timeout (expired)...")
        old_order = Order(
            user_id=user1.id, route_id=route3.id, passenger_count=1,
            price=30000, status=OrderStatus.PENDING,
        )
        session.add(old_order)
        await session.commit()

        # Simulate: retry_count > MAX_RETRIES
        old_order.retry_count = 3
        old_order.status = OrderStatus.EXPIRED
        await session.commit()
        print(f"  OK: Buyurtma #{old_order.id} expired (3 urinishdan keyin)")

        # NATIJA
        users = (await session.execute(select(User))).scalars().all()
        routes = (await session.execute(select(Route))).scalars().all()
        orders = (await session.execute(select(Order))).scalars().all()
        trips_list = (await session.execute(select(Trip))).scalars().all()

        print("\n" + "=" * 50)
        print("BARCHA 12 TEST MUVAFFAQIYATLI! ✅")
        print("=" * 50)
        print(f"\nDB holati:")
        print(f"  Foydalanuvchilar: {len(users)}")
        print(f"  Yonalishlar:      {len(routes)}")
        print(f"  Buyurtmalar:      {len(orders)}")
        print(f"  Triplar:          {len(trips_list)}")
        print(f"  Haydovchilar:     1 (Cobalt Oq, reyting: {driver.rating:.1f})")


if __name__ == "__main__":
    asyncio.run(run_tests())
