import sqlite_utils
from datetime import datetime, timedelta
import secrets
import hashlib
import os

DB_PATH = "otp_service.db"
db = sqlite_utils.Database(DB_PATH)

# --- Table Definitions ---

# 1. Clients (Tenants)
db["clients"].create({
    "client_id": str,
    "client_secret_hash": str,
    "service_name": str,
}, pk="client_id", if_not_exists=True)

# 2. EndUsers (Permanent Link)
db["end_users"].create({
    "client_id": str,
    "phone_number": str,
    "telegram_chat_id": int,
}, pk=("client_id", "phone_number"), if_not_exists=True)

# 3. LinkingCodes (Temporary Link)
db["linking_codes"].create({
    "linking_code": str,
    "client_id": str,
    "phone_number": str,
    "expires_at": str,
}, pk="linking_code", if_not_exists=True)

# 4. OTPs (One-Time Passwords)
db["otps"].create({
    "client_id": str,
    "phone_number": str,
    "code": str,
    "expires_at": str,
}, pk=("client_id", "phone_number"), if_not_exists=True)

# --- Utility Functions ---

def hash_secret(secret: str) -> str:
    """Hashes a secret using SHA256."""
    return hashlib.sha256(secret.encode()).hexdigest()

def verify_secret(secret: str, hashed_secret: str) -> bool:
    """Verifies a secret against its hash."""
    return hash_secret(secret) == hashed_secret

def generate_linking_code() -> str:
    """Generates a 6-character alphanumeric linking code."""
    return secrets.token_hex(3).upper()

def generate_otp() -> str:
    """Generates a 6-digit numeric OTP."""
    return str(secrets.randbelow(1000000)).zfill(6)

def init_db():
    """Initializes the database with a sample client for testing."""
    # Hardcoded sample client for prototype
    sample_client_id = "PHOENIX_SOUL_RISE"
    sample_secret = "super_secret_key_123"
    sample_service_name = "Phoenix Soul Rise"

    # Ensure the client table exists and the sample client is present
    db["clients"].insert({
        "client_id": sample_client_id,
        "client_secret_hash": hash_secret(sample_secret),
        "service_name": sample_service_name,
    }, alter=True, replace=True)
    print(f"Initialized sample client: {sample_client_id} with secret: {sample_secret}")
    
    # Clean up expired codes/otps on startup
    db["linking_codes"].delete_where("expires_at < ?", [datetime.now().isoformat()])
    db["otps"].delete_where("expires_at < ?", [datetime.now().isoformat()])

# The init_db() function is now called explicitly in api.py and bot.py
# to ensure it runs only once per process, preventing database locking.
