
import requests
import json

def test_api():
    login_url = "http://localhost:8000/api/auth/login"
    login_data = {"username": "rutuja@bora.tech", "password": "rutuja@123"}
    
    response = requests.post(login_url, json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    pi_url = "http://localhost:8000/api/pi"
    response = requests.get(pi_url, headers=headers)
    
    if response.status_code == 200:
        pis = response.json()
        print(f"PI Count: {len(pis)}")
        if pis:
            print("First PI sample:")
            print(json.dumps(pis[0], indent=2))
    else:
        print(f"PI fetch failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_api()
