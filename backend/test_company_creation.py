import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_create_company():
    # Login first
    login_data = {
        "username": "rutuja@bora.tech",
        "password": "rutuja@123"
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create company
    company_data = {
        "name": "Test Company " + str(requests.utils.quote(str(datetime.now()) if 'datetime' in locals() else '123')),
        "gstn": "27AAAAA0000A1Z5",
        "city": "Mumbai",
        "country": "India"
    }
    # Simplified name for testing
    import time
    company_data["name"] = f"Test Company {int(time.time())}"
    
    print(f"Sending request to create company: {company_data}")
    response = requests.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_create_company()
