import os
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging
from telegram import Bot
from telegram.error import TelegramError

# Import database utilities
from database import db, hash_secret, verify_secret, generate_linking_code, generate_otp, init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your actual bot token or set as environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Initialize FastAPI app
init_db()
app = FastAPI(title="Multi-Tenant Telegram OTP Service API")

# Initialize Telegram Bot for sending messages
try:
    telegram_bot = Bot(token=BOT_TOKEN)
except Exception as e:
    logger.error(f"Failed to initialize Telegram Bot: {e}")
    telegram_bot = None

# --- Pydantic Models for API Request/Response ---

class AuthHeaders(BaseModel):
    """Model for authentication headers."""
    client_id: str = Header(..., alias="X-Client-ID")
    client_secret: str = Header(..., alias="X-Client-Secret")

class PhoneNumberRequest(BaseModel):
    """Model for requests that only need a phone number."""
    phone_number: str

class OTPVerificationRequest(PhoneNumberRequest):
    """Model for OTP verification request."""
    otp_code: str

# --- Dependency for Client Authentication ---

def authenticate_client(auth: AuthHeaders = Depends()):
    """Authenticates the client using ID and Secret."""
    client_record = db["clients"].get(auth.client_id)
    
    if not client_record:
        raise HTTPException(status_code=401, detail="Invalid Client ID")
    
    if not verify_secret(auth.client_secret, client_record["client_secret_hash"]):
        raise HTTPException(status_code=401, detail="Invalid Client Secret")
    
    return client_record

# --- API Endpoints ---

@app.post("/api/v1/link/generate_code", summary="Generate a temporary linking code for a user.")
async def generate_link_code_endpoint(
    request: PhoneNumberRequest,
    client_info: dict = Depends(authenticate_client)
):
    """
    Generates a short-lived linking code that the user must send to the Telegram bot.
    This links the user's phone number (from the client's system) to their Telegram Chat ID.
    """
    client_id = client_info["client_id"]
    phone_number = request.phone_number
    
    # Generate code and expiration
    linking_code = "LNK-" + generate_linking_code()
    expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
    
    # Store in temporary table
    db["linking_codes"].insert({
        "linking_code": linking_code,
        "client_id": client_id,
        "phone_number": phone_number,
        "expires_at": expires_at,
    }, alter=True, replace=True)
    
    return {
        "status": "success",
        "linking_code": linking_code,
        "message": f"User must send this code to the bot: {linking_code}"
    }

@app.post("/api/v1/otp/send", summary="Generate and send an OTP to a linked user via Telegram.")
async def send_otp_endpoint(
    request: PhoneNumberRequest,
    client_info: dict = Depends(authenticate_client)
):
    """
    Generates an OTP and sends it to the user's linked Telegram chat.
    Requires the user to have completed the linking process.
    """
    if not telegram_bot:
        raise HTTPException(status_code=503, detail="Telegram Bot Service is unavailable.")

    client_id = client_info["client_id"]
    service_name = client_info["service_name"]
    phone_number = request.phone_number

    # 1. Check if user is linked
    user_link = db["end_users"].get((client_id, phone_number))
    if not user_link:
        raise HTTPException(status_code=404, detail="User not linked to Telegram for this service.")

    chat_id = user_link["telegram_chat_id"]

    # 2. Generate and store OTP
    otp_code = generate_otp()
    expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
    
    # Store in OTP table (replaces any existing OTP for this user/client)
    db["otps"].insert({
        "client_id": client_id,
        "phone_number": phone_number,
        "code": otp_code,
        "expires_at": expires_at,
    }, alter=True, replace=True)

    # 3. Send message via Telegram
    message_text = (
        f"Your One-Time Password (OTP) for **{service_name}** is: **{otp_code}**.\n"
        "This code is valid for 5 minutes."
    )
    
    try:
        await telegram_bot.send_message(chat_id=chat_id, text=message_text, parse_mode="Markdown")
    except TelegramError as e:
        logger.error(f"Telegram send error for chat_id {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message via Telegram.")

    return {"status": "success", "message": "OTP sent successfully to Telegram."}

@app.post("/api/v1/otp/verify", summary="Verify a submitted OTP.")
async def verify_otp_endpoint(
    request: OTPVerificationRequest,
    client_info: dict = Depends(authenticate_client)
):
    """
    Verifies the OTP provided by the client's server.
    """
    client_id = client_info["client_id"]
    phone_number = request.phone_number
    submitted_otp = request.otp_code

    # 1. Look up the stored OTP
    otp_record = db["otps"].get((client_id, phone_number))

    if not otp_record:
        raise HTTPException(status_code=404, detail="No active OTP found for this user.")

    # 2. Check for expiration
    expires_at = datetime.fromisoformat(otp_record["expires_at"])
    if datetime.now() > expires_at:
        # Clean up expired OTP
        db["otps"].delete((client_id, phone_number))
        raise HTTPException(status_code=400, detail="OTP has expired.")

    # 3. Verify the code
    if otp_record["code"] == submitted_otp:
        # Success: Delete the OTP to prevent reuse
        db["otps"].delete((client_id, phone_number))
        return {"status": "success", "message": "OTP verified successfully."}
    else:
        # Failure
        raise HTTPException(status_code=400, detail="Invalid OTP.")

# --- Health Check ---

@app.get("/health")
def health_check():
    return {"status": "ok", "db_path": db.path}
