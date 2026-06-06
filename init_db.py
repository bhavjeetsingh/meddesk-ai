"""
CareFirst Medical Center - Database Initialization Script
Run this once to create tables and seed default users.
"""
import asyncio
from core.database import init_db, seed_data
from loguru import logger


async def main():
    logger.info("Initializing database...")
    await init_db()
    logger.info("Seeding default data...")
    await seed_data()
    logger.info("Database setup complete!")


if __name__ == "__main__":
    asyncio.run(main())
