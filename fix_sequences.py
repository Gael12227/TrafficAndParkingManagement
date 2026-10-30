"""
fix_sequences.py
----------------
Fixes Oracle Identity sequence CACHE gaps (IDs jump by 20 on app restart).

ROOT CAUSE
----------
Oracle Identity columns use an underlying system-generated sequence with
CACHE 20 by default. On every application restart, unused cached IDs are
LOST, so IDs jump:
    App start 1  -> IDs 1-20 allocated  -> only ID 1 used
    App restart  -> IDs 2-20 discarded
    App start 2  -> IDs 21-40 allocated -> first insert gets ID 21

ORA-32793 means ALTER SEQUENCE won't work on system-generated sequences.
The ONLY correct fix is to recreate the Identity column using:
    MODIFY <col> GENERATED ALWAYS AS IDENTITY (START WITH <next_val> CACHE 1)

This script does exactly that for every Identity column in the smartcity schema.

USAGE
-----
    venv\\Scripts\\python.exe fix_sequences.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "1521")
DB_SERVICE  = os.getenv("DB_SERVICE")

# Tables and their identity (auto-increment) columns
IDENTITY_COLUMNS = [
    ("USERS",          "USER_ID"),
    ("PARKING_ZONES",  "ZONE_ID"),
    ("RESERVATIONS",   "RES_ID"),
    ("CAMERAS",        "CAMERA_ID"),
    ("VIOLATIONS",     "VIOLATION_ID"),
    ("TICKETS",        "TICKET_ID"),
    ("APPEALS",        "APPEAL_ID"),
]


async def fix_sequences():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    url = (
        f"oracle+oracledb_async://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/?service_name={DB_SERVICE}"
    )
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        print("\n=== Oracle Identity Cache Fix ===\n")

        for table, col in IDENTITY_COLUMNS:
            try:
                # Get the current maximum value so we don't reset to 1
                result = await conn.execute(
                    text(f"SELECT NVL(MAX({col}), 0) FROM {table}")
                )
                max_val = result.scalar() or 0
                next_val = max_val + 1

                # Recreate the identity with CACHE 1 (no gaps on restart)
                ddl = (
                    f"ALTER TABLE {table} MODIFY {col} "
                    f"GENERATED ALWAYS AS IDENTITY "
                    f"(START WITH {next_val} INCREMENT BY 1 NOCACHE ORDER)"
                )
                await conn.execute(text(ddl))
                print(f"  [OK]  {table}.{col}  -> next={next_val}  NOCACHE ORDER")

            except Exception as e:
                print(f"  [FAIL]  {table}.{col}  -> {type(e).__name__}: {e}")

        print("\nDone.")
        print("From now on IDs will increment by 1 with NO gaps on restart.\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_sequences())
