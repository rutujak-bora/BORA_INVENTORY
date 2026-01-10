from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from motor.motor_asyncio import AsyncIOMotorClient
import os
from contextlib import asynccontextmanager
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load .env file first (important for uvicorn --reload child processes)
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Validate required environment variables
required_env_vars = {
    'MONGO_URL': 'MongoDB connection URL',
    'DB_NAME': 'MongoDB database name'
}

for var_name, description in required_env_vars.items():
    if not os.environ.get(var_name):
        print(f"ERROR: Missing required environment variable: {var_name} ({description})", file=sys.stderr)
        print(f"Please set {var_name} in your .env file or environment", file=sys.stderr)
        sys.exit(1)

# PostgreSQL setup (Optional - only if POSTGRES_URL is provided)
POSTGRES_URL = os.environ.get('POSTGRES_URL')
if POSTGRES_URL:
    POSTGRES_URL = POSTGRES_URL.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(POSTGRES_URL, echo=False, future=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
else:
    # PostgreSQL is optional in this application
    engine = None
    AsyncSessionLocal = None

Base = declarative_base()

# MongoDB setup (Required)
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')

try:
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    mongo_db = mongo_client[DB_NAME]
    print(f"MongoDB connection initialized: Database={DB_NAME}")
except Exception as e:
    print(f"ERROR: Failed to initialize MongoDB connection: {e}", file=sys.stderr)
    sys.exit(1)

# Dependency to get PostgreSQL session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Dependency to get MongoDB
async def get_mongo_db():
    return mongo_db
