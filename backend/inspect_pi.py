
import requests
import json

def test_api():
    login_url = "http://localhost:8000/api/auth/login"
    login_data = {"username": "rutuja@bora.tech", "password": "rutuja@123"}
    
    response = requests.post(login_url, json=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    pi_url = "http://localhost:8000/api/pi"
    response = requests.get(pi_url, headers=headers)
    
    pis = response.json()
    if pis:
        # Save the first PI to a file to inspect
        with open("pi_sample.json", "w") as f:
            json.dump(pis[0], f, indent=2)
        print("PI sample saved to pi_sample.json")

if __name__ == "__main__":
    test_api()
