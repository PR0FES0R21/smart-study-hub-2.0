from pymongo import MongoClient
from datetime import datetime

# Koneksi Mongo
client = MongoClient("mongodb://localhost:27017")
db = client["school_db_mvp"]
profiles = db["profiles"]

# Ambil semua siswa, sort by _id biar konsisten
all_students = list(profiles.find().sort("_id", 1))
total_students = len(all_students)
print(f"Total siswa ditemukan: {total_students}")

# Distribusi manual biar bagus untuk visualisasi
year_distribution = {
    2020: 80,
    2021: 120,
    2022: 150,
    2023: 110,
    2024: 10,
    2025: 100,
    2026: 144
}

start_index = 0
for year, count in year_distribution.items():
    end_index = start_index + count
    batch = all_students[start_index:end_index]

    for student in batch:
        profiles.update_one(
            {"_id": student["_id"]},
            {"$set": {
                "start_year": year,
                "end_year": year + 3,
                "updated_at": datetime.utcnow()
            }}
        )
    print(f"✅ {count} siswa di-update ke start_year {year}")
    start_index = end_index

print("🎉 Update selesai! Distribusi siswa sekarang variatif untuk visualisasi.")
