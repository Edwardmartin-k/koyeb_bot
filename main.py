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

# --- File Storage ---
# Using non-sequential, randomized keys to prevent users from guessing the next part.
# The deeplink you share will now use these secure keys.
FILES = {
    # --- Season 1 ---
    "got_s1p1_aK9sL2": { "file_ids": ["BQACAgUAAxkBAAMSa03u0gfcHV-gX2wQbVcNA9_CK4AAvgYAALD04BVgwp7S3LKzt42BA", "BQACAgUAAxkBAAMQA03uIGkpVqVbw9Yu01MiIAgrshYAAVkYAALD04BVg1Mk5bP00Ic2BA", "BQACAgUAAxkBAAMUA03uOJtq2cEZpEVvoa_dfQw3Pr4AAgyYAALD04BVr0njKIM1dAQ2BA"] },
    "got_s1p2_zX7vB5": { "file_ids": ["BQACAgUAAxkBAAMVA03uOtbu1dzQ3k1vWToUZGidnjYAAh0ZAJ-D09e1Iz42BA", "BQACAgUAAxkBAAMWA03uOr6fujlrt3gm5m8XQ1ebScwAAiwcAAJPZahV_G07u50K-fA2BA", "BQACAgUAAxkBAAMXA03u0qcJaGa1SRgcoU9G0_pPvGEAAjQcAAJPZahVeF1oxxauffK2BA"] },
    "got_s1p3_nC6mJ8": { "file_ids": ["BQACAgUAAxkBAAMYA03uOr7ABfPefbeI8Hc3JDrNhYIAAjkcAAJPZahV1xvrdKt_Gmg2BA", "BQACAgUAAxkBAAMZA03u0vSeuyprQD9t7H9vxea_kQUAAj4cAAJPZahV5J4lUPqxuPc2BA", "BQACAgUAAxkBAAMaa03u0kpH8UYpId9oAAG5ZBYXZC8iAAJCHAACT82oVbgiCL3SaKrQNgQ", "BQACAgUAAxkBAAMba03uOr_acPkUkv5Xrn6H3AZPm-UAAkEcAJPZahVzahVsAVfBjjtII2BA"] },

    # --- Season 2 ---
    "got_s2p1_pQ5fG1": { "file_ids": ["FILE_ID_FOR_S2_EP1", "FILE_ID_FOR_S2_EP2", "FILE_ID_FOR_S2_EP3"] },
    "got_s2p2_kL4hT9": { "file_ids": ["FILE_ID_FOR_S2_EP4", "FILE_ID_FOR_S2_EP5", "FILE_ID_FOR_S2_EP6"] },
    "got_s2p3_jM3sR7": { "file_ids": ["FILE_ID_FOR_S2_EP7", "FILE_ID_FOR_S2_EP8", "FILE_ID_FOR_S2_EP9", "FILE_ID_FOR_S2_EP10"] },

    # --- Season 3 ---
    "got_s3p1_yU2vE4": { "file_ids": ["FILE_ID_FOR_S3_EP1", "FILE_ID_FOR_S3_EP2", "FILE_ID_FOR_S3_EP3"] },
    "got_s3p2_wA1zD3": { "file_ids": ["FILE_ID_FOR_S3_EP4", "FILE_ID_FOR_S3_EP5", "FILE_ID_FOR_S3_EP6"] },
    "got_s3p3_sB9xQ2": { "file_ids": ["FILE_ID_FOR_S3_EP7", "FILE_ID_FOR_S3_EP8", "FILE_ID_FOR_S3_EP9", "FILE_ID_FOR_S3_EP10"] },

    # --- Season 4 ---
    "got_s4p1_rF8wP1": { "file_ids": ["FILE_ID_FOR_S4_EP1", "FILE_ID_FOR_S4_EP2", "FILE_ID_FOR_S4_EP3"] },
    "got_s4p2_tG7vO9": { "file_ids": ["FILE_ID_FOR_S4_EP4", "FILE_ID_FOR_S4_EP5", "FILE_ID_FOR_S4_EP6"] },
    "got_s4p3_uH6uN8": { "file_ids": ["FILE_ID_FOR_S4_EP7", "FILE_ID_FOR_S4_EP8", "FILE_ID_FOR_S4_EP9", "FILE_ID_FOR_S4_EP10"] },

    # --- Season 5 ---
    "got_s5p1_iJ5tM7": { "file_ids": ["FILE_ID_FOR_S5_EP1", "FILE_ID_FOR_S5_EP2", "FILE_ID_FOR_S5_EP3"] },
    "got_s5p2_oK4sL6": { "file_ids": ["FILE_ID_FOR_S5_EP4", "FILE_ID_FOR_S5_EP5", "FILE_ID_FOR_S5_EP6"] },
    "got_s5p3_pL3rK5": { "file_ids": ["FILE_ID_FOR_S5_EP7", "FILE_ID_FOR_S5_EP8", "FILE_ID_FOR_S5_EP9", "FILE_ID_FOR_S5_EP10"] },

    # --- Season 6 ---
    "got_s6p1_qM2qJ4": { "file_ids": ["FILE_ID_FOR_S6_EP1", "FILE_ID_FOR_S6_EP2", "FILE_ID_FOR_S6_EP3"] },
    "got_s6p2_rN1pI3": { "file_ids": ["FILE_ID_FOR_S6_EP4", "FILE_ID_FOR_S6_EP5", "FILE_ID_FOR_S6_EP6"] },
    "got_s6p3_sO9oH2": { "file_ids": ["FILE_ID_FOR_S6_EP7", "FILE_ID_FOR_S6_EP8", "FILE_ID_FOR_S6_EP9", "FILE_ID_FOR_S6_EP10"] },

    # --- Season 7 ---
    "got_s7p1_tP8nG1": { "file_ids": ["FILE_ID_FOR_S7_EP1", "FILE_ID_FOR_S7_EP2", "FILE_ID_FOR_S7_EP3"] },
    "got_s7p2_uQ7mF9": { "file_ids": ["FILE_ID_FOR_S7_EP4", "FILE_ID_FOR_S7_EP5"] },
    "got_s7p3_vR6lE8": { "file_ids": ["FILE_ID_FOR_S7_EP6", "FILE_ID_FOR_S7_EP7"] },

    # --- Season 8 ---
    "got_s8p1_wS5kD7": { "file_ids": ["FILE_ID_FOR_S8_EP1", "FILE_ID_FOR_S8_EP2"] },
    "got_s8p2_xT4jC6": { "file_ids": ["FILE_ID_FOR_S8_EP3", "FILE_ID_FOR_S8_EP4"] },
    "got_s8p3_yU3iB5": { "file_ids": ["FILE_ID_FOR_S8_EP5", "FILE_ID_FOR_S8_EP6"] },
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
def handle_start(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) == 1:
        bot.reply_to(message, "👋 Welcome! Please use a special link from one of our channels to get a file.")
        return

    file_key = args[1]

    if file_key not in FILES:
        bot.reply_to(message, "❌ Invalid or expired file link.")
        return

    if user_id in user_usage:
        bot.reply_to(message, "❌ You have already claimed your one file for this session.")
        return

    send_files_and_finalize(message, file_key)


def send_files_and_finalize(message, file_key):
    """Sends one or more files, adds warnings, and schedules deletion for each."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id in user_usage: # Final check
        return

    try:
        file_id_list = FILES[file_key].get('file_ids', [])
        if not file_id_list:
            raise ValueError("No file_ids found for this key.")

        bot.send_message(chat_id, f"📂 Preparing your request... You will receive {len(file_id_list)} file(s).")
        time.sleep(2) # Small delay for a better user experience

        for i, file_id in enumerate(file_id_list):
            # --- Warning Message ---
            caption_text = (
                f"📎 File {i+1} of {len(file_id_list)}\n\n"
                f"⚠️ **Note:** This File/Video will be deleted in 10 mins ❌ (Due to Copyright Issues).\n\n"
                f"Please forward this to your **Saved Messages** and start your download there."
            )

            sent_message = bot.send_document(chat_id, file_id, caption=caption_text, parse_mode="Markdown")

            # --- Schedule Deletion for each file ---
            deletion_thread = threading.Thread(target=schedule_message_deletion, args=(chat_id, sent_message.message_id))
            deletion_thread.start()
            time.sleep(1) # Prevents Telegram from rate-limiting the bot

        user_usage[user_id] = True
        bot.send_message(chat_id, "✅ All files have been sent. Access is now complete.")

    except Exception as e:
        print(f"Error in send_files_and_finalize for key {file_key}: {e}")
        bot.send_message(chat_id, "❌ An error occurred while sending the files.")


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

