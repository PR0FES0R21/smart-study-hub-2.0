import requests

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "79111953"
PASSWORD = "sayoga2019"

# Login
login_resp = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "",
        "client_id": "string",
        "client_secret": "********"
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Daftar mapel lengkap (umum + contoh jurusan)
subjects = [
    # Kelompok A
    {"code": "PAI", "name": "Pendidikan Agama dan Budi Pekerti", "description": "Pembelajaran akidah, ibadah, akhlak, dan sejarah agama."},
    {"code": "PPKN", "name": "Pendidikan Pancasila dan Kewarganegaraan", "description": "Nilai Pancasila, UUD 1945, kehidupan berbangsa."},
    {"code": "BIN", "name": "Bahasa Indonesia", "description": "Bahasa, sastra, keterampilan menulis & membaca."},
    {"code": "MTK", "name": "Matematika", "description": "Bilangan, aljabar, geometri, peluang, statistika."},
    {"code": "SEJ", "name": "Sejarah Indonesia", "description": "Perjalanan sejarah bangsa Indonesia."},
    {"code": "BIG", "name": "Bahasa Inggris", "description": "Listening, speaking, reading, writing."},

    # Kelompok B
    {"code": "SBY", "name": "Seni Budaya", "description": "Seni rupa, musik, tari, teater."},
    {"code": "PJOK", "name": "PJOK", "description": "Olahraga dan kesehatan jasmani/rohani."},
    {"code": "KWU", "name": "Kewirausahaan", "description": "Dasar bisnis, manajemen, wirausaha."},

    # C1
    {"code": "SIMDIG", "name": "Simulasi dan Komunikasi Digital", "description": "Komunikasi digital dan TIK dasar."},
    {"code": "IPA", "name": "IPA Terapan", "description": "Fisika dan kimia dasar untuk SMK."},

    # C2/C3 contoh jurusan TKJ
    {"code": "TKJ1", "name": "Sistem Komputer", "description": "Dasar perangkat keras komputer."},
    {"code": "TKJ2", "name": "Jaringan Dasar", "description": "Dasar instalasi dan konfigurasi jaringan."},
    {"code": "TKJ3", "name": "Pemrograman Dasar", "description": "Algoritma dan logika pemrograman."},
    {"code": "TKJ4", "name": "Administrasi Sistem Jaringan", "description": "Manajemen server, user, layanan jaringan."},
    {"code": "TKJ5", "name": "Jaringan WAN", "description": "Wide Area Network, routing, switching."},
    {"code": "TKJ6", "name": "Cloud Computing", "description": "Dasar-dasar komputasi awan."},

    # C2/C3 contoh jurusan TBSM
    {"code": "TBSM1", "name": "Pemeliharaan Mesin Sepeda Motor", "description": "Perawatan & perbaikan mesin motor."},
    {"code": "TBSM2", "name": "Pemeliharaan Kelistrikan Motor", "description": "Instalasi & perbaikan sistem kelistrikan motor."},
    {"code": "TBSM3", "name": "Chasis dan Suspensi", "description": "Pemeliharaan chasis dan suspensi motor."},

    # C2/C3 contoh jurusan Multimedia
    {"code": "MM1", "name": "Desain Grafis", "description": "Adobe Illustrator, Photoshop, CorelDraw."},
    {"code": "MM2", "name": "Animasi 2D/3D", "description": "Dasar animasi digital."},
    {"code": "MM3", "name": "Editing Video", "description": "Premiere, After Effects."},
    {"code": "MM4", "name": "Fotografi", "description": "Teknik fotografi dan editing."},

    # C2/C3 contoh jurusan Akuntansi
    {"code": "AKT1", "name": "Dasar Akuntansi", "description": "Konsep debit kredit, jurnal, laporan keuangan."},
    {"code": "AKT2", "name": "Perbankan Dasar", "description": "Produk dan layanan perbankan."},
    {"code": "AKT3", "name": "Perpajakan", "description": "Dasar perpajakan di Indonesia."},

    # C2/C3 contoh jurusan Perhotelan
    {"code": "HTL1", "name": "Front Office", "description": "Layanan resepsionis dan reservasi."},
    {"code": "HTL2", "name": "Housekeeping", "description": "Tata graha & kebersihan hotel."},
    {"code": "HTL3", "name": "Food & Beverage", "description": "Dasar tata boga & tata hidang."}
]

# Loop insert
for subj in subjects:
    resp = requests.post(f"{BASE_URL}/subjects/", headers=headers, json=subj)
    if resp.status_code == 201:
        print(f"✅ Added {subj['name']}")
    else:
        print(f"❌ Failed {subj['name']} -> {resp.text}")
