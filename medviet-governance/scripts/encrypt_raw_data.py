import pandas as pd
import json
from pathlib import Path
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.encryption.vault import SimpleVault

def main():
    raw_path = Path("data/raw/patients_raw.csv")
    if not raw_path.exists():
        print(f"Error: {raw_path} not found.")
        return

    print(f"Loading data from {raw_path}...")
    df = pd.read_csv(raw_path)
    
    vault = SimpleVault()
    
    sensitive_columns = ["cccd", "so_dien_thoai", "email"]
    
    print(f"Encrypting columns: {sensitive_columns}...")
    for col in sensitive_columns:
        if col in df.columns:
            # Check if already encrypted (simplistic check)
            if not str(df[col].iloc[0]).startswith('{"encrypted_dek"'):
                df = vault.encrypt_column(df, col)
                print(f"  - Encrypted {col}")
            else:
                print(f"  - {col} is already encrypted.")

    df.to_csv(raw_path, index=False)
    print(f"Done! Encrypted data saved back to {raw_path}")

if __name__ == "__main__":
    main()
