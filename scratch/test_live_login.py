import asyncio
import httpx

async def test_live_login():
    # Trying both port 80 and 8000
    urls = [
        "http://13.50.236.19/api/auth/login",
        "http://13.50.236.19:8000/api/auth/login"
    ]
    
    payload = {
        "username": "sunil@bora.tech",
        "password": "sunil@123"
    }
    
    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                print(f"Testing login at {url}...")
                response = await client.post(url, json=payload, timeout=10.0)
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("SUCCESS: Login successful on live server!")
                    print(f"Response: {response.json()}")
                    return
                else:
                    print(f"Failed: {response.text}")
            except Exception as e:
                print(f"Error connecting to {url}: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_login())
