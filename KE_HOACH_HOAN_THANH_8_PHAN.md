# Kế hoạch hoàn thành Lab 24 — 8 phần (MedViet Governance)

**Repo:** `medviet-governance/` (làm việc chính tại đây)  
**Đề gốc:** `README.md` (thư mục gốc assignment)  
**Giả định:** Bạn đã **xong Phần 1** (có `data/raw/patients_raw.csv`, đã liệt kê cột PII).

---

## Tiền đề mỗi lần làm việc

```powershell
cd d:\VinUni\assignments\Day24-Track02-Lab-Assignment\medviet-governance
.\..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Trên Windows, các lệnh `curl` trong README thường là alias của `Invoke-WebRequest`; có thể dùng **Git Bash curl** hoặc trình duyệt / **httpx** / **Invoke-RestMethod** để gọi API.

---

## Trạng thái tổng quan

| Phần | Nội dung | Trạng thái |
|------|-----------|------------|
| 1 | Chuẩn bị dữ liệu | **Đã xong** |
| 2 | PII detection & anonymization | Cần làm |
| 3 | RBAC + FastAPI | Cần làm |
| 4 | Encryption (vault) | Cần làm |
| 5 | Great Expectations / validation | Cần làm |
| 6 | Security scanning (hook, Bandit, …) | Cần làm |
| 7 | OPA policy | Cần làm |
| 8 | Compliance checklist | Cần làm |

---

## Phần 1 — Chuẩn bị dữ liệu (đã xong)

**Mục tiêu đề:** `patients_raw.csv`, nhận diện cột PII.

**Checklist bạn nên tự xác nhận lại:**

- [ ] File `medviet-governance/data/raw/patients_raw.csv` tồn tại và đủ ~200 dòng (hoặc theo script).
- [ ] Đã ghi chú / báo cáo: các cột PII (ví dụ: `ho_ten`, `cccd`, `ngay_sinh`, `so_dien_thoai`, `email`, `dia_chi`, `bac_si_phu_trach`, …).

**Không cần làm thêm** trừ khi giảng viên yêu cầu format khác.

---

## Phần 2 — PII detection & anonymization (~45 phút)

**Rubric:** PII detection (25đ) + Anonymization (20đ).

### Mục tiêu

- Regex + spaCy + Presidio: **VN_CCCD**, **VN_PHONE**, **EMAIL_ADDRESS**, **PERSON**.
- `MedVietAnonymizer`: replace / mask / hash; dataframe; **detection rate ≥ 95%** trên mẫu test.
- Test đầy đủ trong `tests/test_pii.py`.

### File cần hoàn thiện / kiểm tra

| File | Việc cần làm |
|------|----------------|
| `src/pii/detector.py` | Recognizer CCCD/SĐT, NLP engine (`vi_core_news_lg`, có thể thêm `en_core_web_sm`), `detect_pii`. |
| `src/pii/anonymizer.py` | `anonymize_text`, `anonymize_dataframe`, `calculate_detection_rate`. |
| `tests/test_pii.py` | Assert CCCD/phone/email; detection rate; không còn CCCD gốc; `benh` / `ket_qua_xet_nghiem` không đổi. |

### Lệnh / kịch bản

```powershell
cd medviet-governance
# Project đã ghim spaCy 3.7.x (requirements.txt) để `vi_core_news_lg` cài được; nếu máy đang 3.8+: pip install -r requirements.txt --upgrade
pip install -r requirements.txt
python -m spacy download vi_core_news_lg
# Nếu code dùng thêm tiếng Anh cho NER:
python -m spacy download en_core_web_sm

pytest tests\test_pii.py -v --tb=short
```

### Tiêu chí “xong phần 2”

- [ ] `pytest tests/test_pii.py` **pass toàn bộ** (đặc biệt `test_detection_rate_above_95_percent`).
- [ ] (Tuỳ chọn nộp bài) Xuất `data/processed/patients_anonymized.csv` sau khi anonymize toàn bộ raw.

---

## Phần 3 — RBAC (Casbin) & FastAPI (~45 phút)

**Rubric:** RBAC API (20đ).

### Mục tiêu

- `policy.csv` + `model.conf`: đúng quyền theo role; **ml_engineer không đọc raw PII**; admin delete; v.v.
- `rbac.py`: Bearer token → user; `enforce` đúng tham số Casbin (theo `g, username, role` trong đề thường là enforce theo **username**).
- `main.py`: 4 endpoint + `/health`; đúng **403/401**.

### File

| File | Việc |
|------|------|
| `src/access/policy.csv` | Hoàn thiện policy, không để dòng `#` nếu Casbin của bạn không chấp nhận comment. |
| `src/access/model.conf` | Giữ theo đề (đã có mẫu). |
| `src/access/rbac.py` | `get_current_user`, `require_permission`. |
| `src/api/main.py` | Raw 10 dòng JSON; anonymized; aggregated metrics; DELETE stub. |

### Lệnh / kịch bản

```powershell
cd medviet-governance
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

**Kiểm thử (ví dụ Git Bash hoặc công cụ HTTP):**

- Bob → `GET /api/patients/raw` → **403**
- Alice → `GET /api/patients/raw` → **200**
- Bob → `DELETE /api/patients/abc123` → **403**
- Carol → `GET /api/metrics/aggregated` → **200** (nếu policy cho phép)

### Tiêu chí “xong phần 3”

- [ ] Các curl/scenario trong README khớp kết quả mong đợi.
- [ ] Không hard-code bypass RBAC.

---

## Phần 4 — Encryption (~30 phút)

**Rubric:** Encryption (15đ).

### Mục tiêu

- `SimpleVault`: KEK file; envelope **AES-256-GCM**; `encrypt_data` / `decrypt_data` round-trip; `encrypt_column`.

### File

- `src/encryption/vault.py`

### Kịch bản kiểm tra (Python)

```powershell
cd medviet-governance
python
```

```python
from src.encryption.vault import SimpleVault
vault = SimpleVault()
s = "Nguyen Van A - CCCD: 012345678901"
enc = vault.encrypt_data(s)
assert vault.decrypt_data(enc) == s
print("OK")
```

### Tiêu chí “xong phần 4”

- [ ] Round-trip đúng chuỗi Unicode tiếng Việt.
- [ ] **Không** commit `.vault_key` lên git / file nộp.

---

## Phần 5 — Data quality — Great Expectations (~20 phút)

**Rubric:** Hỗ trợ phần chất lượng dữ liệu / báo cáo (thường đi kèm checklist & pipeline).

### Mục tiêu

- `build_patient_expectation_suite()`: đủ expectation theo đề (null `patient_id`, độ dài `cccd`, khoảng `ket_qua_xet_nghiem`, tập `benh`, regex `email`, unique `patient_id`).
- `validate_anonymized_data()`: logic kiểm post-anonymization (không leak CCCD raw theo `patient_id`, null, số dòng).

### File

- `src/quality/validation.py`

### Lệnh / kịch bản

```powershell
cd medviet-governance
python -c "from src.quality.validation import build_patient_expectation_suite; build_patient_expectation_suite(); print('suite OK')"
python -c "from src.quality.validation import validate_anonymized_data; print(validate_anonymized_data('data/processed/patients_anonymized.csv'))"
```

> Đường dẫn file anonymized chỉnh theo nơi bạn lưu CSV.

### Tiêu chí “xong phần 5”

- [ ] Chạy được build suite không lỗi import/API Great Expectations (phiên bản trong `requirements.txt`).
- [ ] `validate_anonymized_data` trả dict có `success`, `failed_checks`, `stats`.

---

## Phần 6 — Security scanning (~20 phút)

**Rubric:** Security audit (10đ).

### Mục tiêu

- Hook `.github/hooks/pre-commit`: **git-secrets** + **bandit** + **pip-audit** (theo README).
- Thư mục `reports/`, xuất Bandit JSON.
- (Tuỳ chọn) TruffleHog nếu cài được.

### Việc cần làm

| Việc | Ghi chú |
|------|--------|
| Cài git-secrets | Windows: binary release / WSL / hướng dẫn giảng viên. |
| `bandit -r src/ -f json -o reports/bandit_report.json` | Tạo `reports` trước: `mkdir reports` |
| `pip-audit` | Theo hook README |
| Thử hook | File fake AWS key → commit bị chặn (**không** push secret thật) |

### Tiêu chí “xong phần 6”

- [ ] Có `reports/bandit_report.json` (hoặc tương đương đề yêu cầu).
- [ ] Ghi trong báo cáo nộp bài: hook đã chạy và chặn được test credential giả.

---

## Phần 7 — OPA policy (~15 phút)

**Rubric:** Liên quan access control / compliance (mapping ABAC).

### Mục tiêu

- Hoàn thiện `policies/opa_policy.rego`: admin; ml_engineer; **deny** delete production; data_analyst; intern; deny export restricted ra ngoài VN.

### Lệnh / kịch bản (cần OPA CLI)

```bash
opa version
# Ví dụ eval theo README — chỉnh package/path cho đúng file của bạn
```

### Tiêu chí “xong phần 7”

- [ ] `opa eval` với input mẫu (ml_engineer + delete production) cho kết quả **allow = false** (hoặc rule tương đương bạn thiết kế nhất quán với đề).

---

## Phần 8 — Compliance checklist (~15 phút)

**Rubric:** Compliance checklist (10đ).

### Mục tiêu

- Hoàn thiện `medviet-governance/compliance_checklist.md`: mục A–F, DPO contact, bảng mapping NĐ13 — các dòng Todo có **giải pháp kỹ thuật cụ thể**.

### Tiêu chí “xong phần 8”

- [ ] Không còn placeholder `___` / mục “Todo” trống trong phần bắt buộc.
- [ ] Nội dung khớp những gì bạn đã implement (Presidio, Casbin, OPA, encryption, logging, …).

---

## Thứ tự gợi ý (sau Phần 1)

1. **Phần 2** (block mọi thứ phụ thuộc anonymizer + test).  
2. **Phần 3** (API + RBAC — có thể làm song song cuối Phần 2).  
3. **Phần 4** (độc lập).  
4. **Phần 5** (cần CSV raw; nên có file anonymized để test `validate_anonymized_data`).  
5. **Phần 7** + **Phần 8** (tài liệu / policy, xen khi chờ cài tool).  
6. **Phần 6** (cuối hoặc song song — tạo `reports/` trước khi zip nộp).

---

## Gói nộp bài (nhắc từ README)

```powershell
cd medviet-governance
mkdir reports -ErrorAction SilentlyContinue
pytest tests -v --tb=short > reports\test_results.txt
bandit -r src -f json -o reports\bandit_report.json
```

**Zip (không nộp `data/raw/`, `.vault_key`):**

- `src/`, `tests/`, `policies/`, `data/processed/`, `compliance_checklist.md`, `reports/`, `requirements.txt`

---

## Checklist “lab hoàn chỉnh” (tự đánh dấu)

- [ ] Phần 2: pytest PII pass, detection ≥ 95%.
- [ ] Phần 3: API + Casbin đúng 401/403 theo scenario.
- [ ] Phần 4: vault round-trip OK.
- [ ] Phần 5: suite + validate chạy được.
- [ ] Phần 6: Bandit JSON + mô tả hook/git-secrets.
- [ ] Phần 7: OPA eval mẫu đúng ý đồ đề.
- [ ] Phần 8: checklist đầy đủ, có technical controls cụ thể.
- [ ] Docker (nếu bắt buộc): `docker compose` theo `docker-compose.yml`.

---

*Tài liệu này là kế hoạch làm việc; chi tiết code và rubric đầy đủ nằm trong `README.md`.*
