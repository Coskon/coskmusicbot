import yt_dlp

YDL_OPTS = {
    'format': 'bestaudio/best',
    'audioformat': 'mp3',
    'extractaudio': True,
    'quiet': True,
    'skip_download': True,
    'ignoreerrors': True,
    'noplaylist': True,
    'extract_flat': True
}

YOUR_URL = "YOUR_URL_HERE"

with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
    info = ydl.extract_info(f"{YOUR_URL}", download=False)
    for format in info['formats']:
        print(format['format_id'], format['url'])