import requests

BASE_URL = "http://localhost:8000/api/v1"

# Try different possible credentials
credentials = [
    ("admin", "admin123"),
    ("admin", "admin"),
    ("teacher", "teacher123"),
    ("guru", "password"),
    ("guru.budi", "password123"),
    ("test", "test123"),
]

print("Testing login with different credentials...\n")

for username, password in credentials:
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"[SUCCESS] {username} / {password}")
            data = response.json()
            print(f"  Token: {data['access_token'][:50]}...")
            print(f"  User: {data.get('user', {})}")
            break
        else:
            print(f"[FAILED] {username} / {password} -> {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {username} -> {str(e)}")

print("\nDone!")
