import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import re, requests
from yt_dlp import YoutubeDL

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

YOUTUBE_PATTERNS = [r"https?://(www\.)?(youtube\.com|youtu\.be)/\S+"]
INSTAGRAM_PATTERNS = [r"https?://(www\.)?instagram\.com/\S+"]
FACEBOOK_PATTERNS = [r"https?://(www\.)?facebook\.com/\S+"]

def extract_links(text): return re.findall(r"https?://\S+", text)

def detect_platform(url):
    for p in YOUTUBE_PATTERNS:
        if re.match(p, url): return "youtube"
    for p in INSTAGRAM_PATTERNS:
        if re.match(p, url): return "instagram"
    for p in FACEBOOK_PATTERNS:
        if re.match(p, url): return "facebook"
    return "unknown"

def download_instagram(url):
    try:
        apis = [
            "https://saveig.app/api/ajaxSearch",
            "https://instasupersave.com/api/convert"
        ]
        for api in apis:
            r = requests.post(api, data={"q": url}, timeout=10)
            if "medias" in r.text:
                return [m["url"] for m in r.json().get("medias", []) if m.get("url")]
    except:
        pass
    return []

def download_facebook(url):
    try:
        r = requests.post("https://snapsave.app/action.php", data={"url": url})
        return [l.replace("\\", "") for l in re.findall(r'https:\/\/[^\"]+mp4', r.text)]
    except:
        return []

def download_youtube(url):
    try:
        ydl_opts = {'format': 'best[ext=mp4]', 'quiet': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get('filesize') and info['filesize'] > 49 * 1024 * 1024:
                return [info['url'], 'too_large']
            return [info['url']]
    except:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me YouTube, Instagram, or Facebook links.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    links = extract_links(text)
    for link in links:
        platform = detect_platform(link)
        await update.message.reply_text(f"🔍 Checking ({platform}): {link}")
        media_urls = []
        if platform == "youtube":
            media_urls = download_youtube(link)
        elif platform == "instagram":
            media_urls = download_instagram(link)
        elif platform == "facebook":
            media_urls = download_facebook(link)
        if not media_urls:
            await update.message.reply_text(f"❌ Failed to fetch media from {platform.title()}. Link may be private or unsupported.")
        else:
            if 'too_large' in media_urls:
                await update.message.reply_text(f"⚠️ File is too large to send via Telegram.\n🔗 Direct link: {media_urls[0]}")
            else:
                for media in media_urls:
                    if '.mp4' in media:
                        await update.message.reply_video(media)
                    else:
                        await update.message.reply_photo(media)

if __name__ == '__main__':
    try:
        from keep_alive import keep_alive
        keep_alive()
    except:
        pass
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()
