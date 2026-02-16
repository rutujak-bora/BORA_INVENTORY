import asyncio
import sys
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import User, UserRole, Base
from auth import get_password_hash
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Get PostgreSQL URL
POSTGRES_URL = os.environ.get('POSTGRES_URL', 'postgresql://bora_user:bora_password@localhost:5432/bora_inventory')
POSTGRES_URL = POSTGRES_URL.replace('postgresql://', 'postgresql+asyncpg://')

async def populate_users():
    # Create engine and session
    engine = create_async_engine(POSTGRES_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ Database tables created")
    
    # Define users
    all_companies_users = [
        {"email": "rutuja@bora.tech", "password": "rutuja@123", "role": UserRole.ADMIN},
        {"email": "sunil@bora.tech", "password": "sunil@123", "role": UserRole.REGULAR},
        {"email": "athar@bora.tech", "password": "athara@123", "role": UserRole.REGULAR},
        {"email": "kritika@bora.tech", "password": "kritika@123", "role": UserRole.REGULAR},
        {"email": "himanshu@bora.tech", "password": "himanshu@123", "role": UserRole.REGULAR},
        {"email": "sayam@bora.tech", "password": "sayam@123", "role": UserRole.REGULAR},
        {"email": "bharat@bora.tech", "password": "bharat@123", "role": UserRole.REGULAR},
        {"email": "akansha@bora.tech", "password": "akansha@123", "role": UserRole.REGULAR},
    ]
    
    dns_users = [
        {"email": "rkn@bora.tech", "password": "rkn@123", "role": UserRole.REGULAR},
        {"email": "dyaneshwar@bora.tech", "password": "dyan@123", "role": UserRole.REGULAR},
        {"email": "shravni@bora.tech", "password": "shravni@123", "role": UserRole.REGULAR},
        {"email": "shreyash@bora.tech", "password": "shreyash@123", "role": UserRole.REGULAR},
    ]
    
    async with AsyncSessionLocal() as session:
        # Create All Companies Documentary users
        for user_data in all_companies_users:
            user = User(
                id=str(uuid.uuid4()),
                username=user_data["email"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                section="all_companies",
                is_active=True
            )
            session.add(user)
            print(f"✓ Created user: {user_data['email']} (All Companies)")
        
        # Create DNS Documentary users (rutuja already exists in all_companies)
        for user_data in dns_users:
            user = User(
                id=str(uuid.uuid4()),
                username=user_data["email"] + "_dns",  # Add suffix to avoid duplicate
                email=user_data["email"] + ".dns",  # Add suffix to email too
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                section="dns",
                is_active=True
            )
            session.add(user)
            print(f"✓ Created user: {user_data['email']} (DNS)")
        
        # Add rutuja to DNS as well (separate entry)
        dns_rutuja = User(
            id=str(uuid.uuid4()),
            username="rutuja@bora.tech_dns",
            email="rutuja@bora.tech.dns",
            hashed_password=get_password_hash("rutuja@123"),
            role=UserRole.ADMIN,
            section="dns",
            is_active=True
        )
        session.add(dns_rutuja)
        print(f"✓ Created user: rutuja@bora.tech (DNS)")
        
        await session.commit()
        print("\n✅ All users created successfully!")
        print("\n📝 Login Credentials:")
        print("\n--- All Companies Documentary ---")
        for user_data in all_companies_users:
            print(f"  {user_data['email']} / {user_data['password']}")
        print("\n--- DNS Documentary ---")
        for user_data in dns_users:
            print(f"  {user_data['email']} / {user_data['password']}")
        print(f"  rutuja@bora.tech / rutuja@123")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(populate_users())
