# Don't Remove Credit Tg - @Tushar0125
# Ask Doubt on telegram @Tushar0125

import os
import re
import sys
import json
import time
import m3u8
import aiohttp
import asyncio
import requests
import subprocess
import urllib.parse
import cloudscraper
import datetime
import random
import ffmpeg
import logging
import yt_dlp
from subprocess import getstatusoutput
from aiohttp import web
from core import *
from urllib.parse import urlparse, parse_qs, urljoin
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import yt_dlp as youtube_dl
import cloudscraper
import m3u8
import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL
from aiohttp import ClientSession
from pyromod import listen
from subprocess import getstatusoutput
from pytube import YouTube

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Import the Database class from db.py
from db import Database, db as db_instance_placeholder

cookies_file_path = os.getenv("COOKIES_FILE_PATH", "youtube_cookies.txt")

cpimg = "https://files.catbox.moe/v9z1n7.jpg"

async def show_random_emojis(message):
    emojis = ['🎊', '🔮', '😎', '⚡️', '🚀', '✨', '💥', '🎉', '🥂', '�', '🦠', '🤖', '❤️‍🔥', '🕊️', '💃', '🥳','🅰','🦋']
    emoji_message = await message.reply_text(' '.join(random.choices(emojis, k=1)))
    return emoji_message

# Define the owner's user ID
OWNER_ID = 7062964338

# Initialize the database instance globally
try:
    db = Database(DATABASE_URL)
except Exception as e:
    logging.error(f"Failed to initialize database: {e}")
    sys.exit(1)

AUTH_CHANNEL = -1002752608747

# Function to check if a user is authorized
def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or db.is_sudo_user(user_id) or user_id == AUTH_CHANNEL

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN)

# ==================== NEW: ENCRYPTED URL DOWNLOAD FUNCTIONS ====================

async def download_encrypted_video(url, output_filename="video.mp4"):
    """
    Download video from encrypted URL (like sarvamcareerinstitute.in)
    Returns: (success: bool, filepath: str)
    """
    try:
        print(f"Fetching encrypted video URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://sarvamcareerinstitute.in/'
        }
        
        # Use aiohttp for async download with increased timeout
        timeout = aiohttp.ClientTimeout(total=600)  # 10 minutes timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                
                content_type = response.headers.get('Content-Type', '')
                print(f"Content Type: {content_type}")
                
                # If direct video, download it
                if 'video' in content_type or 'octet-stream' in content_type:
                    print(f"Downloading video to {output_filename}...")
                    total_size = 0
                    with open(output_filename, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                            if chunk:
                                f.write(chunk)
                                total_size += len(chunk)
                    
                    print(f"✓ Video downloaded successfully: {output_filename} ({total_size / (1024*1024):.2f} MB)")
                    
                    # Verify file exists and has content
                    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                        return True, output_filename
                    else:
                        print(f"❌ File verification failed")
                        return False, None
                
                # If HTML response, try to extract video URL
                elif 'text/html' in content_type:
                    html_content = await response.text()
                    
                    # Try to find video source URLs
                    video_patterns = [
                        r'<source[^>]+src=[\'"](.*?)[\'"]',
                        r'<video[^>]+src=[\'"](.*?)[\'"]',
                        r'src:\s*[\'"]([^\'"]+\.m3u8[^\'"]*)[\'"]',
                        r'file:\s*[\'"]([^\'"]+)[\'"]',
                    ]
                    
                    video_url = None
                    for pattern in video_patterns:
                        matches = re.findall(pattern, html_content, re.IGNORECASE)
                        if matches:
                            video_url = matches[0]
                            break
                    
                    if video_url:
                        # Make absolute URL if relative
                        if not video_url.startswith('http'):
                            base_url = url.rsplit('/', 1)[0]
                            video_url = urljoin(base_url, video_url)
                        
                        print(f"Found video URL: {video_url}")
                        
                        # Download using ffmpeg for m3u8 or direct download
                        if '.m3u8' in video_url:
                            print("Detected HLS stream, using yt-dlp...")
                            # Use yt-dlp instead of ffmpeg for better compatibility
                            return await download_with_ytdlp_async(video_url, output_filename)
                        else:
                            print("Downloading video file...")
                            async with session.get(video_url, headers=headers) as vid_response:
                                vid_response.raise_for_status()
                                total_size = 0
                                with open(output_filename, 'wb') as f:
                                    async for chunk in vid_response.content.iter_chunked(1024 * 1024):
                                        if chunk:
                                            f.write(chunk)
                                            total_size += len(chunk)
                            print(f"✓ Video downloaded successfully: {output_filename} ({total_size / (1024*1024):.2f} MB)")
                            
                            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                                return True, output_filename
                            else:
                                return False, None
                    else:
                        print("❌ Could not find video URL in response")
                        return False, None
                
                else:
                    print(f"❌ Unexpected content type: {content_type}")
                    return False, None
                    
    except asyncio.TimeoutError:
        print(f"❌ Download timeout for encrypted video")
        return False, None
    except Exception as e:
        print(f"❌ Error downloading encrypted video: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

async def download_with_ytdlp_async(url, output_filename):
    """Download video using yt-dlp (for HLS streams and other formats) - async version"""
    try:
        print("Downloading with yt-dlp...")
        # Remove extension for yt-dlp
        name_without_ext = output_filename.replace('.mp4', '')
        
        cmd = [
            'yt-dlp',
            '-f', 'best',
            '-o', f'{name_without_ext}.mp4',
            url,
            '--no-warnings',
            '--no-check-certificate'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(f'{name_without_ext}.mp4'):
            print(f"✓ Video downloaded successfully: {name_without_ext}.mp4")
            return True, f'{name_without_ext}.mp4'
        else:
            print(f"❌ yt-dlp error: {stderr.decode()}")
            return False, None
        
    except FileNotFoundError:
        print("❌ yt-dlp not found. Please install yt-dlp")
        return False, None
    except Exception as e:
        print(f"❌ yt-dlp error: {e}")
        return False, None

def is_encrypted_url(url):
    """Check if URL is an encrypted URL that needs special handling"""
    encrypted_patterns = [
        'sarvamcareerinstitute.in/serve_video',
        'serve_videouweb.php',
        # Add more patterns here for other encrypted URL types
    ]
    return any(pattern in url for pattern in encrypted_patterns)

# ==================== END: ENCRYPTED URL DOWNLOAD FUNCTIONS ====================

# Sudo command to add/remove sudo users
@bot.on_message(filters.command("sudo"))
async def sudo_command(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await message.reply_text("**🚫 You are not authorized to use this command.**")
        return

    try:
        args = message.text.split(" ", 2)
        if len(args) < 3:
            await message.reply_text("**Usage:** `/sudo add <user_id>` or `/sudo remove <user_id>`")
            return

        action = args[1].lower()
        target_user_id = int(args[2])
        target_username = None
        if message.reply_to_message and message.reply_to_message.from_user:
            target_username = message.reply_to_message.from_user.username

        if action == "add":
            if db.add_sudo_user(target_user_id, target_username):
                await message.reply_text(f"**✅ User `{target_user_id}` added to sudo list.**")
            else:
                await message.reply_text(f"**⚠️ User `{target_user_id}` is already in the sudo list.**")
        elif action == "remove":
            if target_user_id == OWNER_ID:
                await message.reply_text("**🚫 The owner cannot be removed from the sudo list.**")
            elif db.remove_sudo_user(target_user_id):
                await message.reply_text(f"**✅ User `{target_user_id}` removed from sudo list.**")
            else:
                await message.reply_text(f"**⚠️ User `{target_user_id}` is not in the sudo list.**")
        else:
            await message.reply_text("**Usage:** `/sudo add <user_id>` or `/sudo remove <user_id>`")
    except ValueError:
        await message.reply_text("**Error:** Invalid user ID. Please provide a valid integer.")
    except Exception as e:
        await message.reply_text(f"**Error:** {str(e)}")

# Inline keyboard for start command
keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🇮🇳ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ🇮🇳" ,url=f"https://t.me/ItsPikachubot") ],
                    [
                    InlineKeyboardButton("🔔ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ🔔" ,url="https://t.me/Medicoarmy") ],
                    [
                    InlineKeyboardButton("🦋ғᴏʟʟᴏᴡ ᴜs🦋" ,url="https://t.me/Medicoarmy")
                ],
            ]
      )

# Image URLs for the random image feature
image_urls = [
    "https://files.catbox.moe/v9z1n7.jpg",
]
random_image_url = random.choice(image_urls)
caption = (
        "**ʜᴇʟʟᴏ💋**\n\n"
        "➪  **ɪ ᴀᴍ ᴛxᴛ ᴛᴏ ᴠɪᴅᴇᴏ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ.**\n"
        "➪  **ғᴏʀ ᴜsᴇ ᴍᴇ sᴇɴᴅ /txt.\n"
        "➪  **ғᴏʀ ɢᴜɪᴅᴇ sᴇɴᴅ /help."
)

# Start command handler
@bot.on_message(filters.command(["start"]))
async def start_command(bot: Client, message: Message):
    await bot.send_photo(chat_id=message.chat.id, photo=random_image_url, caption=caption, reply_markup=keyboard)

# Stop command handler
@bot.on_message(filters.command("stop"))
async def restart_handler(_, m: Message):
    await m.reply_text("<b>ꜱᴛᴏᴘᴘᴇᴅ</b>🚦", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command("restart"))
async def restart_handler(_, m):
    if not is_authorized(m.from_user.id):
        await m.reply_text("**🚫 You are not authorized to use this command.**")
        return
    await m.reply_text("🔮Restarted🔮", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

COOKIES_FILE_PATH = "youtube_cookies.txt"

@bot.on_message(filters.command("cookies") & filters.private)
async def cookies_handler(client: Client, m: Message):
    if not is_authorized(m.from_user.id):
        await m.reply_text("🚫 You are not authorized to use this command.")
        return
    await m.reply_text(
        "𝗣𝗹𝗲𝗮𝘀𝗲 𝗨𝗽𝗹𝗼𝗮𝗱 𝗧𝗵𝗲 𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝗙𝗶𝗹𝗲 (.𝘁𝘅𝘁 𝗳𝗼𝗿𝗺𝗮𝘁).",
        quote=True
    )

    try:
        input_message: Message = await client.listen(m.chat.id)

        if not input_message.document or not input_message.document.file_name.endswith(".txt"):
            await m.reply_text("Invalid file type. Please upload a .txt file.")
            return

        downloaded_path = await input_message.download()

        with open(downloaded_path, "r") as uploaded_file:
            cookies_content = uploaded_file.read()

        with open(COOKIES_FILE_PATH, "w") as target_file:
            target_file.write(cookies_content)

        await input_message.reply_text(
            "✅ 𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝗨𝗽𝗱𝗮𝘁𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆.\n\n📂 𝗦𝗮𝘃𝗲𝗱 𝗜𝗻 youtube_cookies.txt."
        )

    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

import tempfile

@bot.on_message(filters.command('e2t'))
async def edit_txt(client, message: Message):
    await message.reply_text(
        "🎉 **Welcome to the .txt File Editor!**\n\n"
        "Please send your `.txt` file containing subjects, links, and topics."
    )

    input_message: Message = await bot.listen(message.chat.id)
    if not input_message.document:
        await message.reply_text("🚨 **Error**: Please upload a valid `.txt` file.")
        return

    file_name = input_message.document.file_name.lower()

    with tempfile.TemporaryDirectory() as tmpdir:
        uploaded_file_path = os.path.join(tmpdir, file_name)
        uploaded_file = await input_message.download(uploaded_file_path)

        await message.reply_text(
            "📄 **Send your .txt file name, or type 'd' for the default file name.**"
        )

        user_response: Message = await bot.listen(message.chat.id)
        if user_response.text:
            user_response_text = user_response.text.strip().lower()
            if user_response_text == 'd':
                final_file_name = file_name
            else:
                final_file_name = user_response_text + '.txt'
        else:
            final_file_name = file_name

        try:
            with open(uploaded_file, 'r', encoding='utf-8') as f:
                content = f.readlines()
        except Exception as e:
            await message.reply_text(f"🚨 **Error**: Unable to read the file.\n\nDetails: {e}")
            return

        subjects = {}
        current_subject = None
        for line in content:
            line = line.strip()
            if line and ":" in line:
                title, url = line.split(":", 1)
                title, url = title.strip(), url.strip()

                if title in subjects:
                    subjects[title]["links"].append(url)
                else:
                    subjects[title] = {"links": [url], "topics": []}

                current_subject = title
            elif line.startswith("-") and current_subject:
                subjects[current_subject]["topics"].append(line.strip("- ").strip())

        sorted_subjects = sorted(subjects.items())
        for title, data in sorted_subjects:
            data["topics"].sort()

        try:
            final_file_path = os.path.join(tmpdir, final_file_name)
            with open(final_file_path, 'w', encoding='utf-8') as f:
                for title, data in sorted_subjects:
                    for link in data["links"]:
                        f.write(f"{title}:{link}\n")
                    for topic in data["topics"]:
                        f.write(f"- {topic}\n")
        except Exception as e:
            await message.reply_text(f"🚨 **Error**: Unable to write the edited file.\n\nDetails: {e}")
            return

        try:
            await message.reply_document(
                document=final_file_path,
                caption="📥**ᴇᴅɪᴛᴇᴅ ʙʏ ᴘɪᴋᴀᴄʜᴜ**"
            )
        except Exception as e:
            await message.reply_text(f"🚨 **Error**: Unable to send the file.\n\nDetails: {e}")

from pytube import Playlist
import youtube_dl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def get_videos_with_ytdlp(url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                title = result.get('title', 'Unknown Title')
                videos = {}
                for entry in result['entries']:
                    video_url = entry.get('url', None)
                    video_title = entry.get('title', None)
                    if video_url:
                        videos[video_title if video_title else "Unknown Title"] = video_url
                return title, videos
            return None, None
    except Exception as e:
        logging.error(f"Error retrieving videos: {e}")
        return None, None

def save_to_file(videos, name):
    filename = f"{sanitize_filename(name)}.txt"
    with open(filename, 'w', encoding='utf-8') as file:
        for title, url in videos.items():
            if title == "Unknown Title":
                file.write(f"{url}\n")
            else:
                file.write(f"{title}: {url}\n")
    return filename

@bot.on_message(filters.command('yt2txt'))
async def ytplaylist_to_txt(client: Client, message: Message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        await message.reply_text("**🚫 You are not authorized to use this command.\n\n🫠 This Command is only for owner.**")
        return

    await message.delete()
    editable = await message.reply_text("📥 **Please enter the YouTube Playlist Url :**")
    input_msg = await client.listen(editable.chat.id)
    youtube_url = input_msg.text
    await input_msg.delete()
    await editable.delete()

    title, videos = get_videos_with_ytdlp(youtube_url)
    if videos:
        file_name = save_to_file(videos, title)
        await message.reply_document(
            document=file_name,
            caption=f"`{title}`\n\n<b>📥 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : ᴘɪᴋᴀᴄʜᴜ</b>"
        )
        os.remove(file_name)
    else:
        await message.reply_text("⚠️ **Unable to retrieve videos. Please check the URL.**")

@bot.on_message(filters.command("userlist") & filters.user(OWNER_ID))
async def list_users(client: Client, msg: Message):
    sudo_users = db.get_sudo_users()
    if sudo_users:
        users_list = "\n".join([f"User ID : `{user_id}`" for user_id in sudo_users])
        await msg.reply_text(f"SUDO_USERS :\n{users_list}")
    else:
        await msg.reply_text("No sudo users.")

@bot.on_message(filters.command("help"))
async def help_command(client: Client, msg: Message):
    help_text = (
        "`/start` - Start the bot⚡\n\n"
        "`/txt` - Download and upload files (sudo)🎬\n\n"
        "`/restart` - Restart the bot🔮\n\n"
        "`/stop` - Stop ongoing process🛑\n\n"
        "`/cookies` - Upload cookies file🪐\n\n"
        "`/e2t` - Edit txt file📝\n\n"
        "`/yt2txt` - Create txt of yt playlist (owner)🗃️\n\n"
        "`/sudo add` - Add user or group or channel (owner)🎊\n\n"
        "`/sudo remove` - Remove user or group or channel (owner)❌\n\n"
        "`/userlist` - List of sudo user or group or channel📜\n\n"
    )
    await msg.reply_text(help_text)

# Upload command handler
@bot.on_message(filters.command(["txt"]))
async def upload(bot: Client, m: Message):
    if not is_authorized(m.chat.id):
        await m.reply_text("**🚫You are not authorized to use this bot.**")
        return

    editable = await m.reply_text(f"📥<b>ꜱᴇɴᴅ ᴛxᴛ ꜰɪʟᴇ</b>")
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    pdf_count = 0
    img_count = 0
    zip_count = 0
    video_count = 0
    encrypted_count = 0

    try:
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")

        links = []
        for i in content:
            if "://" in i:
                url = i.split("://", 1)[1]
                links.append(i.split("://", 1))
                
                # Check if it's an encrypted URL
                if is_encrypted_url(i):
                    encrypted_count += 1
                elif ".pdf" in url:
                    pdf_count += 1
                elif url.endswith((".png", ".jpeg", ".jpg")):
                    img_count += 1
                elif ".zip" in url:
                    zip_count += 1
                else:
                    video_count += 1
        os.remove(x)
    except:
        await m.reply_text("⚠️ɪɴᴠᴀʟɪᴅ ꜰɪʟᴇ ɪɴᴘᴜᴛ")
        os.remove(x)
        return

    await editable.edit(f"`🔗 <b>ᴛᴏᴛᴀʟ ʟɪɴᴋꜱ ꜰᴏᴜɴᴅ ᴀʀᴇ</b> {len(links)}\n\n🖼️ ɪᴍᴀɢᴇꜱ : {img_count}\n📄 ᴘᴅꜰꜱ : {pdf_count}\n📂 ᴢɪᴘꜱ : {zip_count}\n🎞️ ᴠɪᴅᴇᴏꜱ : {video_count}\n🔐 ᴇɴᴄʀʏᴘᴛᴇᴅ : {encrypted_count}\n\nꜱᴇɴᴅ ꜰʀᴏᴍ ᴡʜᴇʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ.`")
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)
    try:
        arg = int(raw_text)
    except:
        arg = 1
    await editable.edit("📚 <b>ᴇɴᴛᴇʀ ʏᴏᴜʀ Bᴀᴛᴄʜ Nᴀᴍᴇ\n\n ꜱᴇɴᴅ `1` ꜰᴏʀ ᴜꜱᴇ ᴅᴇꜰᴀᴜʟᴛ</b> ")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    if raw_text0 == '1':
        b_name = file_name
    else:
        b_name = raw_text0

    await editable.edit("<b>📸 ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ 📸</b>\n➤ `144`\n➤ `240`\n➤ `360`\n➤ `480`\n➤ `720`\n➤ `1080`")
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080"
        else:
            res = "UN"
    except Exception:
            res = "UN"

    await editable.edit("✏️ <b>ᴇɴᴛᴇʀ ʏᴏᴜʀ ɴᴀᴍᴇ</b> \n\n <b>ꜱᴇɴᴅ `1` ꜰᴏʀ ᴜꜱᴇ ᴅᴇꜰᴀᴜʟᴛ</b> ")
    input3: Message = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    credit = "️[️](https://t.me/ItsPikachubot)"
    if raw_text3 == '1':
        CR = '[ᴘɪᴋᴀᴄʜᴜ️](https://t.me/ItsPikachubot)'
    elif raw_text3:
        try:
            text, link = raw_text3.split(',')
            CR = f'[{text.strip()}]({link.strip()})'
        except ValueError:
            CR = raw_text3
    else:
        CR = credit

    await editable.edit("<b>ᴇɴᴛᴇʀ ᴘᴡ ᴛᴏᴋᴇɴ ꜰᴏʀ ᴘᴡ ᴜᴘʟᴏᴀᴅɪɴɢ ᴏʀ ꜱᴇɴᴅ `3` ꜰᴏʀ ᴏᴛʜᴇʀꜱ</b>")
    input4: Message = await bot.listen(editable.chat.id)
    raw_text4 = input4.text
    await input4.delete(True)
    if raw_text4 == '3':
        MR = "token"
    else:
        MR = raw_text4

    await editable.edit("<b>ɴᴏᴡ ꜱᴇɴᴅ ᴛʜᴇ ᴛʜᴜᴍʙ ᴜʀʟ ᴇɢ »</b> https://files.catbox.moe/zgfhrn.jpg\n\n<b>ᴏʀ ɪꜰ ᴅᴏɴ'ᴛ ᴡᴀɴᴛ ᴛʜᴜᴍʙɴᴀɪʟ ꜱᴇɴᴅ = ɴᴏ</b>")
    input6 = message = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = input6.text.strip()
    print(f"📸 Thumbnail input received: {thumb}")

    if thumb.startswith("http://") or thumb.startswith("https://"):
        print(f"✅ Using custom thumbnail URL: {thumb}")
    elif thumb.lower() == "no":
        thumb = "no"
        print("⚡ Using auto-generated thumbnail")
    else:
        thumb = "no"
        print("⚠️ Invalid input, using auto-generated thumbnail")

    summary_text = (
       f"╭──────────────╮\n"
        f"┃  📊 **BATCH INFO** 📊  ┃\n"
        f"╰──────────────╯\n\n"
        f"**Batch Name:** `{b_name}`\n"
        f"**Quality:** `{raw_text2}p`\n"
        f"**Total Links:** `{len(links)}`\n\n"
        f"├ 🎞️ Videos: `{video_count}`\n"
        f"├ 📕 PDFs: `{pdf_count}`\n"
        f"├ 🖼️ Images: `{img_count}`\n"
        f"├ 📂 Zips: `{zip_count}`\n"
        f"├ 🔐 Encrypted: `{encrypted_count}`\n\n"
        f"**Status:** 🔄 Processing...\n\n"
        f"⚡ Bot Made By Pikachu"
    )
    
    pinned_msg = None
    try:
        pinned_msg = await m.reply_text(summary_text, disable_web_page_preview=True)
        await pinned_msg.pin(disable_notification=False)
        logging.info(f"✅ Pinned summary message in chat {m.chat.id}")
    except Exception as e:
        logging.error(f"⚠️ Failed to pin message: {e}")
   
    failed_count = 0
    if len(links) == 1:
        count = 1
    else:
        count = int(raw_text)

    try:
        for i in range(count - 1, len(links)):
            V = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + V

            # ==================== CHECK FOR ENCRYPTED URL ====================
            if is_encrypted_url(url):
                name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
                name = f'{str(count).zfill(3)}) {name1[:60]}'
                
                cc = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.({res}).mp4\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀᴄᴛᴇᴅ Bʏ : {CR}**'
                
                Show = (
                    f"**📥 Status:** `Downloading Encrypted Video...`\n\n"
                    f"**📊 Progress:** `{count}/{len(links)}`\n"
                    f"──────────────────\n"
                    f"🔐 **{name}**\n"
                    f"├ Format: `Encrypted URL`\n"
                    f"├ Quality: `{raw_text2}`\n"
                    f"└ Type: `Special Download`\n"
                    f"──────────────────\n"
                    f"ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ"
                )
                prog = await m.reply_text(Show)
                
                try:
                    # Download encrypted video
                    output_file = f"{name}.mp4"
                    success, filepath = await download_encrypted_video(url, output_file)
                    
                    if success and filepath and os.path.exists(filepath):
                        await prog.delete(True)
                        await helper.send_vid(bot, m, cc, filepath, thumb, name, prog)
                        count += 1
                        time.sleep(1)
                    else:
                        await prog.delete(True)
                        await m.reply_text(f'⚠️ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ꜰᴀɪʟᴇᴅ (Encrypted URL)\n\n'
                                           f'ɴᴀᴍᴇ » `{name}`\n\n'
                                           f'ᴜʀʟ » <a href="{url}">__**Click Here to See Link**__</a>')
                        count += 1
                        failed_count += 1
                        
                except Exception as e:
                    await prog.delete(True)
                    await m.reply_text(f'⚠️ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ꜰᴀɪʟᴇᴅ (Encrypted URL)\n\n'
                                       f'ɴᴀᴍᴇ » `{name}`\n\n'
                                       f'Error: {str(e)}')
                    count += 1
                    failed_count += 1
                
                continue
            # ==================== END ENCRYPTED URL HANDLING ====================

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            elif 'media-cdn.classplusapp.com/drm/' in url:
                url = f"https://dragoapi.vercel.app/video/{url}"

            elif 'videos.classplusapp' in url:
             url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9'}).json()['url']

            elif "tencdn.classplusapp" in url or "media-cdn-alisg.classplusapp.com" in url or "videos.classplusapp" in url or "media-cdn.classplusapp" in url:
             headers = {'Host': 'api.classplusapp.com', 'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9', 'user-agent': 'Mobile-Android', 'app-version': '1.4.37.1', 'api-version': '18', 'device-id': '5d0d17ac8b3c9f51', 'device-details': '2848b866799971ca_2848b8667a33216c_SDK-30', 'accept-encoding': 'gzip'}
             params = (('url', f'{url}'),)
             response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
             url = response.json()['url']

            elif "https://appx-transcoded-videos.livelearn.in/videos/rozgar-data/" in url:
                url = url.replace("https://appx-transcoded-videos.livelearn.in/videos/rozgar-data/", "")
                name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("|", "").replace("@", "@").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
                name = f'{str(count).zfill(3)}) {name1[:60]}'
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "https://appx-transcoded-videos-mcdn.akamai.net.in/videos/bhainskipathshala-data/" in url:
                url = url.replace("https://appx-transcoded-videos-mcdn.akamai.net.in/videos/bhainskipathshala-data/", "")
                name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("|", "").replace("@", "@").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
                name = f'{str(count).zfill(3)}) {name1[:60]}'
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "apps-s3-jw-prod.utkarshapp.com" in url:
                if 'enc_plain_mp4' in url:
                    url = url.replace(url.split("/")[-1], res+'.mp4')

                elif 'Key-Pair-Id' in url:
                    url = None

                elif '.m3u8' in url:
                    q = ((m3u8.loads(requests.get(url).text)).data['playlists'][1]['uri']).split("/")[0]
                    x = url.split("/")[5]
                    x = url.replace(x, "")
                    url = ((m3u8.loads(requests.get(url).text)).data['playlists'][1]['uri']).replace(q+"/", x)

            elif "/master.mpd" in url or "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
             id =  url.split("/")[-2]
             url = f"https://anonymouspwplayer-25261acd1521.herokuapp.com/pw?url={url}&token={raw_text4}"

            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]}'

            if 'khansirvod4.pc.cdn.bitgravity.com' in url:
               parts = url.split('/')
               part1 = parts[1]
               part2 = parts[2]
               part3 = parts[3]
               part4 = parts[4]
               part5 = parts[5]

               print(f"PART1: {part1}")
               print(f"PART2: {part2}")
               print(f"PART3: {part3}")
               print(f"PART4: {part4}")
               print(f"PART5: {part5}")
               url = f"https://kgs-v4.akamaized.net/kgs-cv/{part3}/{part4}/{part5}"

            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

            if "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MzUxMzUzNjIsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiYmt3cmVIWmxZMFUwVXpkSmJYUkxVemw2ZW5Oclp6MDkiLCJmaXJzdF9uYW1lIjoiY25GdVpVdG5kRzR4U25sWVNGTjRiVW94VFhaUVVUMDkiLCJlbWFpbCI6ImFFWllPRXhKYVc1NWQyTlFTazk0YmtWWWJISTNRM3BKZW1OUVdIWXJWWE0wWldFNVIzZFNLelE0ZHowPSIsInBob25lIjoiZFhSNlFrSm9XVlpCYkN0clRUWTFOR3REU3pKTVVUMDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJhVVZGZGpBMk9XSnhlbXRZWm14amF6TTBVazQxUVQwOSIsImRldmljZV90eXBlIjoid2ViIiwiZGV2aWNlX3ZlcnNpb24iOiJDaHJvbWUrMTE5IiwiZGV2aWNlX21vZGVsIjoiY2hyb21lIiwicmVtb3RlX2FkZHIiOiIyNDA5OjQwYzI6MjA1NTo5MGQ0OjYzYmM6YTNjOTozMzBiOmIxOTkifX0.Kifitj1wCe_ohkdclvUt7WGuVBsQFiz7eeXoF1RduDJi4X7egejZlLZ0GCZmEKBwQpMJLvrdbAFIRniZoeAxL4FZ-pqIoYhH3PgZU6gWzKz5pdOCWfifnIzT5b3rzhDuG7sstfNiuNk9f-HMBievswEIPUC_ElazXdZPPt1gQqP7TmVg2Hjj6-JBcG7YPSqa6CUoXNDHpjWxK_KREnjWLM7vQ6J3vF1b7z_S3_CFti167C6UK5qb_turLnOUQzWzcwEaPGB3WXO0DAri6651WF33vzuzeclrcaQcMjum8n7VQ0Cl3fqypjaWD30btHQsu5j8j3pySWUlbyPVDOk-g'
                url = url.split("bcov_auth")[0]+bcov

            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "webvideos.classplusapp." in url:
               cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'

            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'

            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            try:
                cc = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.({res}).mkv\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀᴄᴛᴇᴅ Bʏ : {CR}**'
                cyt = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.({res}).mp4\n\n\n🔗𝗩𝗶𝗱𝗲𝗼 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'
                cpvod = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\n\nTitle : {name1}.({res}).mkv\n\n\n🔗𝗩𝗶𝗱𝗲𝗼 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'
                cimg = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.jpg\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'
                cczip = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.zip\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'
                cc1 = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.pdf\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'

                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=m.chat.id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)

                        if response.status_code == 200:
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)

                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif "media-cdn.classplusapp.com/drm/" in url:
                    try:
                        await bot.send_photo(chat_id=m.chat.id, photo=cpimg, caption=cpvod)
                        count +=1
                    except Exception as e:
                        await m.reply_text(str(e))
                        time.sleep(1)
                        continue

                elif any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)

                        if response.status_code == 200:
                            with open(f'{name}.jpg', 'wb') as file:
                                file.write(response.content)

                            await asyncio.sleep(2)
                            copy = await bot.send_photo(chat_id=m.chat.id, photo=f'{name}.jpg', caption=cimg)
                            count += 1
                            os.remove(f'{name}.jpg')
                        else:
                            await m.reply_text(f"Failed to download Image: {response.status_code} {response.reason}")

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(2)
                        return
                    except Exception as e:
                        await m.reply_text(f"An error occurred: {str(e)}")
                        await asyncio.sleep(4)

                elif ".zip" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.zip" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.zip', caption=cczip)
                        count += 1
                        os.remove(f'{name}.zip')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue

                else:
                    Show = (
                          f"**📥 Status:** `Downloading...`\n\n"
                          f"**📊 Progress:** `{count}/{len(links)}`\n"
                          f"──────────────────\n"
                          f"📝 **{name}**\n"
                          f"├ Format: `{MR}`\n"
                          f"├ Quality: `{raw_text2}`\n"
                          f"├ URL: `Secured 🔒`\n"
                          f"└ Thumb: `{input6.text}`\n"
                          f"──────────────────\n"
                          f"ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ"
                      )
                    prog = await m.reply_text(Show)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(1)

            except Exception as e:
                await m.reply_text(f'⚠️ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ꜰᴀɪʟᴇᴅ\n\n'
                                   f'ɴᴀᴍᴇ » `{name}`\n\n'
                                   f'ᴜʀʟ » <a href="{url}">__**Click Here to See Link**__</a>`')

                count += 1
                failed_count += 1
                continue

    except Exception as e:
        await m.reply_text(e)

    if pinned_msg:
        try:
            completed_text = (
                f"╭──────────────╮\n"
                f"┃  📊 **BATCH INFO** 📊  ┃\n"
                f"╰──────────────╯\n\n"
                f"**Batch Name:** `{b_name}`\n"
                f"**Quality:** `{raw_text2}p`\n"
                f"**Total Links:** `{len(links)}`\n\n"
                f"├ 🎞️ Videos: `{video_count}`\n"
                f"├ 📕 PDFs: `{pdf_count}`\n"
                f"├ 🖼️ Images: `{img_count}`\n"
                f"├ 📂 Zips: `{zip_count}`\n"
                f"├ 🔐 Encrypted: `{encrypted_count}`\n"
                f"├ ❌ Failed: `{failed_count}`\n\n"
                f"**Status:** ✅ Completed!\n\n"
                f"⚡ Bot Made By Pikachu"
            )
            await pinned_msg.edit_text(completed_text)
            logging.info("✅ Updated pinned message with completion status")
        except Exception as e:
            logging.error(f"⚠️ Failed to update pinned message: {e}")
    
    await m.reply_text("<b>✨ ᴘʀᴏᴄᴇꜱꜱ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>\n\n"
                       f"<b>📌 Bᴀᴛᴄʜ Nᴀᴍᴇ :</b> {b_name}\n\n"
                       f"╭────────────────\n"
                       f"├ 🔗 ᴛᴏᴛᴀʟ ᴜʀʟꜱ : <code>{len(links)}</code>\n"
                       f"├ ❌ ꜰᴀɪʟᴇᴅ : <code>{failed_count}</code>\n"
                       f"├ 🎞️ ᴠɪᴅᴇᴏꜱ : <code>{video_count}</code>\n"
                       f"├ 📕 ᴘᴅꜰꜱ : <code>{pdf_count}</code>\n"
                       f"├ 🖼️ ɪᴍᴀɢᴇꜱ : <code>{img_count}</code>\n"
                       f"├ 📂 ᴢɪᴘꜱ : <code>{zip_count}</code>\n"
                       f"├ 🔐 ᴇɴᴄʀʏᴘᴛᴇᴅ : <code>{encrypted_count}</code>\n"
                       f"╰────────────────\n\n"
                       f"<b>ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ :</b> {CR}")

bot.run()
