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

    fast_cmd = f'{cmd} -R 25 --fragment-retries 25 -N 32 --concurrent-fragments 48'

    logging.info(f"[Download Attempt] Running command: {fast_cmd}")
    result = subprocess.run(fast_cmd, shell=True)

    for ext in ["", ".webm", ".mp4", ".mkv", ".mp4.webm"]:
        target_file = name + ext
        if os.path.isfile(target_file):
            return target_file

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


def is_vimeo_json_url(url: str) -> bool:
    """Check if URL is a Vimeo CDN JSON playlist URL (vimeocdn.com/.../playlist.json)"""
    return "vimeocdn.com" in url and "playlist.json" in url


def get_vimeo_base_url(data: dict, playlist_url: str) -> str:
    """Resolve base URL from Vimeo playlist JSON data"""
    base_url = data.get("base_url", "")
    if not base_url.startswith("http"):
        base = "/".join(playlist_url.split("?")[0].split("/")[:-1]) + "/"
        base_url = base + base_url
    return base_url


def _download_vimeo_segment(args):
    """Download a single Vimeo segment (for use in ThreadPoolExecutor)"""
    import requests as req
    idx, seg_url, headers = args
    r = req.get(seg_url, headers=headers, timeout=30)
    r.raise_for_status()
    return idx, r.content


def _download_vimeo_stream(base_url: str, stream: dict, output_file: str, stream_type: str = "video", workers: int = 16):
    """Download all segments of a Vimeo stream (video or audio) using parallel threads"""
    import base64
    import requests as req
    from concurrent.futures import ThreadPoolExecutor, as_completed

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://vimeo.com/"
    }

    stream_base = base_url + stream.get("base_url", "")
    init_segment = stream.get("init_segment")
    segments = stream.get("segments", [])
    total = len(segments)

    logging.info(f"[Vimeo] Downloading {stream_type} ({total} segments) with {workers} threads...")

    tasks = [(i, stream_base + seg["url"], headers) for i, seg in enumerate(segments)]
    results = [None] * total
    completed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_download_vimeo_segment, task): task[0] for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            idx, content = future.result()
            results[idx] = content
            completed += 1

    with open(output_file, "wb") as f:
        if init_segment:
            f.write(base64.b64decode(init_segment))
        for chunk in results:
            if chunk:
                f.write(chunk)

    logging.info(f"[Vimeo] {stream_type} saved: {output_file}")


async def download_vimeo_json(playlist_url: str, output_name: str) -> str:
    """
    Download video from a Vimeo CDN JSON playlist URL.
    Returns path to the final merged .mp4 file, or raises Exception on failure.
    """
    import requests as req

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://vimeo.com/"
    }

    logging.info(f"[Vimeo] Fetching playlist: {playlist_url}")
    response = req.get(playlist_url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    base_url = get_vimeo_base_url(data, playlist_url)

    video_streams = data.get("video", [])
    audio_streams = data.get("audio", [])

    if not video_streams:
        raise Exception("No video streams found in Vimeo playlist JSON")

    best_video = max(video_streams, key=lambda x: x.get("avg_bitrate", 0))
    best_audio = max(audio_streams, key=lambda x: x.get("avg_bitrate", 0)) if audio_streams else None

    logging.info(f"[Vimeo] Quality: {best_video.get('width')}x{best_video.get('height')} @ {best_video.get('avg_bitrate')} bps")

    safe_name = output_name.replace('"', '').replace("'", "")
    temp_video = f"{safe_name}_vimeo_video.mp4"
    temp_audio = f"{safe_name}_vimeo_audio.mp4"
    final_output = f"{safe_name}.mp4"

    # Run blocking downloads in a thread pool to not block the event loop
    loop = asyncio.get_event_loop()

    await loop.run_in_executor(
        None,
        lambda: _download_vimeo_stream(base_url, best_video, temp_video, "video", 16)
    )

    if best_audio:
        await loop.run_in_executor(
            None,
            lambda: _download_vimeo_stream(base_url, best_audio, temp_audio, "audio", 8)
        )
        # Merge video + audio with ffmpeg
        logging.info(f"[Vimeo] Merging video + audio → {final_output}")
        merge_cmd = f'ffmpeg -y -loglevel error -i "{temp_video}" -i "{temp_audio}" -c copy "{final_output}"'
        result = subprocess.run(merge_cmd, shell=True)
        if os.path.exists(temp_video):
            os.remove(temp_video)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        if result.returncode != 0:
            raise Exception("ffmpeg merge failed for Vimeo download")
    else:
        os.rename(temp_video, final_output)

    logging.info(f"[Vimeo] Download complete: {final_output}")
    return final_output


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
