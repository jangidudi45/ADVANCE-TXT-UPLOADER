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

import re
from pathlib import Path

def sanitize_filename(name: str, max_len: int = 180) -> str:
    """Make a filesystem-safe filename (keeps Unicode but known-bad chars removed)."""
    if not name:
        return "video"
    name = name.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # Remove path separators and other illegal chars on common filesystems
    name = re.sub(r'[\\/:"*?<>|]+', " ", name)
    # Remove control characters
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    # Collapse spaces
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "video"

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




def is_m3u8_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower()
    return ".m3u8" in u or "manifest.m3u8" in u or u.endswith(".m3u8")


def build_ffmpeg_hls_cmd(url: str, out_file: str, user_agent: str | None = None) -> list[str]:
    """Return ffmpeg argv list for robust HLS download + remux to MP4."""
    ua = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-stats",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-user_agent", ua,
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-movflags", "+faststart",
        out_file,
    ]


async def download_video(url, cmd, name):
    """
    Downloads a video using yt-dlp.
    - First tries yt-dlp with sane concurrency (avoids 'I/O operation on closed file' seen with very high fragment concurrency).
    - If HLS (.m3u8) and yt-dlp fails, falls back to ffmpeg (shell=False, safe args).
    Returns the final downloaded filepath (or the best-effort name).
    """
    base_name = sanitize_filename(name)
    # keep original directory if provided in name
    out_dir = os.path.dirname(name) or "."
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Reduce concurrency: Akamai/KGS m3u8 often breaks with huge --concurrent-fragments
    fast_cmd = f'{cmd} -R 20 --fragment-retries 20 -N 8 --concurrent-fragments 8 --no-part'

    logging.info(f"[Download Attempt] Running command: {fast_cmd}")
    try:
        r = subprocess.run(
            fast_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if r.stdout:
            logging.info(r.stdout[-4000:])  # last chunk for debugging
    except Exception as e:
        logging.exception(f"yt-dlp subprocess failed: {e}")

    # yt-dlp may output different extensions based on source
    for ext in ["", ".webm", ".mp4", ".mkv", ".mp4.webm", ".ts"]:
        target_file = name + ext
        if os.path.isfile(target_file):
            return target_file

    # Fallback: direct HLS via ffmpeg
    if is_m3u8_url(url) or ".m3u8" in str(cmd).lower():
        safe_out = os.path.join(out_dir, sanitize_filename(os.path.basename(base_name)) + ".mp4")
        ff_argv = build_ffmpeg_hls_cmd(url, safe_out)
        logging.warning(f"[HLS Fallback] yt-dlp failed; trying ffmpeg argv: {ff_argv}")

        try:
            r2 = subprocess.run(
                ff_argv,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if r2.stdout:
                logging.info(r2.stdout[-4000:])
        except Exception as e:
            logging.exception(f"ffmpeg fallback failed: {e}")

        if os.path.isfile(safe_out) and os.path.getsize(safe_out) > 1024:
            return safe_out

    return name


async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name):
    thread_id = getattr(m, 'message_thread_id', None)
    
    reply = await bot.send_message(
        m.chat.id,
        f"<b>📤ᴜᴘʟᴏᴀᴅɪɴɢ📤 »</b> `{name}`\n\nʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ",
        message_thread_id=thread_id
    )
    time.sleep(1)
    start_time = time.time()
    
    await bot.send_document(
        m.chat.id,
        ka,
        caption=cc1,
        message_thread_id=thread_id
    )
    count += 1
    await reply.delete()
    time.sleep(1)
    os.remove(ka)
    time.sleep(3)


async def download_thumbnail(url, save_path):
    """Download thumbnail with multiple fallback methods"""
    
    for attempt in range(3):
        try:
            connector = aiohttp.TCPConnector(force_close=True, limit=1)
            timeout = aiohttp.ClientTimeout(total=60, connect=30, sock_read=30)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        async with aiofiles.open(save_path, mode='wb') as f:
                            await f.write(content)
                        logging.info(f"✅ Thumbnail downloaded via aiohttp (attempt {attempt + 1})")
                        return True
                    else:
                        logging.warning(f"HTTP {resp.status} on attempt {attempt + 1}")
        except Exception as e:
            logging.warning(f"aiohttp attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2)
    
    try:
        logging.info("Trying fallback method with requests library...")
        response = requests.get(url, timeout=30, stream=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logging.info("✅ Thumbnail downloaded via requests")
            return True
    except Exception as e:
        logging.error(f"Requests method also failed: {e}")
    
    try:
        logging.info("Trying last resort method with wget...")
        result = subprocess.run(
            ['wget', '-q', '-O', save_path, url],
            timeout=30,
            capture_output=True
        )
        if result.returncode == 0 and os.path.exists(save_path):
            logging.info("✅ Thumbnail downloaded via wget")
            return True
    except Exception as e:
        logging.error(f"Wget method also failed: {e}")
    
    return False


async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog):
    thread_id = getattr(m, 'message_thread_id', None)
    
    subprocess.run(f'ffmpeg -i "{filename}" -ss 00:00:12 -vframes 1 "{filename}.jpg"', shell=True)
    await prog.delete()
    
    reply = await bot.send_message(
        m.chat.id,
        f"<b>📤ᴜᴘʟᴏᴀᴅɪɴɢ📤 »</b> `{name}`\n\nʙᴏᴛ ᴍᴀᴅᴇ ʙʏ ᴘɪᴋᴀᴄʜᴜ",
        message_thread_id=thread_id
    )
    
    thumbnail = f"{filename}.jpg"
    downloaded_thumb = None
    
    try:
        if thumb != "no":
            if thumb.startswith("http://") or thumb.startswith("https://"):
                downloaded_thumb = "custom_thumb.jpg"
                logging.info(f"📸 Downloading thumbnail from: {thumb}")
                
                success = await download_thumbnail(thumb, downloaded_thumb)
                
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

    dur = int(duration(filename))
    start_time = time.time()

    try:
        await bot.send_video(
            m.chat.id,
            filename,
            caption=cc,
            supports_streaming=True,
            height=720,
            width=1280,
            thumb=thumbnail,
            duration=dur,
            progress=progress_bar,
            progress_args=(reply, start_time),
            message_thread_id=thread_id
        )
        logging.info(f"✅ Video uploaded successfully: {name}")
    except Exception as e:
        logging.error(f"❌ Video upload failed: {e}, falling back to document")
        try:
            await bot.send_document(
                m.chat.id,
                filename,
                caption=cc,
                progress=progress_bar,
                progress_args=(reply, start_time),
                message_thread_id=thread_id
            )
        except Exception as doc_error:
            logging.error(f"❌ Document upload also failed: {doc_error}")
            await bot.send_message(
                m.chat.id,
                f"❌ Upload failed for: {name}\nError: {str(doc_error)}",
                message_thread_id=thread_id
            )

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
