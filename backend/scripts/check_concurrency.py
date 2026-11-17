"""PostgreSQL smoke test proving a ride row lock permits one assignment only."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Ride, User


def main():
    engine = get_engine()
    with Session(engine) as db:
        customer = User(
            phone="+919000000001", display_name="Concurrency customer", role="customer"
        )
        drivers = [
            User(
                phone=f"+91900000000{number}",
                display_name=f"Concurrency driver {number}",
                role="driver",
                driver_approved=True,
                vehicle_number=f"TN19TEST{number}",
            )
            for number in (2, 3)
        ]
        db.add_all([customer, *drivers])
        db.flush()
        ride = Ride(
            customer_id=customer.id,
            pickup="Lock test pickup",
            dropoff="Lock test drop-off",
            distance_tenths_km=10,
            estimated_fare_paise=6500,
            status="requested",
        )
        db.add(ride)
        db.commit()
        ride_id, driver_ids = ride.id, [driver.id for driver in drivers]

    barrier = Barrier(2)

    def claim(driver_id: int) -> bool:
        with Session(engine) as session, session.begin():
            barrier.wait()
            locked = session.scalar(
                select(Ride).where(Ride.id == ride_id).with_for_update()
            )
            if locked.driver_id is not None:
                return False
            locked.driver_id = driver_id
            locked.status = "accepted"
            return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, driver_ids))
    assert sorted(results) == [False, True], results
    with Session(engine) as db:
        assigned = db.get(Ride, ride_id)
        assert assigned.driver_id in driver_ids and assigned.status == "accepted"
    print("PostgreSQL row-lock concurrency check passed: one assignment committed.")


if __name__ == "__main__":
    main()
