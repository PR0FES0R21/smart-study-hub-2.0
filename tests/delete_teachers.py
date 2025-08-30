from pymongo import MongoClient
from bson import ObjectId

# koneksi Mongo
client = MongoClient("mongodb://localhost:27017")
db = client["school_db_mvp"]

users_col = db["users"]
profiles_col = db["profiles"]

def delete_last_teachers(limit=800):
    # ambil 800 teacher terbaru
    teachers = list(
        users_col.find({"roles": "teacher"})
        .sort("_id", -1)  # newest first
        .limit(limit)
    )

    if not teachers:
        print("Tidak ada teacher ditemukan.")
        return

    # ambil semua user_id & profile_id
    user_ids = [t["_id"] for t in teachers]
    profile_ids = [t["profile_id"] for t in teachers if "profile_id" in t]

    # hapus di users
    res_users = users_col.delete_many({"_id": {"$in": user_ids}})
    print(f"Deleted {res_users.deleted_count} users")

    # hapus di profiles (yang user_id match)
    res_profiles = profiles_col.delete_many({"_id": {"$in": profile_ids}})
    print(f"Deleted {res_profiles.deleted_count} profiles")

if __name__ == "__main__":
    delete_last_teachers(800)
