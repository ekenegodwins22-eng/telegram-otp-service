import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from datetime import datetime, timedelta

# Import database utilities
from database import db, generate_linking_code

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your actual bot token or set as environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

async def start(update: Update, context):
    """Sends a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to the Multi-Tenant OTP Service Bot! "
        "To link your account, please get a linking code from the website and send it to me."
    )

async def handle_linking_code(update: Update, context):
    """Handles incoming messages that are potential linking codes."""
    text = update.message.text.strip().upper()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the message looks like a linking code (e.g., LNK-XXXXXX)
    if not text.startswith("LNK-") or len(text) != 10:
        await update.message.reply_text(
            "I'm sorry, I didn't recognize that. Please send a valid linking code (e.g., LNK-A1B2C3) or use the /start command."
        )
        return

    linking_code = text

    # 1. Look up the linking code in the database
    linking_record = db["linking_codes"].get(linking_code)

    if not linking_record:
        await update.message.reply_text(
            f"Linking code **{linking_code}** is invalid or has expired. Please request a new one from the website."
        )
        return

    # 2. Check for expiration
    expires_at = datetime.fromisoformat(linking_record["expires_at"])
    if datetime.now() > expires_at:
        # Clean up expired code
        db["linking_codes"].delete(linking_code)
        await update.message.reply_text(
            f"Linking code **{linking_code}** has expired. Please request a new one from the website."
        )
        return

    # 3. Get client info and create permanent link
    client_id = linking_record["client_id"]
    phone_number = linking_record["phone_number"]
    
    client_info = db["clients"].get(client_id)
    service_name = client_info["service_name"] if client_info else "an unknown service"

    try:
        # Create/Update the permanent link
        db["end_users"].insert({
            "client_id": client_id,
            "phone_number": phone_number,
            "telegram_chat_id": chat_id,
            "telegram_user_id": user_id,
        }, alter=True, replace=True)

        # 4. Clean up the temporary linking code
        db["linking_codes"].delete(linking_code)

        # 5. Send success message
        await update.message.reply_text(
            f"✅ Success! Your phone number **{phone_number}** for **{service_name}** is now linked to this Telegram chat. "
            "You can now receive OTPs here."
        )
    except Exception as e:
        logger.error(f"Error linking user: {e}")
        await update.message.reply_text(
            "An error occurred while trying to link your account. Please try again later."
        )


def main():
    """Start the bot."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("FATAL: Please replace 'YOUR_BOT_TOKEN_HERE' with your actual Telegram Bot Token.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non-command messages - handle as linking code
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_linking_code))

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is running... Press Ctrl-C to stop.")
    application.run_polling(poll_interval=1.0)

if __name__ == "__main__":
    main()
