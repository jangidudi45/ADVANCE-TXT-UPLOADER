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
import re

from utils import progress_bar

from pyrogram import Client, filters
from pyrogram.types import Message

from pytube import Playlist  # Youtube Playlist Extractor
from yt_dlp import YoutubeDL
import yt_dlp as youtube_dl


def sanitize_filename(filename):
    """Sanitize filename to remove problematic characters"""
    # Remove or replace characters that cause issues
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Remove leading/trailing spaces
    filename = filename.strip()
    # Limit length to avoid path issues
    if len(filename) > 200:
        filename = filename[:200]
    return filename


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
    """Enhanced download function with better m3u8 support"""
    global failed_counter

    # Sanitize the output filename
    safe_name = sanitize_filename(name)
    
    # Check if it's an m3u8 URL
    is_m3u8 = '.m3u8' in url.lower()
    
    if is_m3u8:
        logging.info(f"🎬 Detected m3u8 stream: {url}")
        
        # Enhanced yt-dlp command for m3u8 with better options
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{safe_name}.%(ext)s',
            'retries': 25,
            'fragment_retries': 25,
            'skip_unavailable_fragments': True,
            'keep_fragments': False,
            'buffersize': 1024 * 1024 * 4,  # 4MB buffer
            'http_chunk_size': 1024 * 1024 * 2,  # 2MB chunks
            'concurrent_fragment_downloads': 16,
            'noprogress': True,
            'no_warnings': False,
            'ignoreerrors': False,
            'nocheckcertificate': True,
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'quiet': False,
            'no_color': True,
        }
        
        try:
            logging.info(f"[M3U8 Download] Starting download with yt-dlp library")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Find the downloaded file
                if info:
                    # Try different possible extensions
                    for ext in ['.mp4', '.mkv', '.webm', '']:
                        target_file = f"{safe_name}{ext}"
                        if os.path.isfile(target_file):
                            logging.info(f"✅ M3U8 downloaded successfully: {target_file}")
                            return target_file
                    
                    # If not found with safe_name, try with the original filename from info
                    if 'requested_downloads' in info and info['requested_downloads']:
                        downloaded_file = info['requested_downloads'][0].get('filepath')
                        if downloaded_file and os.path.isfile(downloaded_file):
                            # Rename to expected name
                            target = f"{safe_name}.mp4"
                            os.rename(downloaded_file, target)
                            logging.info(f"✅ Renamed file to: {target}")
                            return target
                            
        except Exception as e:
            logging.error(f"❌ yt-dlp library method failed: {e}")
            logging.info("🔄 Trying fallback method with command line...")
            
            # Fallback to command line yt-dlp
            try:
                fallback_cmd = f'yt-dlp -f "best" "{url}" -o "{safe_name}.%(ext)s" --merge-output-format mp4 --no-check-certificate --concurrent-fragments 16 --retries 25 --fragment-retries 25'
                
                logging.info(f"[M3U8 Fallback] Running: {fallback_cmd}")
                result = subprocess.run(fallback_cmd, shell=True, capture_output=True, text=True, timeout=3600)
                
                if result.returncode == 0:
                    # Check for downloaded file
                    for ext in ['.mp4', '.mkv', '.webm', '']:
                        target_file = f"{safe_name}{ext}"
                        if os.path.isfile(target_file):
                            logging.info(f"✅ Fallback download successful: {target_file}")
                            return target_file
                else:
                    logging.error(f"❌ Fallback command failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logging.error("❌ Download timeout after 1 hour")
            except Exception as e2:
                logging.error(f"❌ Fallback method also failed: {e2}")
    
    else:
        # For non-m3u8 URLs, use the original fast command with sanitized name
        # Replace the name in the cmd with safe_name
        cmd_parts = cmd.split('"')
        if len(cmd_parts) >= 4:
            # Update the output template with sanitized name
            cmd_parts[3] = safe_name
            cmd = '"'.join(cmd_parts)
        
        fast_cmd = f'{cmd} -R 25 --fragment-retries 25 -N 32 --concurrent-fragments 48'
        
        logging.info(f"[Standard Download] Running command: {fast_cmd}")
        result = subprocess.run(fast_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"❌ Download failed: {result.stderr}")

    # Check for any downloaded file with various extensions
    for ext in ["", ".webm", ".mp4", ".mkv", ".mp4.webm"]:
        target_file = safe_name + ext
        if os.path.isfile(target_file):
            logging.info(f"✅ Found downloaded file: {target_file}")
            return target_file
        
        # Also check original name
        target_file = name + ext
        if os.path.isfile(target_file):
            logging.info(f"✅ Found downloaded file with original name: {target_file}")
            # Rename to safe name
            safe_target = safe_name + ext
            try:
                os.rename(target_file, safe_target)
                return safe_target
            except:
                return target_file

    logging.error(f"❌ No output file found after download attempt")
    return safe_name


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
