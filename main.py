import os
import pymongo
from flask import Flask, send_file
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ───── ENV VARIABLES ─────
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
FQDN = os.getenv("FQDN", "https://your-default-domain.com")  # Set your Render domain here!

# ───── INITIALIZE BOT ─────
bot = Client(
    "FileBot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# ───── MONGODB ─────
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["telegram_file_bot"]
files_collection = db["files"]
users_collection = db["users"]

# ───── FLASK APP ─────
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/download/<file_id>")
def serve_file(file_id):
    file_data = files_collection.find_one({"file_id": file_id})
    if not file_data:
        return "⚠️ File not found!", 404
    
    file_path = file_data.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return "⚠️ File not found on server!", 404
    
    return send_file(file_path, as_attachment=True)  # Set as_attachment=False for streaming

def run_flask():
    print(f"🌐 FQDN set to: {FQDN}")  # Debugging print
    app.run(host="0.0.0.0", port=10000)

# ───── PYROGRAM HANDLERS ─────
@bot.on_message(filters.command("start"))
def start_handler(client, message):
    user_id = message.from_user.id
    users_collection.update_one(
        {"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True
    )
    
    message.reply_text(
        "✅ Bot is alive!\nSend me a file to generate a direct download link.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Stats", callback_data="stats")]
        ])
    )

@bot.on_callback_query()
def callback_handler(client, callback_query):
    if callback_query.data == "stats":
        user_count = users_collection.count_documents({})
        file_count = files_collection.count_documents({})
        callback_query.message.reply_text(
            f"📊 Total Users: {user_count}\n"
            f"📂 Total Files: {file_count}"
        )

# ───── FILE HANDLER ─────
@bot.on_message(filters.document | filters.video | filters.audio | filters.photo)
def media_handler(client, message):
    media = message.document or message.video or message.audio or message.photo

    if not media:
        print("❌ No media detected")
        return
    
    file_id = media.file_id
    file_name = getattr(media, "file_name", f"file_{file_id}")

    # Ensure downloads folder exists
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{file_id}"

    # Download file
    print(f"📥 Downloading file: {file_name} ({file_id})...")
    client.download_media(message, file_path)
    print(f"✅ Download complete: {file_path}")

    # Generate public link
    file_link = f"{FQDN}/download/{file_id}"
    print(f"🔗 File link generated: {file_link}")

    # Store in database
    files_collection.update_one(
        {"file_id": file_id},
        {"$set": {"file_name": file_name, "file_path": file_path}},
        upsert=True
    )

    # Send response with download link
    buttons = [
        [InlineKeyboardButton("▶️ Stream", url=file_link)],
        [InlineKeyboardButton("📥 Download", url=file_link)],
        [InlineKeyboardButton("🔗 Get File Link", url=file_link)]
    ]

    message.reply_text(
        f"**File:** {file_name}\n📥 [Download File]({file_link})",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

# ───── MAIN ─────
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()
