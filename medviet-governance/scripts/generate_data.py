# scripts/generate_data.py
import random
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("vi_VN")
Faker.seed(42)

def generate_patients(n=200):
    records = []
    for _ in range(n):
        records.append({
            "patient_id": fake.uuid4(),
            "ho_ten": fake.name(),
            "cccd": "".join(str(random.randint(0, 9)) for _ in range(12)),
            "ngay_sinh": fake.date_of_birth(minimum_age=18, maximum_age=90)
                              .strftime("%d/%m/%Y"),
            "so_dien_thoai": "0"
            + str(random.choice([3, 5, 7, 8, 9]))
            + "".join(str(random.randint(0, 9)) for _ in range(8)),
            "email": fake.email(),
            "dia_chi": fake.address(),
            "benh": random.choice(["Tiểu đường", "Huyết áp cao", 
                                   "Tim mạch", "Khỏe mạnh"]),
            "ket_qua_xet_nghiem": round(random.uniform(3.5, 12.0), 2),
            "bac_si_phu_trach": fake.name(),
            "ngay_kham": fake.date_this_year().strftime("%d/%m/%Y"),
        })
    return pd.DataFrame(records)

Path("data/raw").mkdir(parents=True, exist_ok=True)
df = generate_patients()
# Giữ CCCD/SĐT là chuỗi (tránh Excel/pandas làm mất số 0 đầu khi đọc lại).
df = df.astype({"cccd": "string", "so_dien_thoai": "string"})
df.to_csv("data/raw/patients_raw.csv", index=False)
print(f"Generated {len(df)} patient records")
print(df.head(3))
