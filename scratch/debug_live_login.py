import httpx

def test():
    url = "http://13.50.236.19/api/auth/login"
    payload = {"username": "sunil@bora.tech", "password": "sunil@123"}
    try:
        with httpx.Client() as client:
            resp = client.post(url, json=payload)
            print(f"Status: {resp.status_code}")
            print(f"Headers: {resp.headers}")
            print(f"Content: {resp.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
