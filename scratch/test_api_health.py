import asyncio
import os
import httpx
from dotenv import load_dotenv
from pathlib import Path

async def test_api_health():
    backend_dir = Path("backend")
    load_dotenv(backend_dir / ".env")
    
    # Check if backend is running locally or on a known IP
    # Based on App.js, it might be localhost:8000
    urls = ["http://localhost:8000/health", "http://13.50.236.19:8000/health"]
    
    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                print(f"Checking {url}...")
                response = await client.get(url, timeout=5.0)
                print(f"Status: {response.status_code}")
                print(f"Response: {response.json()}")
                if response.status_code == 200:
                    print("SUCCESS: Backend is reachable and healthy!")
                    return True
            except Exception as e:
                print(f"Failed to connect to {url}: {e}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_api_health())
