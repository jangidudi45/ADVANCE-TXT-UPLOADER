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

loop = asyncio.get_event_loop()
sem = asyncio.Semaphore(10)

failed_counter = 0
uploaded_counter = 0
total_counter = 0

start_time = None

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def get_duration():
    current_time = datetime.datetime.now()
    elapsed_time = current_time - start_time
    return elapsed_time


async def get_urls(url):
    async with sem:
        print(url)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(response.status)

                if response.status != 200:
                    raise ValueError("Error: Can't access the webpage")

                content = await response.read()
                data = content.decode('utf-8')

        return data


async def write_urls(data):
    filename = f"Config_Video_list_{time.time()}.txt"

    async with aiofiles.open(filename, mode="a", encoding="utf-8") as file:
        await file.write(data)


async def download_file(url, name, msg, log):

    global failed_counter
    global uploaded_counter

    thumb_name = f"{name}.jpg"

    # if os.path.exists(f"{thumb_name}"):
    #     os.remove(f"{thumb_name}")

    cmd = f'yt-dlp {url} -o "{name}"'

    logging.info(f"Downloading: {name}")

    ka = await download_video(url, cmd, name)

    logging.info(f"Downloaded: {ka}")

    if os.path.exists(ka):
        duration = await get_durationf(name)

        logging.info("Extracting Thumbnail...")

        Ka = await take_jpg(name)

        if Ka:
            logging.info("Thumbnail Extracted Successfully..")
        else:
            logging.info("Thumbnail Extract Failed..")

        await msg.edit(f"Uploading : {name}")

        logging.info("Uploading...")

        k = False
        for i in range(3):
            try:
                if os.path.exists(thumb_name):
                    res = await msg.reply_video(f"{ka}",
                                                supports_streaming=True,
                                                caption=log,
                                                duration=duration,
                                                thumb=thumb_name,
                                                progress=progress_bar)
                else:
                    res = await msg.reply_video(f"{ka}",
                                                supports_streaming=True,
                                                caption=log,
                                                duration=duration,
                                                progress=progress_bar)

                k = True
                break
            except Exception as e:
                logging.error(f"Failed to upload.. Retrying {i+1}/3 error: {e}")
                await asyncio.sleep(5)

        if k:
            uploaded_counter += 1
            await msg.edit(f"Uploaded : {name}")
        else:
            await msg.edit(f"Video `{name}` Upload failed..")
            failed_counter += 1

        if os.path.exists(ka):
            os.remove(ka)
        if os.path.exists(thumb_name):
            os.remove(thumb_name)
    else:
        failed_counter += 1
        await msg.edit(f"Video `{name}` Download failed..")

    return


def download(url, name, msg, log):

    # res = loop.create_task(download_file(url, name, msg, log))
    # loop.run_until_complete(asyncio.wait([res]))

    try:
        loop.run_until_complete(download_file(url, name, msg, log))
    except Exception as e:
        logging.error(f"Download Error: {e}")


async def get_durationf(name):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        name
    ]

    # print(cmd)

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        # logging.error(f"Error: {stderr.decode()}")
        print(stderr.decode())
        return None

    try:
        duration = float(stdout.decode().strip())
    except Exception:
        duration = None

    return duration


async def take_jpg(name):
    cmd = [
        "ffmpeg", "-i", name,
        "-ss", "00:00:01.000",
        "-vframes", "1",
        f"{name}.jpg", "-y"
    ]

    # print(cmd)

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        # logging.error(f"Error: {stderr.decode()}")
        print(stderr.decode())
        return False

    return True


async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False) as response:
            if response.status == 200:
                text = await response.read()
                return text
            else:
                return False


async def write_json(value, text):
    try:
        name = (value.replace(": ", "-").replace(" ", "_").replace("/", "_").replace("|", "_").replace("\\", "_")
                .replace(":", "_").replace("!", "_").replace('"', "_").replace("'", "_").replace("*", "_")
                .replace("?", "_").replace("<", "_").replace(">", "_"))

        async with aiofiles.open(f"{name}.txt", mode="a", encoding="utf-8") as file:
            await file.write(text)
        return True
    except Exception as e:
        logging.error(e, exc_info=True)
        return False


async def get_response(session, url):
    try:
        async with session.get(url, ssl=False) as response:
            if response.status == 200:
                text = await response.read()
                return text
            else:
                return None
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None


def get_hls(urls, html):
    x = html.split(urls)

    x = x[1]

    x = x.split(".vtt")[0]

    t = x.split("https")

    ko = []

    for i in t:
        if ".m3u8" in i:
            ko.append("https" + i.split('"""')[0])

    return ko


def hj(urls, text, urls2=None):
    x = text.split(urls)

    k = text.split(urls)[0].splitlines().pop()

    vidname = k.split(" ", 1)[1].split("|", 1)[0].strip()

    # print(x[1])

    if ".m3u8" in x[1]:
        ka = x[1].split(".m3u8")[0].rsplit(" ", 1)[-1].replace('"', '').replace("\\", "") + ".m3u8"
    else:
        ka = x[1].split(".mp4")[0].rsplit(" ", 1)[-1].replace('"', '').replace("\\", "") + ".mp4"

    print(vidname)
    print("HLS_URL - " + ka)

    if urls2 is not None:
        sk = get_hls(urls2, text)
        print("iframe_hls url - ", sk)
        ka = ka + "|" + str(sk)

    return f"{vidname}|{ka}"


async def download_video(url, cmd, name):
    global failed_counter

    # ✅ Special fast-path for direct Unacademy .webm links
    if "uamedia.uacdn.net" in url and url.endswith(".webm"):
        file_name = f"{name}.webm"
        logging.info(f"[FAST] Detected Unacademy direct .webm, downloading without yt-dlp: {url}")

        try:
            # Big chunks for faster throughput (4 MB)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(file_name, "wb") as f:
                    for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
                        if chunk:
                            f.write(chunk)

            # Verify file created
            if os.path.isfile(file_name):
                logging.info(f"[FAST] Direct download completed: {file_name}")
                return file_name
            else:
                logging.warning(f"[FAST] File not found after direct download, falling back to yt-dlp...")
        except Exception as e:
            logging.error(f"[FAST] Direct download failed, falling back to yt-dlp: {e}")

    # 🔁 Normal path for all other URLs (and fallback)
    fast_cmd = f'{cmd} -R 25 --fragment-retries 25 -N 32 --concurrent-fragments 48'
    logging.info(f"[Download Attempt] Running command: {fast_cmd}")
    result = subprocess.run(fast_cmd, shell=True)

    # Check for common file outputs
    for ext in ["", ".webm", ".mp4", ".mkv", ".mp4.webm"]:
        target_file = name + ext
        if os.path.isfile(target_file):
            return target_file

    return name


def extract_text(ko):
    mk = ""
    io = 0

    for i in ko.splitlines():
        if "HLS URL" in i:
            io += 1
            mk += i

    return mk, io


def parse_m3u8_info(info, base_uri):
    info = info.strip().split("\n")
    new_info = []
    temp = []
    for i in info:
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")

            i = i.strip()
            i = i.split("|")[0].split(" ", 1)[1]

            # print(i)
            # exit()

            try:
                url = i
                if 'https://akamai' in url and "index" not in url and url not in temp:
                    res = url.split(".m3u8")
                    url = res[0].replace("_720", "").replace("_480", "").replace("unified_", "") + ".m3u8"

                if url not in temp and "na-all" not in url:
                    new_info.append(
                        f"Resolution: {url}"
                    )
                    temp.append(url)
            except Exception:
                pass

    base_name = ""
    for i in base_uri.split("/"):
        if "." in i:
            base_name = i

    return "".join(new_info), base_name


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

                    name = i[2]
                    ep_id_name = i[0].replace("[", "").replace("]", "")
                    lesson_id_name = i[1].split("-")[1]
                    video_id_name = i[1].split("-")[0]

                    name = name.replace(" ", "_").replace("|", "_").replace("/", "_").replace("\\", "_").replace(":",
                                                                                                                  "_").replace(
                        "!", "_") \
                        .replace('"', "_").replace("'", "_").replace("*", "_").replace("?", "_").replace("<", "_") \
                        .replace(">", "_")

                    new_info.append(
                        f"[{ep_id_name}][{video_id_name}-{lesson_id_name}] {name}\n"
                    )

                    # new_info.append(
                    #     f"{i[2]}\n"
                    # )
            except Exception:
                pass

    # print("".join(new_info))

    return "".join(new_info)


def write_vid_name(info):
    with open("VidName.txt", "w", encoding="utf-8") as f:
        f.write(info)

    return


def write_m3u8_info(info):
    with open("vid_list.txt", "w", encoding="utf-8") as f:
        f.write(info)

    return


def generate_download_url(res, raw_urls):
    # print(res)
    # print(raw_urls)
    url_string = ""

    # raw_urls = raw_urls.split(",")

    for i in res.splitlines():
        try:
            name = i.split("[", 1)[1].split(" ", 1)[1].strip() + ".webm"
        except Exception:
            name = i.split("[", 1)[1].strip() + ".webm"

        # Create unique file names by appending an index if the file already exists
        original_name, extension = os.path.splitext(name)
        counter = 1
        while os.path.isfile(name):
            name = f"{original_name}_{counter}{extension}"
            counter += 1

        lesson_id = i.split("[", 1)[1].split("]", 1)[0]

        url = none

        concate_lesson_id = ""
        for urls in raw_urls:
            if lesson_id in urls.split("|")[0]:
                concate_lesson_id += urls.split("|")[1] + "|"

        for urls in concate_lesson_id.split("|"):
            if "akamai" in urls and "index" not in urls and urls != " " and urls != "":
                url = urls.replace('"', '').replace("\\", "").replace("_720", "").replace("_480", "").replace("unified_", "") + ".m3u8"
                break

            if "akamai" not in urls and urls != " " and urls != "":
                url = urls.replace('"', '').replace("\\", "")
                break

        if url is None:
            continue

        url_string += f"Name : {name}\n"
        url_string += f"ID : {lesson_id}\n"
        url_string += f"URL : {url}\n"
        url_string += f"\n"

    with open("Download_info.txt", "w", encoding="utf-8") as f:
        f.write(url_string)

    return


def download_main():
    with open("Download_info.txt", "r", encoding="utf-8") as f:
        data = f.read()

    if len(data.strip()) < 5:
        logging.info("Download_info.txt is blank..")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        loop = asyncio.get_event_loop()
        futures = []

        for i in data.split("\n\n"):
            if len(i) < 5:
                continue

            try:
                name = i.split("Name : ")[1].split("\n", 1)[0].strip()
                url = i.split("URL : ")[1].strip()
                log = i.split("Name : ")[1].strip()

                msg = loop.run_until_complete(download_msg.send_message("Downloading: " + name.split(".mkv")[0]))

                future = executor.submit(download, url, name, msg, log)
                futures.append(future)

            except Exception as e:
                logging.error(e, exc_info=True)

        for future in concurrent.futures.as_completed(futures):
            pass

    return


def none():
    return None


def write_cmds(urls, name):
    url_string = ""

    for i in urls.splitlines():
        name_ = i.split("|")[0]
        cmd = i.split("|")[1].replace(" ", "").split(",")[:2]
        cmd.append("")
        cmd.sort()

        url = cmd[0]

        url_string += f"Name : {name_}\n"
        url_string += f"ID : {name_}\n"
        url_string += f"URL : {url}\n"
        url_string += f"\n"

    with open(name, "w", encoding="utf-8") as f:
        f.write(url_string)

    return


def write_cmds_1(urls, name):
    url_string = ""

    for i in urls.splitlines():
        name_ = i.split("|")[0]
        url = i.split("|")[1]

        if "|" in url:
            cmd = url.replace(" ", "").split("|")[1].replace("\\n", "").split(",")[:2]
            # cmd.append("")
            cmd[1] = ""
            cmd.sort()

            url = cmd[0]
        elif "input_master.mpd" in url:
            cmd = [
                "python", "-m", "yt_dlp",
                url,
                "-N", "32",
                "-o", f"{name_}.webm",
                "-S", "res:720"
            ]
        else:
            cmd = [
                "python", "-m", "yt_dlp",
                url,
                "-N", "32",
                "-o", f"{name_}.webm"
            ]
        url_string += f"Name : {name_}\n"
        url_string += f"ID : {name_}\n"
        url_string += f"URL : {url}\n"
        url_string += f"\n"

    with open(name, "w", encoding="utf-8") as f:
        f.write(url_string)

    return


def hjjk(urls, text):
    x = text.split(urls)

    k = text.split(urls)[0].splitlines().pop()

    vidname = k.split(" ", 1)[1].split("|", 1)[0].strip()

    # print(x[1])
    ka = x[1].split("stream_url")[1].split(",", 1)[0].rsplit(" ", 1)[-1].replace('"', '').replace("\\", "")

    y = x[1].split("[INFO] HLS URL - ", 1)[1]
    ka = y.split("\n\n[INFO]")[0]

    print(vidname)
    print(ka)

    return f"{vidname}|{ka}"


def write_stream_url(info):
    with open("stream_info.txt", "w", encoding="utf-8") as f:
        f.write(info)

    return
