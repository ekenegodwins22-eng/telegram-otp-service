# Multi-Tenant Telegram OTP Service Prototype

This project implements a secure, multi-tenant Telegram bot service for One-Time Password (OTP) delivery, as discussed. It uses FastAPI for the API endpoints, `python-telegram-bot` for the bot logic, and `sqlite-utils` for a simple, file-based database.

## Key Features

1.  **Multi-Tenancy:** Supports multiple client websites (tenants) with isolated data.
2.  **Simplified Linking:** Users link their phone number to their Telegram chat ID using a single, short-lived code.
3.  **Secure API:** Client authentication using `X-Client-ID` and `X-Client-Secret` headers.
4.  **Service Name Inclusion:** OTP messages automatically include the client's service name for user trust.

## Setup and Running

### Prerequisites

*   Python 3.11+
*   A Telegram Bot Token (obtained from BotFather).

### 1. Project Structure

```
telegram_otp_service/
├── database.py       # Database setup, models, and utility functions
├── bot.py            # Telegram bot logic (handles linking code)
├── api.py            # FastAPI endpoints (generate_code, send_otp, verify_otp)
├── main.py           # Unified entry point to run API and Bot
└── requirements.txt  # Project dependencies
```

### 2. Installation

```bash
# Navigate to the project directory
cd telegram_otp_service

# Install dependencies
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

You must set your Telegram Bot Token as an environment variable.

```bash
export TELEGRAM_BOT_TOKEN="YOUR_ACTUAL_BOT_TOKEN_HERE"
```

### 4. Running the Service

The `main.py` file starts both the FastAPI server (for the API) and the Telegram bot (using polling) concurrently.

```bash
python main.py
```

The API server will run on `http://0.0.0.0:8000`.

## API Documentation

The service provides three main endpoints for client integration.

### Client Credentials (Sample)

For testing, a sample client is initialized in `database.py`:

| Field | Value |
| :--- | :--- |
| **Client ID** | `PHOENIX_SOUL_RISE` |
| **Client Secret** | `super_secret_key_123` |
| **Service Name** | `Phoenix Soul Rise` |

### 1. Generate Linking Code

This is the first step to initiate the linking process from the client's website.

*   **Endpoint:** `POST /api/v1/link/generate_code`
*   **Headers:**
    *   `X-Client-ID`: `PHOENIX_SOUL_RISE`
    *   `X-Client-Secret`: `super_secret_key_123`
*   **Body (JSON):**
    ```json
    {
        "phone_number": "+15551234567"
    }
    ```
*   **Response (Success):**
    ```json
    {
        "status": "success",
        "linking_code": "LNK-A1B2C3",
        "message": "User must send this code to the bot: LNK-A1B2C3"
    }
    ```

### 2. Send OTP

This is called by the client's server when a user requests an OTP for login/signup.

*   **Endpoint:** `POST /api/v1/otp/send`
*   **Headers:** (Same as above)
*   **Body (JSON):**
    ```json
    {
        "phone_number": "+15551234567"
    }
    ```
*   **Response (Success):** The user receives the OTP in Telegram.
    ```json
    {
        "status": "success",
        "message": "OTP sent successfully to Telegram."
    }
    ```

### 3. Verify OTP

This is called by the client's server to check the OTP entered by the user.

*   **Endpoint:** `POST /api/v1/otp/verify`
*   **Headers:** (Same as above)
*   **Body (JSON):**
    ```json
    {
        "phone_number": "+15551234567",
        "otp_code": "123456"
    }
    ```
*   **Response (Success):**
    ```json
    {
        "status": "success",
        "message": "OTP verified successfully."
    }
    ```
*   **Response (Failure):**
    ```json
    {
        "detail": "Invalid OTP."
    }
    ```

## Flow Summary

1.  **Client Website:** Calls `generate_code` with user's phone number.
2.  **Client Website:** Displays the returned `linking_code` and bot link to the user.
3.  **User:** Sends the `linking_code` to the Telegram bot.
4.  **Bot:** Receives the code, creates a permanent link in the database, and confirms with the user.
5.  **Client Website (Login):** Calls `send_otp` with user's phone number.
6.  **Bot:** Sends the OTP to the user's linked Telegram chat.
7.  **Client Website (Verification):** Calls `verify_otp` with the user's phone number and the code they entered.
8.  **Service:** Verifies the code and confirms the login to the client's server.
