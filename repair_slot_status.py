"""
repair_slot_status.py
---------------------
One-time repair: sets status='RESERVED' on any ParkingSlot that has an
existing Reservation in the DB, fixing slots that were created before the
slot-status update was added to create_reservation.

Run once after deploying the booking router fix:
    venv\\Scripts\\python.exe repair_slot_status.py
"""
import asyncio, os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()
url = (
    f"oracle+oracledb_async://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/?service_name={os.getenv('DB_SERVICE')}"
)

async def repair():
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT DISTINCT zone_id, slot_id FROM reservations")
        )
        rows = result.fetchall()
        print(f"\nFound {len(rows)} slot(s) with existing reservations.\n")
        for zone_id, slot_id in rows:
            await conn.execute(
                text(
                    "UPDATE parking_slots SET status='RESERVED' "
                    f"WHERE zone_id={zone_id} AND slot_id={slot_id}"
                )
            )
            print(f"  [OK] Zone {zone_id} / Slot {slot_id}  ->  RESERVED")
        print("\nDone. Admin dashboard will now show correct occupied/reserved count.\n")
    await engine.dispose()

asyncio.run(repair())
