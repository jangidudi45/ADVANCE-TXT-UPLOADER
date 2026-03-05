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
from urllib.parse import urlparse, parse_qs
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
from db import Database

cookies_file_path = os.getenv("COOKIES_FILE_PATH", "youtube_cookies.txt")

cpimg = "https://files.catbox.moe/v9z1n7.jpg"

async def show_random_emojis(message):
    emojis = ['🎊', '🔮', '😎', '⚡️', '🚀', '✨', '💥', '🎉', '🥂', '🍾', '🦠', '🤖', '❤️‍🔥', '🕊️', '💃', '🥳','🐅','🦁']
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
def is_authorized(message: Message) -> bool:
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    thread_id = message.reply_to_message_id if hasattr(message, 'reply_to_message_id') else None
    
    # Check if the user is the owner
    if user_id == OWNER_ID:
        return True
    
    # Check if user is in sudo list
    if user_id and db.is_sudo_user(user_id):
        return True
    
    # Check if the chat/topic is authorized
    if db.is_authorized_chat(chat_id, thread_id):
        return True
    
    # Check for auth channel
    if chat_id == AUTH_CHANNEL:
        return True
    
    return False

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN)

# Enhanced sudo command to handle topics
@bot.on_message(filters.command("sudo"))
async def sudo_command(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await message.reply_text("**🚫 You are not authorized to use this command.**")
        return

    try:
        args = message.text.split()
        if len(args) < 3:
            await message.reply_text("**Usage:**\n"
                                   "`/sudo add <user_id>` - Add user\n"
                                   "`/sudo add <chat_id>` - Add chat (group/channel)\n"
                                   "`/sudo add <chat_id/thread_id>` - Add specific topic\n"
                                   "`/sudo remove <user_id>` - Remove user\n"
                                   "`/sudo remove <chat_id>` - Remove chat\n"
                                   "`/sudo remove <chat_id/thread_id>` - Remove topic")
            return

        action = args[1].lower()
        target = args[2]
        
        if action == "add":
            # Check if it's a chat/topic format
            if '/' in target:
                try:
                    chat_id, thread_id = db.parse_topic_string(target)
                    if db.add_topic_auth(chat_id, thread_id):
                        await message.reply_text(f"**✅ Topic `{target}` added to authorized list.**")
                    else:
                        await message.reply_text(f"**⚠️ Topic `{target}` is already authorized.**")
                except ValueError as e:
                    await message.reply_text(f"**Error:** {e}")
            else:
                # Try to parse as integer (user or chat ID)
                try:
                    target_id = int(target)
                    # Negative IDs are chats, positive are users
                    if target_id < 0:
                        if db.add_topic_auth(target_id, None):
                            await message.reply_text(f"**✅ Chat `{target_id}` added to authorized list.**")
                        else:
                            await message.reply_text(f"**⚠️ Chat `{target_id}` is already authorized.**")
                    else:
                        if db.add_sudo_user(target_id):
                            await message.reply_text(f"**✅ User `{target_id}` added to sudo list.**")
                        else:
                            await message.reply_text(f"**⚠️ User `{target_id}` is already in the sudo list.**")
                except ValueError:
                    await message.reply_text("**Error:** Invalid ID format")
                    
        elif action == "remove":
            if '/' in target:
                try:
                    chat_id, thread_id = db.parse_topic_string(target)
                    if db.remove_topic_auth(chat_id, thread_id):
                        await message.reply_text(f"**✅ Topic `{target}` removed from authorized list.**")
                    else:
                        await message.reply_text(f"**⚠️ Topic `{target}` not found in authorized list.**")
                except ValueError as e:
                    await message.reply_text(f"**Error:** {e}")
            else:
                try:
                    target_id = int(target)
                    if target_id < 0:
                        if db.remove_topic_auth(target_id, None):
                            await message.reply_text(f"**✅ Chat `{target_id}` removed from authorized list.**")
                        else:
                            await message.reply_text(f"**⚠️ Chat `{target_id}` not found in authorized list.**")
                    else:
                        if target_id == OWNER_ID:
                            await message.reply_text("**🚫 The owner cannot be removed from the sudo list.**")
                        elif db.remove_sudo_user(target_id):
                            await message.reply_text(f"**✅ User `{target_id}` removed from sudo list.**")
                        else:
                            await message.reply_text(f"**⚠️ User `{target_id}` is not in the sudo list.**")
                except ValueError:
                    await message.reply_text("**Error:** Invalid ID format")
        else:
            await message.reply_text("**Invalid action. Use 'add' or 'remove'.**")
            
    except Exception as e:
        await message.reply_text(f"**Error:** {str(e)}")

# Inline keyboard for start command
keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🇮🇳ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ🇮🇳", url="https://t.me/ItsPikachubot")
        ],
        [
            InlineKeyboardButton("🔔ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ🔔", url="https://t.me/Medicoarmy")
        ],
        [
            InlineKeyboardButton("🦋ғᴏʟʟᴏᴡ ᴜs🦋", url="https://t.me/Medicoarmy")
        ],
    ]
)

# Image URLs for the random image feature
image_urls = [
    "https://files.catbox.moe/v9z1n7.jpg",
]
random_image_url = random.choice(image_urls)

caption = (
    "**ʜᴇʟʟᴏ👋**\n\n"
    "➠ **ɪ ᴀᴍ ᴛxᴛ ᴛᴏ ᴠɪᴅᴇᴏ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ.**\n"
    "➠ **ғᴏʀ ᴜsᴇ ᴍᴇ sᴇɴᴅ /txt.\n"
    "➠ **ғᴏʀ ɢᴜɪᴅᴇ sᴇɴᴅ /help."
)

# Start command handler
@bot.on_message(filters.command(["start"]))
async def start_command(bot: Client, message: Message):
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=random_image_url,
        caption=caption,
        reply_markup=keyboard,
        reply_to_message_id=message.reply_to_message_id if hasattr(message, 'reply_to_message_id') else None
    )

# Stop command handler
@bot.on_message(filters.command("stop"))
async def restart_handler(_, m: Message):
    if not is_authorized(m):
        await m.reply_text("**🚫 You are not authorized to use this command.**")
        return
    await m.reply_text("<b>ꜱᴛᴏᴘᴘᴇᴅ</b>🚦", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command("restart"))
async def restart_handler(_, m: Message):
    if not is_authorized(m):
        await m.reply_text("**🚫 You are not authorized to use this command.**")
        return
    await m.reply_text("🔮Restarted🔮", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

COOKIES_FILE_PATH = "youtube_cookies.txt"

@bot.on_message(filters.command("cookies") & filters.private)
async def cookies_handler(client: Client, m: Message):
    if not is_authorized(m):
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
            "✅ 𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝗨𝗽𝗱𝗮𝘁𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆.\n\𝗻📂 𝗦𝗮𝘃𝗲𝗱 𝗜𝗻 youtube_cookies.txt."
        )

    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

import tempfile

@bot.on_message(filters.command('e2t'))
async def edit_txt(client, message: Message):
    if not is_authorized(message):
        await message.reply_text("**🚫 You are not authorized to use this command.**")
        return
        
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
            "🔄 **Send your .txt file name, or type 'd' for the default file name.**"
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
                caption="📥**ᴇᴅɪᴛᴇᴅ ʙʏ ᴘɪᴋᴀᴄʜᴜ**",
                reply_to_message_id=message.reply_to_message_id if hasattr(message, 'reply_to_message_id') else None
            )
        except Exception as e:
            await message.reply_text(f"🚨 **Error**: Unable to send the file.\n\nDetails: {e}")
        finally:
            pass

# YouTube to TXT handler
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
    if not is_authorized(message):
        await message.reply_text("**🚫 You are not authorized to use this command.**")
        return

    user_id = message.from_user.id
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
            caption=f"`{title}`\n\n<b>📥 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : ᴘɪᴋᴀᴄʜᴜ</b>",
            reply_to_message_id=message.reply_to_message_id if hasattr(message, 'reply_to_message_id') else None
        )
        os.remove(file_name)
    else:
        await message.reply_text("⚠️ **Unable to retrieve videos. Please check the URL.**")

# List users command - Enhanced to show topics
@bot.on_message(filters.command("userlist"))
async def list_users(client: Client, msg: Message):
    if msg.from_user.id != OWNER_ID:
        await msg.reply_text("**🚫 You are not authorized to use this command.**")
        return
        
    sudo_users = db.get_sudo_users()
    authorized_chats = db.get_authorized_chats()
    
    response = "**SUDO USERS:**\n"
    if sudo_users:
        response += "\n".join([f"• User ID: `{user_id}`" for user_id in sudo_users])
    else:
        response += "No sudo users.\n"
    
    response += "\n\n**AUTHORIZED CHATS/TOPICS:**\n"
    if authorized_chats:
        for chat in authorized_chats:
            if chat.get('thread_id'):
                response += f"• Chat: `{chat['chat_id']}` / Topic: `{chat['thread_id']}`\n"
            else:
                response += f"• Chat: `{chat['chat_id']}` (General)\n"
    else:
        response += "No authorized chats/topics."
    
    await msg.reply_text(response)

# Help command
@bot.on_message(filters.command("help"))
async def help_command(client: Client, msg: Message):
    help_text = (
        "`/start` - Start the bot⚡\n\n"
        "`/txt` - Download and upload files (sudo)🎬\n\n"
        "`/restart` - Restart the bot🔮\n\n"
        "`/stop` - Stop ongoing process🛑\n\n"
        "`/cookies` - Upload cookies file🍪\n\n"
        "`/e2t` - Edit txt file📝\n\n"
        "`/yt2txt` - Create txt of yt playlist (owner)🗃️\n\n"
        "`/sudo add` - Add user/chat/topic (owner)🎊\n\n"
        "`/sudo remove` - Remove user/chat/topic (owner)❌\n\n"
        "`/userlist` - List of sudo users/chats/topics📜\n\n"
        "\n**Topic Support:**\n"
        "• Add topic: `/sudo add -100123456789/34`\n"
        "• Add chat: `/sudo add -100123456789`\n"
        "• Add user: `/sudo add 123456789`"
    )
    await msg.reply_text(help_text)

# Callback handler for Topic Index "Done ✅" button
@bot.on_callback_query(filters.regex("^index_done$"))
async def index_done_callback(client: Client, callback_query):
    try:
        await callback_query.answer("✅ Done!", show_alert=False)
        # Remove inline keyboard from the index message
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logging.error(f"⚠️ index_done callback error: {e}")

# Modified send_doc function for topic support
async def send_doc_topic(bot: Client, m: Message, cc, ka, cc1, prog, count, name):
    reply = await m.reply_text(
        f"<b>📤ᴜᴘʟᴏᴀᴅɪɴɢ📤 »</b> `{name}`\n\nʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ",
        reply_to_message_id=m.reply_to_message_id if hasattr(m, 'reply_to_message_id') else None
    )
    await asyncio.sleep(1)
    start_time = time.time()
    
    await bot.send_document(
        chat_id=m.chat.id,
        document=ka,
        caption=cc1,
        reply_to_message_id=m.reply_to_message_id if hasattr(m, 'reply_to_message_id') else None
    )
    
    count += 1
    await reply.delete()
    await asyncio.sleep(1)
    os.remove(ka)
    await asyncio.sleep(3)

# Modified upload command handler with topic support
@bot.on_message(filters.command(["txt"]))
async def upload(bot: Client, m: Message):
    if not is_authorized(m):
        await m.reply_text(
            "**🚫 You are not authorized to use this bot.**",
            reply_to_message_id=m.reply_to_message_id if hasattr(m, 'reply_to_message_id') else None
        )
        return

    # Get thread_id for all messages in this session
    thread_id = m.reply_to_message_id if hasattr(m, 'reply_to_message_id') else None
    
    editable = await m.reply_text(
        f"📝<b>ꜱᴇɴᴅ ᴛxᴛ ꜰɪʟᴇ</b>",
        reply_to_message_id=thread_id
    )
    input: Message = await bot.listen(m.chat.id)
    x = await input.download()
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    pdf_count = 0
    img_count = 0
    zip_count = 0
    video_count = 0

    try:
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")

        links = []
        for i in content:
            if "://" in i:
                url = i.split("://", 1)[1]
                title_part = i.split("://", 1)[0]

                # Extract [Topic] from title if present
                topic_match = re.match(r'^\[([^\]]+)\]\s*[-–]?\s*(.*)', title_part)
                if topic_match:
                    topic_tag = topic_match.group(1).strip()
                    clean_title = topic_match.group(2).strip()
                else:
                    topic_tag = None
                    clean_title = title_part.strip()

                # links entry: [clean_title, url_without_scheme, topic_tag]
                links.append([clean_title, url, topic_tag])

                if ".pdf" in url:
                    pdf_count += 1
                elif url.endswith((".png", ".jpeg", ".jpg")):
                    img_count += 1
                elif ".zip" in url:
                    zip_count += 1
                else:
                    video_count += 1
        os.remove(x)
    except:
        await m.reply_text(
            "⚠️ɪɴᴠᴀʟɪᴅ ꜰɪʟᴇ ɪɴᴘᴜᴛ",
            reply_to_message_id=thread_id
        )
        os.remove(x)
        return

    await editable.edit(
        f"`🔗 <b>ᴛᴏᴛᴀʟ ʟɪɴᴋꜱ ꜰᴏᴜɴᴅ ᴀʀᴇ</b> {len(links)}\n\n"
        f"🖼️ ɪᴍᴀɢᴇꜱ : {img_count}\n"
        f"📄 ᴘᴅꜰꜱ : {pdf_count}\n"
        f"📂 ᴢɪᴘꜱ : {zip_count}\n"
        f"🎞️ ᴠɪᴅᴇᴏꜱ : {video_count}\n\n"
        f"ꜱᴇɴᴅ ꜰʀᴏᴍ ᴡʜᴇʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ.`"
    )
    
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

    await editable.edit(
        "<b>📸 ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ 📸</b>\n"
        "➤ `144`\n➤ `240`\n➤ `360`\n➤ `480`\n➤ `720`\n➤ `1080`"
    )
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    await input2.delete(True)
    
    res_map = {
        "144": "256x144",
        "240": "426x240",
        "360": "640x360",
        "480": "854x480",
        "720": "1280x720",
        "1080": "1920x1080"
    }
    res = res_map.get(raw_text2, "UN")

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
    MR = "token" if raw_text4 == '3' else raw_text4

    await editable.edit(
        "<b>ɴᴏᴡ ꜱᴇɴᴅ ᴛʜᴇ ᴛʜᴜᴍʙ ᴜʀʟ ᴇɢ »</b> https://files.catbox.moe/zgfhrn.jpg\n\n"
        "<b>ᴏʀ ɪꜰ ᴅᴏɴ'ᴛ ᴡᴀɴᴛ ᴛʜᴜᴍʙɴᴀɪʟ ꜱᴇɴᴅ = ɴᴏ</b>"
    )
    input6 = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = raw_text6.strip()
    print(f"📸 Thumbnail input received: {thumb}")

    if thumb.startswith("http://") or thumb.startswith("https://"):
        print(f"✅ Using custom thumbnail URL: {thumb}")
    elif thumb.lower() == "no":
        thumb = "no"
        print("⚡ Using auto-generated thumbnail")
    else:
        thumb = "no"
        print("⚠️ Invalid input, using auto-generated thumbnail")

    # CREATE AND PIN SUMMARY MESSAGE
    summary_text = (
        f"╭━━━━━━━━━━━━━━━━━╮\n"
        f"┃  📊 **BATCH INFO** 📊  ┃\n"
        f"╰━━━━━━━━━━━━━━━━━╯\n\n"
        f"**Batch Name:** `{b_name}`\n"
        f"**Quality:** `{raw_text2}p`\n"
        f"**Total Links:** `{len(links)}`\n\n"
        f"├ 🎞️ Videos: `{video_count}`\n"
        f"├ 📕 PDFs: `{pdf_count}`\n"
        f"├ 🖼️ Images: `{img_count}`\n"
        f"├ 📂 Zips: `{zip_count}`\n\n"
        f"**Status:** 🔄 Processing...\n\n"
        f"⚡ Bot Made By Pikachu"
    )
    
    pinned_msg = None
    try:
        pinned_msg = await m.reply_text(
            summary_text,
            disable_web_page_preview=True,
            reply_to_message_id=thread_id
        )
        await pinned_msg.pin(disable_notification=False)
        logging.info(f"✅ Pinned summary message in chat {m.chat.id}, topic {thread_id}")
    except Exception as e:
        logging.error(f"⚠️ Failed to pin message: {e}")

    failed_count = 0
    # topic_index stores: { topic_name: first_message_id_of_that_topic }
    topic_index = {}   # e.g. {"Physics": 12345, "Chemistry": 12399}
    last_seen_topic = None

    if len(links) == 1:
        count = 1
    else:
        count = int(raw_text)

    try:
        for i in range(count - 1, len(links)):
            V = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","") # .replace("mpd","m3u8")
            url = "https://" + V
            current_topic = links[i][2] if len(links[i]) > 2 else None

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
            #elif '/master.mpd' in url:
             #id =  url.split("/")[-2]
             #url = f"https://player.muftukmall.site/?id={id}"
            elif "/master.mpd" in url or "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
             id =  url.split("/")[-2]
             url = f"https://anonymouspwplayer-25261acd1521.herokuapp.com/pw?url={url}&token={raw_text4}"
             #url = f"https://madxabhi-pw.onrender.com/{id}/master.m3u8?token={raw_text4}"
            #elif '/master.mpd' in url:
             #id =  url.split("/")[-2]
             #url = f"https://dl.alphacbse.site/download/{id}/master.m3u8"


            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]}'

            # ── Topic tag: track first message per topic ──────────────────────
            if current_topic and current_topic != last_seen_topic:
                last_seen_topic = current_topic
                # We'll update topic_index with message_id after sending below

            #if 'cpvod.testbook' in url:
                #CPVOD = url.split("/")[-2]
                #url = requests.get(f'https://extractbot.onrender.com/classplus?link=https://cpvod.testbook.com/{CPVOD}/playlist.m3u8', headers={'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9r'}).json()['url']

            #if 'cpvod.testbook' in url:
               #url = requests.get(f'https://mon-key-3612a8154345.herokuapp.com/get_keys?url=https://cpvod.testbook.com/{CPVOD}/playlist.m3u8', headers={'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9r'}).json()['url']


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

            # ── Vimeo CDN JSON playlist URLs ──────────────────────────────────
            if helper.is_vimeo_json_url(url):
                name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
                name = f'{str(count).zfill(3)}) {name1[:60]}'
                topic_line_v = f"\n\nᴛᴏᴘɪᴄ : {current_topic}" if current_topic else ""
                cc = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.mp4{topic_line_v}\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀᴄᴛᴇᴅ Bʏ : {CR}**'
                Show = (
                    f"**📥 Status:** `Downloading (Vimeo)...`\n\n"
                    f"**📊 Progress:** `{count}/{len(links)}`\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📁 **{name}**\n"
                    f"├ Format: `Vimeo JSON`\n"
                    f"├ Quality: `Best Available`\n"
                    f"└ Thumb: `{raw_text6}`\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ"
                )
                prog = await m.reply_text(Show, reply_to_message_id=thread_id)
                try:
                    filename = await helper.download_vimeo_json(url, name)
                    await prog.delete()
                    sent_msg = await send_vid_topic(bot, m, cc, filename, thumb, name, prog, thread_id)
                    if current_topic and current_topic not in topic_index and sent_msg:
                        topic_index[current_topic] = sent_msg.id
                    count += 1
                    video_count += 1
                except Exception as vimeo_err:
                    await prog.delete()
                    await m.reply_text(
                        f'⚠️ Vimeo ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ғᴀɪʟᴇᴅ\n\nɴᴀᴍᴇ » `{name}`\nᴇʀʀᴏʀ » `{str(vimeo_err)}`',
                        reply_to_message_id=thread_id
                    )
                    count += 1
                    failed_count += 1
                continue
            # ─────────────────────────────────────────────────────────────────

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
                topic_line = f"\n\nᴛᴏᴘɪᴄ : {current_topic}" if current_topic else ""
                cc = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.({res}).mkv{topic_line}\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀᴄᴛᴇᴅ Bʏ : {CR}**'
                cpvod = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\n\nTitle : {name1}.({res}).mkv{topic_line}\n\n\n🔗𝗩𝗶𝗱𝗲ᴏ 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'
                cimg = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.jpg{topic_line}\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'
                cczip = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.zip{topic_line}\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'
                cc1 = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.pdf{topic_line}\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ : {CR}**'

                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        sent_msg = await bot.send_document(
                            chat_id=m.chat.id,
                            document=ka,
                            caption=cc1,
                            reply_to_message_id=thread_id
                        )
                        if current_topic and current_topic not in topic_index:
                            topic_index[current_topic] = sent_msg.id
                        count += 1
                        os.remove(ka)
                        await asyncio.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(e.value + 2)
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
                            sent_msg = await bot.send_document(
                                chat_id=m.chat.id,
                                document=f'{name}.pdf',
                                caption=cc1,
                                reply_to_message_id=thread_id
                            )
                            if current_topic and current_topic not in topic_index:
                                topic_index[current_topic] = sent_msg.id
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")

                    except FloodWait as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(e.value + 2)
                        continue

                elif "media-cdn.classplusapp.com/drm/" in url:
                    try:
                        sent_msg = await bot.send_photo(
                            chat_id=m.chat.id,
                            photo=cpimg,
                            caption=cpvod,
                            reply_to_message_id=thread_id
                        )
                        if current_topic and current_topic not in topic_index:
                            topic_index[current_topic] = sent_msg.id
                        count += 1
                    except Exception as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(1)
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
                            sent_msg = await bot.send_photo(
                                chat_id=m.chat.id,
                                photo=f'{name}.jpg',
                                caption=cimg,
                                reply_to_message_id=thread_id
                            )
                            if current_topic and current_topic not in topic_index:
                                topic_index[current_topic] = sent_msg.id
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
                        sent_msg = await bot.send_document(
                            chat_id=m.chat.id,
                            document=f'{name}.zip',
                            caption=cczip,
                            reply_to_message_id=thread_id
                        )
                        if current_topic and current_topic not in topic_index:
                            topic_index[current_topic] = sent_msg.id
                        count += 1
                        os.remove(f'{name}.zip')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(e.value + 2)
                        count += 1
                        continue

                elif ".pdf" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        sent_msg = await bot.send_document(
                            chat_id=m.chat.id,
                            document=f'{name}.pdf',
                            caption=cc1,
                            reply_to_message_id=thread_id
                        )
                        if current_topic and current_topic not in topic_index:
                            topic_index[current_topic] = sent_msg.id
                        count += 1
                        os.remove(f'{name}.pdf')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(e.value + 2)
                        continue
                else:
                    Show = (
                        f"**📥 Status:** `Downloading...`\n\n"
                        f"**📊 Progress:** `{count}/{len(links)}`\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📁 **{name}**\n"
                        f"├ Format: `{MR}`\n"
                        f"├ Quality: `{raw_text2}`\n"
                        f"├ URL: `Secured 🔐`\n"
                        f"└ Thumb: `{input6.text}`\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ"
                    )
                    prog = await m.reply_text(
                        Show,
                        reply_to_message_id=thread_id
                    )
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete()
                    
                    # Modified send_vid call for topic support
                    sent_msg = await send_vid_topic(bot, m, cc, filename, thumb, name, prog, thread_id)
                    if current_topic and current_topic not in topic_index and sent_msg:
                        topic_index[current_topic] = sent_msg.id
                    count += 1
                    await asyncio.sleep(1)

            except Exception as e:
                await m.reply_text(
                    f'⚠️ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ғᴀɪʟᴇᴅ\n\n'
                    f'ɴᴀᴍᴇ » `{name}`\n\n'
                    f'ᴜʀʟ » <a href="{url}">__**Click Here to See Link**__</a>`',
                    reply_to_message_id=thread_id
                )
                count += 1
                failed_count += 1
                continue

    except Exception as e:
        await m.reply_text(str(e))

    # UPDATE PINNED MESSAGE AFTER COMPLETION
    if pinned_msg:
        try:
            completed_text = (
                f"╭━━━━━━━━━━━━━━━━━╮\n"
                f"┃  📊 **BATCH INFO** 📊  ┃\n"
                f"╰━━━━━━━━━━━━━━━━━╯\n\n"
                f"**Batch Name:** `{b_name}`\n"
                f"**Quality:** `{raw_text2}p`\n"
                f"**Total Links:** `{len(links)}`\n\n"
                f"├ 🎞️ Videos: `{video_count}`\n"
                f"├ 📕 PDFs: `{pdf_count}`\n"
                f"├ 🖼️ Images: `{img_count}`\n"
                f"├ 📂 Zips: `{zip_count}`\n"
                f"├ ❌ Failed: `{failed_count}`\n\n"
                f"**Status:** ✅ Completed!\n\n"
                f"⚡ Bot Made By Pikachu"
            )
            await pinned_msg.edit_text(completed_text)
            logging.info("✅ Updated pinned message with completion status")
        except Exception as e:
            logging.error(f"⚠️ Failed to update pinned message: {e}")
    


    # ── Topic Index as plain hyperlink text ──────────────────────────────────
    if topic_index:
        try:
            raw_chat_id = str(m.chat.id).replace("-100", "")

            def to_smallcaps(text):
                normal = "abcdefghijklmnopqrstuvwxyz"
                small  = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
                result = ""
                for ch in text.lower():
                    if ch in normal:
                        result += small[normal.index(ch)]
                    else:
                        result += ch
                return result

            index_lines = []
            for topic_name, msg_id in topic_index.items():
                topic_url = f"https://t.me/c/{raw_chat_id}/{msg_id}"
                display = to_smallcaps(topic_name)
                index_lines.append(f'• <a href="{topic_url}">{display}</a>')

            index_text = "\n \n".join(index_lines)

            await m.reply_text(
                index_text,
                disable_web_page_preview=True,
                reply_to_message_id=thread_id
            )
            logging.info(f"✅ Sent topic index with {len(topic_index)} topics")

            await m.reply_text(
                "✅ <b>Done</b>",
                reply_to_message_id=thread_id
            )
        except Exception as e:
            logging.error(f"⚠️ Failed to send topic index: {e}")

# Modified send_vid function for topic support
async def send_vid_topic(bot: Client, m: Message, cc, filename, thumb, name, prog, thread_id=None):
    # Generate auto thumbnail from video
    subprocess.run(f'ffmpeg -i "{filename}" -ss 00:00:12 -vframes 1 "{filename}.jpg"', shell=True)
    await prog.delete()
    
    reply = await m.reply_text(
        f"<b>📤ᴜᴘʟᴏᴀᴅɪɴɢ📤 »</b> `{name}`\n\nʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ",
        reply_to_message_id=thread_id
    )
    
    # Enhanced thumbnail handling
    thumbnail = f"{filename}.jpg"
    downloaded_thumb = None
    
    try:
        if thumb != "no":
            if thumb.startswith("http://") or thumb.startswith("https://"):
                downloaded_thumb = "custom_thumb.jpg"
                logging.info(f"📸 Downloading thumbnail from: {thumb}")
                
                success = await helper.download_thumbnail(thumb, downloaded_thumb)
                
                if success and os.path.exists(downloaded_thumb):
                    thumbnail = downloaded_thumb
                    logging.info("✅ Custom thumbnail set successfully")
                else:
                    logging.warning("⚠️ All download methods failed, using auto-generated thumbnail")
                    
            elif os.path.exists(thumb):
                thumbnail = thumb
                logging.info(f"✅ Using local thumbnail: {thumb}")
            else:
                logging.warning(f"⚠️ Thumbnail path does not exist: {thumb}")
    except Exception as e:
        logging.error(f"❌ Thumbnail error: {e}")
        thumbnail = f"{filename}.jpg"

    dur = int(helper.duration(filename))
    start_time = time.time()

    sent_result = None
    for attempt in range(3):
        try:
            sent_result = await bot.send_video(
                chat_id=m.chat.id,
                video=filename,
                caption=cc,
                supports_streaming=True,
                height=720,
                width=1280,
                thumb=thumbnail,
                duration=dur,
                progress=progress_bar,
                progress_args=(reply, start_time),
                reply_to_message_id=thread_id
            )
            logging.info(f"✅ Video uploaded successfully: {name}")
            break
        except FloodWait as fw:
            logging.warning(f"⚠️ FloodWait {fw.value}s on send_video, waiting...")
            await asyncio.sleep(fw.value + 2)
        except Exception as e:
            logging.error(f"❌ Video upload failed: {e}, falling back to document")
            try:
                for attempt2 in range(3):
                    try:
                        sent_result = await bot.send_document(
                            chat_id=m.chat.id,
                            document=filename,
                            caption=cc,
                            progress=progress_bar,
                            progress_args=(reply, start_time),
                            reply_to_message_id=thread_id
                        )
                        break
                    except FloodWait as fw2:
                        logging.warning(f"⚠️ FloodWait {fw2.value}s on send_document, waiting...")
                        await asyncio.sleep(fw2.value + 2)
            except Exception as doc_error:
                logging.error(f"❌ Document upload also failed: {doc_error}")
                await m.reply_text(
                    f"❌ Upload failed for: {name}\nError: {str(doc_error)}",
                    reply_to_message_id=thread_id
                )
            break

    # Small delay after each upload to avoid flood
    await asyncio.sleep(3)

    # Cleanup all files
    try:
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")
        if downloaded_thumb and os.path.exists(downloaded_thumb):
            os.remove(downloaded_thumb)
            logging.info("🧹 Cleanup completed")
    except Exception as e:
        logging.error(f"⚠️ Cleanup error: {e}")
    
    await reply.delete()
    return sent_result

bot.run()
