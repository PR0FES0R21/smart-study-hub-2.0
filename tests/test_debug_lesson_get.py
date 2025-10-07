import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Try to get a lesson - replace with actual lesson_id
lesson_id = "68e417bcfd89bb8eb15f09ad"  # From your error

print("="*80)
print("DEBUG: GET /lessons/{lesson_id}")
print("="*80)

# First, let's list lessons to get a valid ID
print("\n1. Listing lessons to find a valid ID...")
try:
    # Without auth to see if that's the issue
    response = requests.get(
        f"{BASE_URL}/lessons",
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 401:
        print("Need authentication. Let me try with login...")
        
        # Try to login
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": "admin", "password": "admin123"},
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")
            print("Please provide valid credentials in the script")
            exit(1)
        
        token = login_response.json()["access_token"]
        print(f"Logged in successfully!")
        
        # Now get lessons with auth
        response = requests.get(
            f"{BASE_URL}/lessons",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        print(f"List lessons status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("items") and len(data["items"]) > 0:
                lesson_id = data["items"][0]["id"]
                print(f"Found lesson ID: {lesson_id}")
            else:
                print("No lessons found in database")
                exit(0)
    
except Exception as e:
    print(f"Error: {e}")
    exit(1)

# Now test GET lesson detail
print(f"\n2. Getting lesson detail: {lesson_id}")
try:
    response = requests.get(
        f"{BASE_URL}/lessons/{lesson_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"\nFull Response:")
    print("="*80)
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2, default=str))
    except:
        print(response.text)
    
    print("="*80)
    
except Exception as e:
    print(f"Exception occurred: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")
