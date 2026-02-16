import pandas as pd
import requests

BASE_URL = "http://localhost:8000/api"

def test_bulk_upload_companies():
    # Login
    login_data = {"username": "rutuja@bora.tech", "password": "rutuja@123"}
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create dummy dataframe
    df = pd.DataFrame([
        {"name": "Bulk Co 1", "gstn": "27BBBBB1111B1Z1", "city": "Pune"},
        {"name": "Bulk Co 2", "gstn": "27CCCCC2222C2Z2", "city": "Delhi"}
    ])
    
    # Save to Excel
    excel_file = "test_companies.xlsx"
    df.to_excel(excel_file, index=False)
    
    # Upload
    with open(excel_file, 'rb') as f:
        files = {'file': (excel_file, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = requests.post(f"{BASE_URL}/companies/bulk", files=files, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_bulk_upload_companies()
