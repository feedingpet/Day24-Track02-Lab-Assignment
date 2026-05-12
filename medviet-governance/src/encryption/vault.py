import base64
import json
import os
from pathlib import Path

import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SimpleVault:
    """
    Local envelope encryption (KEK on disk). Replace with KMS/HSM in production.
    """

    def __init__(self, master_key_path: str = ".vault_key"):
        self.master_key_path = master_key_path
        self.kek = self._load_or_create_kek()

    def _load_or_create_kek(self) -> bytes:
        path = Path(self.master_key_path)
        if path.is_file():
            with path.open("rb") as f:
                return base64.b64decode(f.read())
        kek = os.urandom(32)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            f.write(base64.b64encode(kek))
        return kek

    def generate_dek(self) -> tuple[bytes, bytes]:
        plaintext_dek = os.urandom(32)
        aesgcm = AESGCM(self.kek)
        nonce = os.urandom(12)
        encrypted_dek = nonce + aesgcm.encrypt(nonce, plaintext_dek, None)
        return plaintext_dek, encrypted_dek

    def decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        nonce = encrypted_dek[:12]
        ciphertext = encrypted_dek[12:]
        aesgcm = AESGCM(self.kek)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_data(self, plaintext: str) -> dict:
        plaintext_dek, encrypted_dek = self.generate_dek()
        aesgcm = AESGCM(plaintext_dek)
        nonce = os.urandom(12)
        body = plaintext.encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, body, None)
        del plaintext_dek

        return {
            "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
            "ciphertext": base64.b64encode(nonce + ciphertext).decode(),
            "algorithm": "AES-256-GCM",
        }

    def decrypt_data(self, encrypted_payload: dict) -> str:
        encrypted_dek = base64.b64decode(encrypted_payload["encrypted_dek"])
        ciphertext_with_nonce = base64.b64decode(encrypted_payload["ciphertext"])

        plaintext_dek = self.decrypt_dek(encrypted_dek)
        nonce = ciphertext_with_nonce[:12]
        ciphertext = ciphertext_with_nonce[12:]

        aesgcm = AESGCM(plaintext_dek)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        del plaintext_dek

        return plaintext.decode("utf-8")

    def encrypt_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        df = df.copy()
        df[column] = df[column].apply(lambda x: json.dumps(self.encrypt_data(str(x))))
        return df
