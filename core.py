# Don't Remove Credit Tg - @Tushar0125

import os
import time
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures

from utils import progress_bar

from pyrogram import Client, filters
from pyrogram.types import Message

from pytube import Playlist  # Youtube Playlist Extractor
from yt_dlp import YoutubeDL
import yt_dlp as youtube_dl


def duration(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)


def exec(cmd):
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.stdout.decode()
    print(output)
    return output


def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        fut = executor.map(exec, cmds)


async def aio(url, name):
    k = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(k, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return k


async def download(url, name):
    ka = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(ka, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return ka


def parse_vid_info(info):
    info = info.strip().split("\n")
    new_info = []
    temp = []
    for i in info:
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i = i.strip().split("|")[0].split(" ", 2)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info


def vid_info(info):
    info = info.strip().split("\n")
    new_info = dict()
    temp = []
    for i in info:
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i = i.strip().split("|")[0].split(" ", 3)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info[f'{i[2]}'] = f'{i[0]}'
            except:
                pass
    return new_info


async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode == 1:
        return False
    if stdout:
        return f'[stdout]\n{stdout.decode()}'
    if stderr:
        return f'[stderr]\n{stderr.decode()}'


def old_download(url, file_name, chunk_size=1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"


def get_playlist_videos(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        playlist_title = playlist.title
        videos = {}
        for video in playlist.videos:
            try:
                video_title = video.title
                video_url = video.watch_url
                videos[video_title] = video_url
            except Exception as e:
                logging.error(f"Could not retrieve video details: {e}")
        return playlist_title, videos
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None, None


def get_all_videos(channel_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True
    }

    all_videos = []
    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(channel_url, download=False)

        if 'entries' in result:
            channel_name = result['title']
            all_videos.extend(result['entries'])

            video_links = {index + 1: (video['title'], video['url']) for index, video in enumerate(all_videos)}
            return video_links, channel_name
        else:
            return None, None


def save_to_file(video_links, channel_name):
    import re
    sanitized_channel_name = re.sub(r'[^\w\s-]', '', channel_name).strip().replace(' ', '_')
    filename = f"{sanitized_channel_name}.txt"
    with open(filename, 'w', encoding='utf-8') as file:
        for number, (title, url) in video_links.items():
            if url.startswith("https://"):
                formatted_url = url
            elif "shorts" in url:
                formatted_url = f"https://www.youtube.com{url}"
            else:
                formatted_url = f"https://www.youtube.com/watch?v={url}"
            file.write(f"{number}. {title}: {formatted_url}\n")
    return filename


async def download_video(url, cmd, name):
    global failed_counter

    # ✅ Force fastest possible yt-dlp command with multithreading
    fast_cmd = f'{cmd} -R 25 --fragment-retries 25 -N 32 --concurrent-fragments 48'

    logging.info(f"[Download Attempt] Running command: {fast_cmd}")
    result = subprocess.run(fast_cmd, shell=True)

    # Check for common file outputs
    for ext in ["", ".webm", ".mp4", ".mkv", ".mp4.webm"]:
        target_file = name + ext
        if os.path.isfile(target_file):
            return target_file

    return name


async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name):
    reply = await m.reply_text(f"<b>📤ᴜᴘʟᴏᴀᴅɪɴɢ📤 »</b> `{name}`\n\nʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ")
    time.sleep(1)
    start_time = time.time()
    await m.reply_document(ka, caption=cc1)
    count += 1
    await reply.delete(True)
    time.sleep(1)
    os.remove(ka)
    time.sleep(3)


async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog):
    # Generate auto thumbnail from video
    subprocess.run(f'ffmpeg -i "{filename}" -ss 00:00:12 -vframes 1 "{filename}.jpg"', shell=True)
    await prog.delete(True)
    reply = await m.reply_text(f"<b>📤ᴜᴘʟᴏᴀᴅɪɴɢ📤 »</b> `{name}`\n\nʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ")
    
    # ✅ Enhanced thumbnail handling
    thumbnail = f"{filename}.jpg"  # Default to auto-generated
    downloaded_thumb = None
    
    try:
        if thumb != "no":
            if thumb.startswith("http://") or thumb.startswith("https://"):
                # Download thumbnail from URL
                downloaded_thumb = "custom_thumb.jpg"
                logging.info(f"Downloading thumbnail from: {thumb}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumb, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            async with aiofiles.open(downloaded_thumb, mode='wb') as f:
                                await f.write(await resp.read())
                            thumbnail = downloaded_thumb
                            logging.info("Thumbnail downloaded successfully")
                        else:
                            logging.warning(f"Failed to download thumbnail: HTTP {resp.status}")
            elif os.path.exists(thumb):
                # Use local file if it exists
                thumbnail = thumb
            else:
                logging.warning(f"Thumbnail path does not exist: {thumb}")
    except Exception as e:
        logging.error(f"Thumbnail error: {e}")
        thumbnail = f"{filename}.jpg"  # Fallback to auto-generated

    dur = int(duration(filename))
    start_time = time.time()

    try:
        await m.reply_video(
            filename, 
            caption=cc, 
            supports_streaming=True, 
            height=720, 
            width=1280,
            thumb=thumbnail, 
            duration=dur,
            progress=progress_bar, 
            progress_args=(reply, start_time)
        )
        logging.info(f"Video uploaded successfully: {name}")
    except Exception as e:
        logging.error(f"Video upload failed: {e}, falling back to document")
        try:
            await m.reply_document(
                filename, 
                caption=cc, 
                progress=progress_bar, 
                progress_args=(reply, start_time)
            )
        except Exception as doc_error:
            logging.error(f"Document upload also failed: {doc_error}")
            await m.reply_text(f"❌ Upload failed for: {name}\nError: {str(doc_error)}")

    # ✅ Cleanup all files
    try:
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")
        if downloaded_thumb and os.path.exists(downloaded_thumb):
            os.remove(downloaded_thumb)
            logging.info("Custom thumbnail cleaned up")
    except Exception as e:
        logging.error(f"Cleanup error: {e}")
    
    await reply.delete(True)
