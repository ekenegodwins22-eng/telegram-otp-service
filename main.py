import uvicorn
from api import app
from bot import main as run_bot_polling
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_api_server():
    """Starts the FastAPI server."""
    logger.info("Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

def start_bot_in_thread():
    """Starts the Telegram bot polling in a separate thread."""
    logger.info("Starting Telegram Bot Polling in a separate thread.")
    bot_thread = threading.Thread(target=run_bot_polling)
    bot_thread.daemon = True
    bot_thread.start()
    return bot_thread

if __name__ == "__main__":
    # For a simple prototype, we can run the bot in a separate thread
    # and the API server in the main thread.
    # NOTE: In a production environment, you would typically use webhooks
    # for the bot and a process manager (like systemd or supervisor)
    # to manage both the API and the bot process.
    
    # Start the bot in a separate thread
    bot_thread = start_bot_in_thread()
    
    # Start the API server in the main thread
    start_api_server()
