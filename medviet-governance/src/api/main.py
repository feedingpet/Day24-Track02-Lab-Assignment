from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI
from fastapi.encoders import jsonable_encoder

from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer
from src.encryption.vault import SimpleVault
import json

import logging
import time
import uuid
from pythonjsonlogger import jsonlogger
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import Request

# Setup Structured Logging
logger = logging.getLogger("audit_logger")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(timestamp)s %(request_id)s %(user)s %(resource)s %(action)s %(status_code)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "patients_raw.csv"

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()
vault = SimpleVault()

# Prometheus Instrumentation
Instrumentator().instrument(app).expose(app)

@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Try to get user from header (same logic as get_current_user but earlier)
    user = "anonymous"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        from src.access.rbac import MOCK_USERS
        user_info = MOCK_USERS.get(token)
        if user_info:
            user = user_info["username"]

    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log the access
    logger.info("API Access", extra={
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "request_id": request_id,
        "user": user,
        "resource": request.url.path,
        "action": request.method,
        "status_code": response.status_code,
        "latency_ms": round(process_time * 1000, 2)
    })
    
    return response


def _load_raw_df() -> pd.DataFrame:
    if not RAW_CSV.is_file():
        raise FileNotFoundError(f"Missing dataset: {RAW_CSV}")
    df = pd.read_csv(
        RAW_CSV,
        dtype={"cccd": "string", "so_dien_thoai": "string"},
    )
    
    # Auto-decryption logic for at-rest encrypted columns
    for col in ["cccd", "so_dien_thoai", "email"]:
        if col in df.columns:
            first_val = str(df[col].iloc[0])
            if first_val.startswith('{"encrypted_dek"'):
                df[col] = df[col].apply(lambda x: vault.decrypt_data(json.loads(x)))
                
    return df


@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(current_user: dict = Depends(get_current_user)):
    df = _load_raw_df()
    records = jsonable_encoder(df.head(10).to_dict(orient="records"))
    return {"count": len(records), "records": records}


@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(current_user: dict = Depends(get_current_user)):
    df = _load_raw_df()
    df_anon = anonymizer.anonymize_dataframe(df)
    records = jsonable_encoder(df_anon.head(10).to_dict(orient="records"))
    return {"count": len(records), "records": records}


@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(current_user: dict = Depends(get_current_user)):
    df = _load_raw_df()
    counts = df.groupby("benh").size().reset_index(name="patient_count")
    return {
        "metrics": jsonable_encoder(
            counts.rename(columns={"benh": "condition"}).to_dict(orient="records")
        )
    }


@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
):
    return {"deleted": True, "patient_id": patient_id}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
