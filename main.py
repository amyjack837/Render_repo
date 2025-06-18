import os
import re
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from keep_alive import keep_alive
from dotenv import load_dotenv
import yt_dlp as youtube_dl

load_dotenv()
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")

def extract_links(text):
    return re.findall(r"https?://\S+", text)

def detect_platform(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    elif "facebook.com" in url:
        return "facebook"
    return "unknown"

def download_youtube(url):
    try:
        ydl_opts = {
            'quiet': True,
            'format': 'best[ext=mp4]/best',
            'skip_download': True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return [info['url']]
    except Exception as e:
        logging.error(f"[YouTube ERROR] {e}")
    return []

def download_instagram(url):
    try:
        r = requests.post("https://saveig.app/api/ajaxSearch", data={"q": url}, timeout=10)
        if r.status_code == 200 and "medias" in r.text:
            data = r.json()
            return [m['url'] for m in data.get("medias", []) if "url" in m]
    except Exception as e:
        logging.error(f"[Instagram ERROR] {e}")
    return []

def download_facebook(url):
    try:
        r = requests.post("https://snapsave.app/action.php", data={"url": url})
        if r.status_code == 200:
            matches = re.findall(r'https:\/\/[^"]+\.mp4', r.text)
            return matches
    except Exception as e:
        logging.error(f"[Facebook ERROR] {e}")
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a YouTube, Instagram or Facebook link.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    links = extract_links(text)
    for link in links:
        platform = detect_platform(link)
        await update.message.reply_text(f"🔍 Fetching media from ({platform})...")
        media_urls = []
        if platform == "youtube":
            media_urls = download_youtube(link)
        elif platform == "instagram":
            media_urls = download_instagram(link)
        elif platform == "facebook":
            media_urls = download_facebook(link)

        if not media_urls:
            await update.message.reply_text(f"❌ Failed to fetch media from {platform.title()}.")
        else:
            for media in media_urls:
                if media.endswith(".mp4") or "googlevideo.com" in media:
                    await update.message.reply_text(f"📽️ Download video:\n{media}")
                else:
                    await update.message.reply_photo(media)

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ Bot is running...")
    app.run_polling()
