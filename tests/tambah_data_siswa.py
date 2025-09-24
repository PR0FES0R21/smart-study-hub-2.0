import requests
import random
import faker

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_USER = "79111953"
ADMIN_PASS = "sayoga2019"

# --- Login admin
login_resp = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "grant_type": "password",
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
        "scope": "",
        "client_id": "string",
        "client_secret": "********"
    },
    headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
)

access_token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

# --- Daftar class_id (lu punya dari atas)
class_ids = [
    "687e01044593234141867820",
    "6885e5bf17298472a078fae3",
    "6885e5d217298472a078fae4",
    "688a41602bbce55062b8f0c3",
    "6894bbfda8b78acc6a1fdfce",
    "68b2d3479d799b47b6fd4675",
    "68b2d35a9d799b47b6fd4676",
    "68b2d3629d799b47b6fd4677",
    "68b2d3729d799b47b6fd4678",
    "68b2d3799d799b47b6fd4679",
    "68b2d3859d799b47b6fd467a",
    "68b2d38b9d799b47b6fd467b",
    "68b2d3939d799b47b6fd467c",
    "68b2d39a9d799b47b6fd467d",
    "68b2d3c09d799b47b6fd467e",
    "68b2d3c59d799b47b6fd467f",
    "68b2d3dc9d799b47b6fd4680",
    "68b2d3e19d799b47b6fd4681",
    "68b2d3e89d799b47b6fd4682",
    "68b2d3ed9d799b47b6fd4683",
    "68b2d3f59d799b47b6fd4684",
    "68b2d3fb9d799b47b6fd4685",
    "68b2d4049d799b47b6fd4686",
    "68b2d4099d799b47b6fd4687"
]

fake = faker.Faker("id_ID")  # biar nama/alamat Indonesia

student_counter = 1
for class_id in class_ids:
    # Bikin jumlah random 10–40 siswa per kelas
    jumlah_siswa = random.randint(10, 40)

    for _ in range(jumlah_siswa):
        payload = {
            "login_id": f"{student_counter:08d}",
            "email": f"student{student_counter}@mail.com",
            "roles": ["student"],
            "is_active": True,
            "profile": {
                "full_name": fake.name(),
                "gender": random.choice(["Laki Laki", "Perempuan"]),
                "birth_date": fake.date_time_between(start_date="-20y", end_date="-10y").isoformat(),
                "birth_place": fake.city(),
                "address": fake.address(),
                "phone_number": fake.phone_number(),
                "class_id": class_id,
                "start_year": 2026,
                "end_year": 2029
            }
        }
        r = requests.post(f"{BASE_URL}/users/", json=payload, headers=headers)
        if r.status_code != 200:
            print("Gagal insert:", r.text)
        student_counter += 1

print("✅ Dummy student berhasil di-generate")
