import telebot
import os
import schedule
import time
import threading
from telebot import types
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

# --- File Storage (Add your files and series here) ---
FILES = {
    "coolie": {
        "type": "single",
        "file_id": "BQACAgUAAxkBAAIBMGjgtNpnsd5f5veDMrXehMPGfpHGAAL5GAACw9OAVe99IbZ3jy-aNgQ"
    },
    # Example of a series
    "got": {
        "type": "series",
        "title": "Game of Thrones",
        "seasons": {
            "got_s1": "Season 1",
            "got_s2": "Season 2",
        }
    },
    "got_s1": { "type": "single", "file_id": "FILE_ID_FOR_SEASON_1" },
    "got_s2": { "type": "single", "file_id": "FILE_ID_FOR_SEASON_2" },
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


# --- Bot Command and Callback Handlers ---

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

    if user_id in user_usage:
        bot.reply_to(message, "❌ You have already claimed your one file for this session.")
        return

    item = FILES[file_key]
    if item["type"] == "series":
        send_series_menu(message, file_key)
    else:
        send_file_and_finalize(message, file_key)


def send_series_menu(message, series_key):
    """Sends a message with season selection buttons."""
    series = FILES[series_key]
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for season_key, season_name in series["seasons"].items():
        # Pass the season key in the callback data
        buttons.append(types.InlineKeyboardButton(season_name, callback_data=f"getfile:{season_key}"))
    markup.add(*buttons)
    bot.send_message(message.chat.id, f"Please select a season for **{series['title']}**:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("getfile:"))
def handle_file_request(call):
    """Handles button clicks for series and single files."""
    user_id = call.from_user.id
    file_key = call.data.split(":")[1]

    if user_id in user_usage:
        bot.answer_callback_query(call.id, "❌ You have already claimed your one file.", show_alert=True)
        return

    # Delete the season selection message for a cleaner interface
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_file_and_finalize(call.message, file_key)


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
        # We start a new thread so the bot isn't blocked while waiting
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

