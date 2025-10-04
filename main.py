import telebot
import os
import schedule
import time
import threading
from keep_alive import keep_alive

# --- Configuration ---
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID_STR = os.environ.get('ADMIN_USER_ID')

# A check to ensure secrets are set on Render
if not all([API_TOKEN, ADMIN_USER_ID_STR]):
    raise ValueError("FATAL ERROR: Both TELEGRAM_BOT_TOKEN and ADMIN_USER_ID must be set in Render's Environment Variables.")

try:
    ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
except ValueError:
    raise ValueError("FATAL ERROR: ADMIN_USER_ID must be a valid integer.")

bot = telebot.TeleBot(API_TOKEN)

# This dictionary tracks users who have already received a file.
user_usage = {}

# --- File Storage (Add your single movie files here) ---
FILES = {
    "fall": {
        "file_id": "BQACAgUAAxkBAAIBRmjgt53aF_5Iee1oapfXORT-8ZYRAAKtGgACNQuoVYWDs9gHXC0mNgQ"
    },
    # Add more movies here, e.g.:
    # "movie2": { "file_id": "ANOTHER_FILE_ID_HERE" }
}


# --- Auto-Delete and Daily Reset Schedulers ---

def schedule_message_deletion(chat_id, message_id):
    """Waits 10 minutes and then deletes the specified message."""
    time.sleep(600)  # 10 minutes = 600 seconds
    try:
        bot.delete_message(chat_id, message_id)
        print(f"Successfully deleted message {message_id} from chat {chat_id}.")
    except Exception as e:
        print(f"Could not delete message {message_id} from chat {chat_id}: {e}")

def reset_user_sessions():
    """Resets the user usage dictionary daily."""
    global user_usage
    print("--- SCHEDULER: Resetting all user sessions... ---")
    user_usage = {}
    print("--- SESSIONS CLEARED ---")

schedule.every().day.at("00:00", "UTC").do(reset_user_sessions)

def run_scheduler():
    """Runs the daily reset scheduler in a background thread."""
    while True:
        schedule.run_pending()
        time.sleep(1)


# --- Bot Command Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) == 1:
        bot.reply_to(message, "👋 Welcome! Please use a special link to get a file.")
        return

    file_key = args[1]

    if file_key not in FILES:
        bot.reply_to(message, "❌ Invalid or expired file link.")
        return



    # Since there are no series, we directly send the file.
    send_file_and_finalize(message, file_key)


def send_file_and_finalize(message, file_key):
    """Sends the file, adds the warning, and schedules deletion."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id in user_usage: # Final check
        return

    try:
        file_id = FILES[file_key]['file_id']

        # --- Warning Message ---
        caption_text = (
            f"⚠️ **Note:** This File/Video will be deleted in 10 mins ❌ (Due to Copyright Issues).\n\n"
            f"Please forward this to your **Saved Messages** and start your download there."
        )

        sent_message = bot.send_document(chat_id, file_id, caption=caption_text, parse_mode="Markdown")

        # --- Schedule Deletion ---
        deletion_thread = threading.Thread(target=schedule_message_deletion, args=(chat_id, sent_message.message_id))
        deletion_thread.start()

        user_usage[user_id] = True
        bot.send_message(chat_id, "You have received your file. Access is now complete.")

    except Exception as e:
        print(f"Error in send_file_and_finalize for key {file_key}: {e}")
        bot.send_message(chat_id, "❌ An error occurred while sending the file.")


@bot.message_handler(content_types=['document', 'video', 'audio'])
def get_file_id(message):
    """Admin-only function to get file IDs."""
    if message.from_user.id == ADMIN_USER_ID and message.chat.type == 'private':
        file_id = ""
        if message.document: file_id = message.document.file_id
        elif message.video: file_id = message.video.file_id
        elif message.audio: file_id = message.audio.file_id
        reply_text = f"New File ID Found!\n\n**ID:** `{file_id}`"
        bot.reply_to(message, reply_text, parse_mode="Markdown")


# --- Main Bot Execution ---
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    keep_alive() # Starts the Flask web server in a thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    print("✔️ Daily reset scheduler started.")
    print("✔️ Bot is now polling for messages.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

