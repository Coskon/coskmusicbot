import discord
import asyncio
import utilidades
import spotipy
import datetime
import random, traceback, time, configparser, math
from discord.ext import commands, tasks
from pydub import AudioSegment
from io import BytesIO
from shazamio import Shazam
import subprocess
from pytube import Playlist, Search, YouTube
from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor
from extras import *
from fuzzywuzzy import process

## BOT INITIALIZATION ##
intents = discord.Intents.default()
intents.voice_states, intents.message_content, intents.members = (True for _ in range(3))
activity = discord.Activity(type=discord.ActivityType.listening, name=".play")

## CONFIG AND LANGUAGE ##
config_path = "config.ini"
config = configparser.ConfigParser()
try:
    with open(config_path, "r") as f:
        config.read_string(f.read())
except:
    config.add_section("Config")
    config.set("Config", "lang", "en")
    with open(config_path, "w") as f:
        config.write(f)

language = config.get('Config', 'lang').lower()
try:
    with open(f"lang/{language}.json", "r") as f:
        lang_dict = json.load(f)
except:
    subprocess.run(["python.exe", "lang/lang.py"])
    with open(f"lang/{language}.json", "r") as f:
        lang_dict = json.load(f)

globals().update(lang_dict)

## PARAMETER VARIABLES ##
parameters = read_param()
if len(parameters.keys()) < ALL_PARAM_COUNT:
    input(f"\033[91m{missing_parameters}\033[0m")
    write_param()
    parameters = read_param()

globals().update(parameters)

## API KEYS ##
USE_PRIVATE_TOKENS = False
if USE_PRIVATE_TOKENS:
    DISCORD_APP_KEY = os.getenv('DISCORD_APP_KEY')
else:
    with open('API_KEYS.txt', 'r') as f:
        DISCORD_APP_KEY = f.read().split("\n")[0].split("=")[1]

TENOR_API_KEY = utilidades.TENOR_API_KEY
OPENAI_KEY = utilidades.OPENAI_API_KEY
GENIUS_ACCESS_TOKEN = utilidades.GENIUS_ACCESS_TOKEN
SPOTIFY_ID = utilidades.SPOTIFY_ID
SPOTIFY_SECRET = utilidades.SPOTIFY_SECRET

if not DISCORD_APP_KEY:
    print(f"\033[91mDISCORD_APP_KEY {api_key_not_found}\033[0m")
    raise Exception
if not TENOR_API_KEY:
    print(f"\033[91mTENOR_API_KEY {api_key_not_found}\033[0m")
if not OPENAI_KEY:
    print(f"\033[91mOPENAI_KEY {api_key_not_found}\033[0m")
if not GENIUS_ACCESS_TOKEN:
    print(f"\033[91mGENIUS_ACCESS_TOKEN {api_key_not_found}\033[0m")
if not SPOTIFY_ID:
    print(f"\033[91mSPOTIFY_ID {api_key_not_found}\033[0m")
if not SPOTIFY_SECRET:
    print(f"\033[91mSPOTIFY_SECRET {api_key_not_found}\033[0m")
if SPOTIFY_ID and SPOTIFY_SECRET:
    SPOTIFY_CREDENTIAL_MANAGER = utilidades.SPOTIFY_CREDENTIAL_MANAGER
    sp = spotipy.Spotify(client_credentials_manager=SPOTIFY_CREDENTIAL_MANAGER)

## GLOBAL VARIABLES ##
dict_queue, dict_current_song, active_servers = dict(), dict(), dict()
button_choice, vote_skip_dict, vote_skip_counter = dict(), dict(), dict()
message_id_dict, majority_dict, ctx_dict_skip = dict(), dict(), dict()
song_start_times, paused_durations, pause_start_times = dict(), dict(), dict()
user_cooldowns = {}
loop_mode = dict()
go_back, seek_called, disable_play = (False for _ in range(3))
INV_CHAR_PADDING = "᲼"*5
DEFAULT_OPTIONS = { "search_limit": DEFAULT_SEARCH_LIMIT, "recomm_limit": DEFAULT_RECOMMENDATION_LIMIT,
                       "custom_prefixes": DEFAULT_PREFIXES, "restricted_to": "ALL_CHANNELS" }
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -sn'
}
YDL_OPTS = {
    'format': 'bestaudio/best',
    'audioformat': 'mp3',
    'extractaudio': True,
    'quiet': True,
    'skip_download': True,
    'ignoreerrors': True,
    'noplaylist': True,
    'extract_flat': True,
    'cookiefile': './cookies.txt' if os.path.exists('./cookies.txt') else None,
}
PREFERRED_FORMATS = {'http', 'mp4', 'Audio_Only', '1'}
EXTRA_FORMATS = {'160p', '360p', '480p', '720p60', '1080p60', '0', '2', 'hls_mp3_128', 'http_mp3_128', 'hls_opus_64',
                 'hls', 'f5-a1-x3', 'f3-a1-x3', 'f1-a1-x3', 'f4-v1-x3', 'f5-v1-x3', 'f3-v1-x3', 'f2-v1-x3', 'f1-v1-x3'}

## NORMAL FUNCTIONS ##
def get_sp_id(url):
    # Extract the track ID from the Spotify URL
    pattern = r'\/track\/([a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Spotify URL")


def get_video_info(video):
    global dict_queue
    try:
        if isinstance(video, str):
            video = info_from_url(video, is_url=is_url(video))
        return video
    except:
        traceback.print_exc()


def create_options_file(file_path, force=False):
    if not os.path.exists(file_path) or force:
        with open(file_path, 'w') as f:
            json.dump(DEFAULT_OPTIONS, f)


def get_audio_channels(stream_url):
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=channels',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        stream_url
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
        return int(result.stdout.strip())
    except subprocess.TimeoutExpired:
        return 2


def get_updated_options(vid, curr_time, get_options_only=False):
    channels_info = 'pan=1c|c0=c0+c1' if vid['audio_options']['channels'] == 1 else 'pan=stereo|c0=c0|c1=c1'
    str_command_prompt = f' -filter:a "{channels_info},rubberband=pitch={vid["audio_options"]["pitch"]}, ' \
                         f'rubberband=tempo={vid["audio_options"]["speed"]}, ' \
                         f'volume={vid["audio_options"]["volume"]}dB, ' \
                         f'equalizer=f=300:width_type=h:width=120:g={vid["audio_options"]["bass"]}, ' \
                         f'equalizer=f=8000:width_type=h:width=3000:g={vid["audio_options"]["high"]}"'

    if get_options_only:
        return str_command_prompt

    updated_options = FFMPEG_OPTIONS.copy()
    updated_options['before_options'] += f' -ss {curr_time}'
    updated_options['options'] += str_command_prompt
    return updated_options


def write_options(options, gid, missing_opts: list):
    file_path = f'options_{gid}.json'
    for opt in missing_opts:
        options[opt] = DEFAULT_OPTIONS[opt]
    with open(file_path, 'w') as f:
        json.dump(options, f)
    return options


def get_current_time(gid):
    global song_start_times, pause_start_times, paused_durations
    if gid in song_start_times:
        start_time = song_start_times[gid]
        current_time = datetime.datetime.now()

        # Adjust the elapsed time for any pauses
        if pause_start_times[gid] is not None:
            # If currently paused, add the ongoing pause duration to the total paused duration
            pause_duration = current_time - pause_start_times[gid]
        else:
            pause_duration = datetime.timedelta()

        elapsed_time = (current_time - start_time) - (paused_durations[gid] + pause_duration)
        return elapsed_time.total_seconds()
    else:
        return 0


def get_playlist_duration(playlist_url, urls, total_extracted):
    PLAYLIST_YDL_OPTS = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
        'playlist-end': 1,
        'ignoreerrors': True
    }

    with YoutubeDL(PLAYLIST_YDL_OPTS) as ydl:
        playlist_info = ydl.extract_info(playlist_url, download=False)

        total_duration, total = 0, 0
        videos = playlist_info['entries']
        for video in videos:
            if video['duration'] and video['url'] in urls:
                total_duration += video['duration']
                total += 1
            if total >= total_extracted:
                break
    return total_duration, len(videos), total


def create_perms_file(ctx, file_path, force=False):
    if not os.path.exists(file_path) or force:
        server = ctx.guild
        userdict = dict()
        for member in server.members:
            if member.guild_permissions.administrator:
                userdict[str(member.id)] = ADMIN_PERMS
            else:
                userdict[str(member.id)] = DEFAULT_USER_PERMS
        with open(file_path, 'w') as f:
            json.dump(userdict, f)


def on_song_end(ctx, error):
    global dict_current_song, go_back, seek_called, loop_mode
    if error:
        print(f"{generic_error}: {error}")
    if seek_called:
        seek_called = False
    else:
        gid = str(ctx.guild.id)
        loop_mode.setdefault(gid, "off")
        if loop_mode[gid] == 'one':
            pass
        elif go_back:
            dict_current_song[gid] -= 1
        else:
            dict_current_song[gid] += 1
        try:
            del song_start_times[gid]
            del pause_start_times[gid]
            del paused_durations[gid]
        except:
            pass
        bot.loop.create_task(play_next(ctx))


def get_channel_picture(channel_url):
    response = requests.get(channel_url)
    if response.status_code == 200:
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        meta_tag = soup.find('meta', {'property': 'og:image'})
        if meta_tag:
            image_url = meta_tag.get('content')
            return image_url
    return None


def get_stream_url(stream_info: dict, itags: list):
    for itag in itags:
        stream_url = next((d.get("url") for d in stream_info if d.get("itag") == itag), None)
        if stream_url: return stream_url
    return


def fetch_info(result):
    vtype = 'video'
    try:
        streaming_data = result.streaming_data
        stream_url = get_stream_url(streaming_data['formats'], itags=ITAGS_LIST)  # get best stream url if possible
        if not stream_url:
            stream_url = get_stream_url(streaming_data['adaptiveFormats'], itags=ITAGS_LIST)  # get best stream url if possible
    except:
        try:
            streaming_data = result.streaming_data
            stream_url = streaming_data['hlsManifestUrl']
            vtype = 'live'
        except:  # ABSOLUTE LAST RESORT, THE MYTH THE LEGEND YT-DLP
            if SKIP_PRIVATE_SEARCH: return None
            try:
                with YoutubeDL(YDL_OPTS) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={result.video_id}", download=False)
                    stream_url = None
                    if 'is_live' in info and info['is_live']:
                        vtype = 'live'
                        stream_url = info['formats'][0]['url']
                    else:
                        vtype = 'video'
                    for formats in info['formats']:
                        fid = formats['format_id'].split("-")[0]
                        if fid in {'233', '234'}:
                            stream_url = formats['url']
                            break
                        elif fid in {'139', '249', '250', '140', '251'}:
                            stream_url = formats['url']
                            break
                        elif fid in EXTRA_FORMATS | PREFERRED_FORMATS:
                            stream_url = formats['url']
                            break
                    if not stream_url:
                        stream_url = info['formats'][0]['url']
            except:
                return None
    try:
        channels = get_audio_channels(stream_url)
    except:
        channels = 2
    return {
        'obj': result, 'title': cut_str_length(result.title), 'channel': cut_str_length(result.author), 'views': result.views,
        'length': int(result.length), 'id': result.video_id, 'thumbnail_url': result.thumbnail_url,
        'url': result.watch_url, 'stream_url': stream_url, 'channel_url': result.channel_url, 'type': vtype,
        'channel_image': get_channel_picture(result.channel_url), 'audio_options':
            {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'channels': channels, 'bass': 0.0, 'high': 0.0}
        # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
    }


def search_youtube(query, max_results=18):
    tmp_l = Search(query).results[:max_results]
    with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
        results = executor.map(fetch_info, tmp_l)
    return list(filter(None, results))


def info_from_url(query, is_url=True, not_youtube=False):
    url = query if is_url else f"https://www.youtube.com/watch?v={query}"
    try:
        result = YouTube(url)
        if result.vid_info['playabilityStatus']['status'] == 'ERROR':
            raise Exception
    except:
        not_youtube = True
    vtype = 'video'
    try:
        streaming_data = result.streaming_data
        stream_url = get_stream_url(streaming_data['formats'], itags=ITAGS_LIST)  # get best stream url if possible
        if not stream_url:
            stream_url = get_stream_url(streaming_data['adaptiveFormats'], itags=ITAGS_LIST)  # get best stream url if possible
    except:
        try:
            streaming_data = result.streaming_data
            stream_url = streaming_data['hlsManifestUrl']
            vtype = 'live'
        except: # ABSOLUTE LAST RESORT, THE MYTH THE LEGEND YT-DLP
            try:
                account = get_account_data(url)
                YDL_OPTS.update({
                    'username': account['username'],
                    'password': account['password']
                })
                with YoutubeDL(YDL_OPTS) as ydl:
                    info = ydl.extract_info(url, download=False)
                    stream_url = None
                    if 'is_live' in info and info['is_live']:
                        vtype = 'live'
                        stream_url = info['formats'][0]['url']
                    else:
                        vtype = 'video'
                    for formats in info['formats']:
                        fid = formats['format_id'].split("-")[0]
                        if fid in {'233', '234'}:
                            stream_url = formats['url']
                            break
                        elif fid in {'139', '249', '250', '140', '251'}:
                            stream_url = formats['url']
                            break
                        elif fid in PREFERRED_FORMATS:
                            stream_url = formats['url']
                            break
                    if not stream_url:
                        fid = formats['format_id'].split("-")[0]
                        for formats in info['formats']:
                            if fid in EXTRA_FORMATS:
                                stream_url = formats['url']
                                break
                        if not stream_url:
                            stream_url = info['formats'][0]['url']
            except:
                stream_url = None
    if not_youtube:
        try: thumb = info['thumbnail']
        except: thumb = None
        try: dur = info['duration']
        except: dur = 0
        try: title = cut_str_length(info['title'])
        except: title = 'Some audio'
        try: channel = cut_str_length(info['uploader'])
        except: channel = 'Someone'
        try: views = info['view_count']
        except: views = 'A lot, probably'
        try:
            channels = get_audio_channels(stream_url)
        except:
            channels = 2
        return {
            'obj': None, 'title': title, 'channel': channel, 'views': views,
            'length': dur, 'id': None, 'thumbnail_url': thumb,
            'url': url, 'stream_url': stream_url, 'channel_url': None, 'type': vtype, 'channel_image': None,
            'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'channels': channels, 'bass': 0.0, 'high': 0.0}
            # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
        }
    try:
        channels = get_audio_channels(stream_url)
    except:
        channels = 2
    return {
        'obj': result, 'title': cut_str_length(result.title), 'channel': cut_str_length(result.author), 'views': result.views,
        'length': int(result.length), 'id': result.video_id, 'thumbnail_url': result.thumbnail_url,
        'url': result.watch_url, 'stream_url': stream_url, 'channel_url': result.channel_url, 'type': vtype,
        'channel_image': get_channel_picture(result.channel_url), 'audio_options':
            {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'channels': channels, 'bass': 0.0, 'high': 0.0}
        # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
    }


def change_active(ctx, mode="a"):
    global active_servers
    active_servers[str(ctx.guild.id)] = 1 if mode == "a" else 0
    print(f"{'active on' if mode == 'a' else 'left'} -> {ctx.guild.name}")


def check_perms(ctx, perm):
    file_path = f'user_perms_{ctx.guild.id}.json'
    create_perms_file(ctx, file_path)
    try:
        with open(file_path, 'r') as f:
            user_perms = json.load(f)
    except:
        create_perms_file(ctx, file_path, force=True)
        with open(file_path, 'r') as f:
            user_perms = json.load(f)
    if perm not in user_perms[str(ctx.author.id)]:
        return False
    return True


def get_channel_restriction(ctx):
    gid = ctx.guild.id
    file_path = f'options_{gid}.json'
    create_options_file(file_path)
    try:
        with open(file_path, 'r') as f:
            options = json.load(f)
    except:
        create_options_file(file_path, force=True)
        with open(file_path, 'r') as f:
            options = json.load(f)
    if not 'restricted_to' in options:
        options = write_options(options, str(gid), ['restricted_to'])
    return (ctx, True) if options['restricted_to'] == 'ALL_CHANNELS' \
        else (discord.utils.get(ctx.guild.channels, name=options['restricted_to']), False)


def write_to_playlist(file_path, playlist):
    data = read_playlists(file_path, bot)
    data.update(playlist)
    with open(file_path, 'w') as f:
        json.dump(data, f)


def read_playlists(file_path, bot):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({'favs': {'songs': [], 'creator': {'avatar': str(bot.user.avatar), 'display_name': str(bot.user.display_name), 'name': str(bot.user.name)}}}, f)
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


def find_command_info(command_name):
    for category, commands in COMMANDS_INFO.items():
        for command, info in commands.items():
            aliases = info['aliases'] if 'aliases' in info else []
            if command == command_name or command_name in aliases:
                return command, info
    return None, None


## ASYNC FUNCTIONS ##
async def choice(ctx, embed, reactions):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        message = await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        for rct in reactions:
            await message.add_reaction(rct)

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions

        try:
            choice, _ = await bot.wait_for('reaction_add', timeout=TIMELIMIT, check=check)
            await message.delete()
            return str(choice.emoji)
        except asyncio.TimeoutError:
            await message.delete()
            await channel_to_send.send(random.choice(song_not_chosen_texts), reference=ctx.message if REFERENCE_MESSAGES else None)
            return
    except:
        traceback.print_exc()


async def play_next(ctx, rewinded=0):
    global dict_current_song, loop_mode, dict_queue, disable_play, go_back
    go_back = False
    gid = str(ctx.guild.id)
    if discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild) is None:
        dict_queue[gid] = []
        dict_current_song[gid] = 0
        try:
            del song_start_times[gid]
            del pause_start_times[gid]
            del paused_durations[gid]
        except:
            pass
        disable_play = False
        return
    await asyncio.sleep(0.25)
    dict_queue.setdefault(gid, list())
    dict_current_song.setdefault(gid, 0)
    if rewinded == 1: dict_current_song[gid] -= 1
    elif rewinded == 2: dict_current_song[gid] += 1
    queue = dict_queue[gid]
    current_song = dict_current_song[gid]
    auto = False
    if current_song < 0: dict_current_song[gid] = 0
    if current_song >= len(queue):
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] in ['queue', 'all']:
            dict_current_song[gid] = 0
        elif loop_mode[gid] in ['random', 'shuffle']:
            dict_current_song[gid] = random.randint(0, len(queue) - 1)
        elif loop_mode[gid] == "autodj":
            auto = True
        else:
            await leave(ctx, ignore=True, disconnect=DISCONNECT_AFTER_QUEUE_END, ended_queue=True)
            return
    if auto:
        await autodj(ctx, ignore=True)
    elif queue:
        url = queue[dict_current_song[gid]]
        await ctx.invoke(bot.get_command('play'), url=url, append=False, attachment=False)


async def update_level_info(ctx, user_id, xp_add):
    try:
        server = ctx.guild
        level_file_path = f'level_data_{server.id}.json'
        if not os.path.exists(level_file_path):
            await restart_levels(ctx)
        with open(level_file_path, 'r') as json_file:
            datos = json.load(json_file)
        k, prev = 0, 0
        for i in range(len(datos)):
            if user_id == datos[i]['id']:
                datos[i]['xp'] += xp_add
                while True:
                    prev = k
                    if datos[i]['xp'] >= datos[i]['next_xp']:
                        datos[i]['lvl'] += 1
                        datos[i]['next_xp'] += LVL_NEXT_XP
                        k += 1
                    if prev == k: break
                break
        with open(level_file_path, 'w') as f:
            json.dump(datos, f)
    except:
        traceback.print_exc()


async def find_song_shazam(url, start, total_length, vtype, clip_length=15):
    try:
        if start > total_length - 10: start -= 10
        start = max(0, start)
        clip_length = min(max(1, clip_length), 59)

        if vtype == 'live' or total_length == 0:
            start_byte = int(start * 7812)  # estimate
            headers = {
                'Range': f'bytes={start_byte}-'
            }
        else:
            start_byte = int((start / total_length) * 1000000)  # estimate
            end_byte = start_byte + int((clip_length / total_length) * 1000000)
            headers = {
                'Range': f'bytes={start_byte}-{end_byte}'
            }
        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH)
        try:
            start_time = '00:00:00' if vtype == 'live' else '00:' * (start < 3600) + convert_seconds(start)
            end_time = f'00:00:{clip_length}' if vtype == 'live' else '00:' * (start + 10 < 3600) + convert_seconds(
                start + clip_length)
            subprocess.run(['ffmpeg', '-ss', start_time, '-to', end_time, '-i', url, '-y', DOWNLOAD_PATH+'shazam.mp3'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            try:
                print("ffmpeg failed, moving to pydub...")
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                AudioSegment.from_file(BytesIO(response.content), start_second=start, duration=clip_length).export(DOWNLOAD_PATH+'shazam.mp3', format='mp3')
            except:
                print("pydub failed")
                return None

        shazam = Shazam()
        out = await shazam.recognize(DOWNLOAD_PATH+'shazam.mp3')
        if not out or not out['matches']: return None
        return out['track']
    except:
        traceback.print_exc()


async def change_channels(ctx, channels):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_change_channels"):
            await channel_to_send.send(random.choice(insuff_perms_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        if voice_client.is_playing(): voice_client.pause()
        channels = min(max(int(channels), 1), 2)
        vid['audio_options']['channels'] = channels
        updated_options = get_updated_options(vid, get_current_time(gid))
        voice_client.play(discord.FFmpegPCMAudio(queue[current_song]['stream_url'], **updated_options),
                          after=lambda e: on_song_end(ctx, e))
        await channel_to_send.send(change_channels_mode.replace("%mode", 'mono' if channels == 1 else 'stereo'), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


bot = commands.Bot(command_prefix="DEF_PREFIX", activity=activity, intents=intents, help_command=None,
                   case_insensitive=True)


## CLASSES ##
class PlayButton(discord.ui.Button):
    def __init__(self, song_index, gid, disabled=False):
        self.song_index = song_index
        self.gid = gid
        super().__init__(label="", style=discord.ButtonStyle.success if 0 <= song_index < 5 else discord.ButtonStyle.secondary,
                         emoji=f"{['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '🔀', '⬅️', '❌', '➡️', '🇦'][song_index if song_index != -1 else 7]}",
                         disabled=disabled, custom_id=str(song_index))
    async def callback(self, interaction):
        global button_choice
        button_choice[self.gid] = self.song_index


class SongChooseMenu(discord.ui.View):
    def __init__(self, gid):
        super().__init__()
        # song choice buttons
        for i in range(10):
            if i == 7: self.add_item(PlayButton(-1, gid)) # cancel
            else: self.add_item(PlayButton(i, gid)) # other buttons


class QueueMenu(discord.ui.View):
    def __init__(self, queue, num_pages, ctx, gid):
        super().__init__(timeout=None)
        self.queue = queue
        self.num_pages = num_pages
        self.current_page = 1
        self.gid = gid
        self.ctx = ctx  # to check for perms

    @discord.ui.button(label="", emoji="🔃", style=discord.ButtonStyle.secondary)
    async def button_reverse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id == interaction.user.id:
            successful = await reverse(self.ctx)
            if successful:
                self.queue = dict_queue[self.gid].copy()
                self.current_page = 1
                await self.update_message(interaction)
                return
        await interaction.response.defer()

    @discord.ui.button(label="", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def button_prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id == interaction.user.id:
            if self.current_page > 1:
                self.current_page -= 1
            await self.update_message(interaction)
            return
        await interaction.response.defer()

    @discord.ui.button(label="", emoji="❌", style=discord.ButtonStyle.secondary)
    async def button_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id == interaction.user.id:
            await self.update_message(interaction, True)
            return
        await interaction.response.defer()

    @discord.ui.button(label="", emoji="➡️", style=discord.ButtonStyle.secondary)
    async def button_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id == interaction.user.id:
            if self.current_page < self.num_pages:
                self.current_page += 1
            await self.update_message(interaction)
            return
        await interaction.response.defer()

    @discord.ui.button(label="", emoji="🔀", style=discord.ButtonStyle.secondary)
    async def button_shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        global dict_queue
        if self.ctx.author.id == interaction.user.id:
            successful = await shuffle(self.ctx)
            if successful:
                self.queue = dict_queue[self.gid].copy()
                self.current_page = 1
                await self.update_message(interaction)
                return
        await interaction.response.defer()

    async def update_message(self, interaction: discord.Interaction, cancelled=False):
        if cancelled:
            await interaction.message.delete()
            return
        embed = self.create_embed()
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    def create_embed(self):
        global dict_current_song
        start_index = (self.current_page - 1) * QUEUE_VIDEOS_PER_PAGE
        end_index = start_index + QUEUE_VIDEOS_PER_PAGE
        with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
            self.queue[start_index:end_index] = dict_queue[self.gid][start_index:end_index] = \
                list(executor.map(get_video_info, self.queue[start_index:end_index]))
        title_queue = [vid['title'] for vid in self.queue[start_index:end_index]]
        MAX_LENGTH = 70
        page_content = [
            f"{pos+1+QUEUE_VIDEOS_PER_PAGE*(self.current_page-1)}. {title[:(MAX_LENGTH-len(str(pos+1+QUEUE_VIDEOS_PER_PAGE*(self.current_page-1))))]}"+
            "..."*int(len(title) > (MAX_LENGTH-len(str(pos+1+QUEUE_VIDEOS_PER_PAGE*(self.current_page-1)))))
            for pos, title in enumerate(title_queue)
        ]  # cut titles length
        curr = max(0, dict_current_song[self.gid])
        if (self.current_page - 1) * QUEUE_VIDEOS_PER_PAGE <= curr <= self.current_page * QUEUE_VIDEOS_PER_PAGE and curr < len(self.queue):
            page_content[curr % QUEUE_VIDEOS_PER_PAGE] = f"`{page_content[curr % QUEUE_VIDEOS_PER_PAGE][:MAX_LENGTH-len(queue_current)]+'...'*int(len(page_content[curr % QUEUE_VIDEOS_PER_PAGE][:MAX_LENGTH]) > MAX_LENGTH-3)}{queue_current}"
        if any(isinstance(vid, str) for vid in self.queue):
            videos_with_length = filter(lambda vid: not isinstance(vid, str), dict_queue[self.gid])
            not_all = True
        else:
            videos_with_length = self.queue.copy()
            not_all = False
        embed = discord.Embed(
            title=queue_title,
            description="\n".join(page_content),
            color=EMBED_COLOR
        )
        embed.add_field(name=queue_pages, value=f"`{self.current_page}/{self.num_pages}`"+INV_CHAR_PADDING)
        embed.add_field(name=queue_videos, value=f"`{len(dict_queue[self.gid])}`"+INV_CHAR_PADDING)
        embed.add_field(name=queue_duration, value=f"`{'+' if not_all else ''}{convert_seconds(sum([vid['length'] for vid in videos_with_length]))}`")
        return embed


class PlaylistQueueMenu(discord.ui.View):
    def __init__(self, queue, num_pages, ctx, gid, playlist_title, creator):
        super().__init__(timeout=None)
        self.queue = queue
        self.num_pages = num_pages
        self.current_page = 1
        self.gid = gid
        self.ctx = ctx  # to check for perms
        self.playlist_title = playlist_title
        self.creator = creator

    @discord.ui.button(label="", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def button_prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id == interaction.user.id:
            if self.current_page > 1:
                self.current_page -= 1
            await self.update_message(interaction)
            return
        await interaction.response.defer()

    @discord.ui.button(label="", emoji="❌", style=discord.ButtonStyle.secondary)
    async def button_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id == interaction.user.id:
            await self.update_message(interaction, True)
            return
        await interaction.response.defer()

    @discord.ui.button(label="", emoji="➡️", style=discord.ButtonStyle.secondary)
    async def button_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id == interaction.user.id:
            if self.current_page < self.num_pages:
                self.current_page += 1
            await self.update_message(interaction)
            return
        await interaction.response.defer()

    async def update_message(self, interaction: discord.Interaction, cancelled=False):
        if cancelled:
            await interaction.message.delete()
            return
        embed = self.create_embed()
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    def create_embed(self):
        start_index = (self.current_page - 1) * QUEUE_VIDEOS_PER_PAGE
        end_index = start_index + QUEUE_VIDEOS_PER_PAGE
        with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
            self.queue[start_index:end_index] = list(executor.map(get_video_info, self.queue[start_index:end_index]))
        title_queue = [vid['title'] for vid in self.queue[start_index:end_index]]
        MAX_LENGTH = 70
        page_content = [
            f"{pos+1+QUEUE_VIDEOS_PER_PAGE*(self.current_page-1)}. {title[:(MAX_LENGTH-len(str(pos+1+QUEUE_VIDEOS_PER_PAGE*(self.current_page-1))))]}"+
            "..."*int(len(title) > (MAX_LENGTH-len(str(pos+1+QUEUE_VIDEOS_PER_PAGE*(self.current_page-1)))))
            for pos, title in enumerate(title_queue)
        ]  # cut titles length
        if any(isinstance(vid, str) for vid in self.queue):
            videos_with_length = filter(lambda vid: not isinstance(vid, str), self.queue)
            not_all = True
        else:
            videos_with_length = self.queue.copy()
            not_all = False
        embed = discord.Embed(
            title=playlist_title + self.playlist_title,
            description="\n".join(page_content),
            color=EMBED_COLOR
        )
        embed.add_field(name=queue_pages, value=f"`{self.current_page}/{self.num_pages}`"+INV_CHAR_PADDING)
        embed.add_field(name=queue_videos, value=f"`{len(self.queue)}`"+INV_CHAR_PADDING)
        embed.add_field(name=queue_duration, value=f"`{'+' if not_all else ''}{convert_seconds(sum([vid['length'] for vid in videos_with_length]))}`")
        embed.set_author(name=playlist_created_by.replace("%name", self.creator['name']), icon_url=self.creator['avatar'])
        return embed


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=find_font(category.capitalize(), FONT), description=CATEGORY_DESC[category.replace("\u2002", "_").replace(" ", "_")]) for category in COMMANDS_INFO.keys()]
        self.help_font = FONT
        super().__init__(placeholder=category_placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = find_font(self.values[0], FONT=self.help_font, inverse=True).lower().replace("\u2002", "_").replace(" ", "_")
        embed = discord.Embed(
            title=CATEGORY_DESC[category],
            color=EMBED_COLOR
        )
        category = category.replace("_", " ")
        for command, info in COMMANDS_INFO[category].items():
            command_info = COMMANDS_INFO[category][command]
            command = command.replace("_", r"\_").replace("*", r"\*")
            if 'aliases_show' in command_info:
                embed.add_field(name=f"{command} (`{', '.join(command_info['aliases_show'])}`)", value=info['description_short'], inline=False)
            else:
                embed.add_field(name=f"{command}", value=info['description_short'], inline=False)
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(HelpDropdown())


## BOT EVENTS ##
@bot.event
async def on_ready():
    print(f'{logged_in} {bot.user.name}')


@bot.event
async def on_message(message):
    try:
        if message.author == bot.user:
            return

        gid = message.guild.id
        file_path = f'options_{gid}.json'
        create_options_file(file_path)
        try:
            with open(file_path, 'r') as f:
                options = json.load(f)
        except:
            create_options_file(file_path, force=True)
            with open(file_path, 'r') as f:
                options = json.load(f)
        if not 'custom_prefixes' in options:
            options = write_options(options, str(gid), ['custom_prefixes'])
        temp_message = message.content
        succ = False
        for prefix in options['custom_prefixes']+['DEF_PREFIX']:
            if message.content.startswith(prefix):
                if message.content in EXCLUDED_CASES: return
                print(f'\033[92m>>> {command_from} {message.author}: {message.content[len(prefix):]}\033[0m')
                message.content = 'DEF_PREFIX' + message.content[len(prefix):]
                if message.author.id in user_cooldowns:
                    curr_time = time.time()
                    cooldown_time = user_cooldowns[message.author.id]
                    time_elapsed = curr_time - cooldown_time
                    if time_elapsed < REQUEST_LIMIT:
                        await message.channel.send(
                            wait_seconds.replace("%name", message.author.mention).replace("%time", str(round(
                                REQUEST_LIMIT - time_elapsed, 1))))
                        return
                user_cooldowns[message.author.id] = time.time()
                succ = True
                break
            else:
                temp_message = message.content[len(prefix):]
        if not succ: message.content = temp_message

        await bot.process_commands(message)
    except:
        traceback.print_exc()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        command_called = ctx.message.content.split(" ")[0].replace("DEF_PREFIX", "")
        if not any(command_called.startswith(prefix) for prefix in EXCLUDED_CASES):
            channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
            await channel_to_send.send(not_existing_command.replace("%command", command_called), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)


@bot.event
async def on_voice_state_update(member, before, after):
    global loop_mode, dict_current_song, disable_play, dict_queue
    if before.channel is not None:
        voice_channel = before.channel
        if bot.user in voice_channel.members:
            if len(voice_channel.members) <= 1:
                server = voice_channel.guild
                gid = str(server.id)
                voice_client = discord.utils.get(bot.voice_clients, guild=server)
                await voice_client.disconnect()

                file_path = f'options_{gid}.json'
                create_options_file(file_path)
                try:
                    with open(file_path, 'r') as f:
                        options = json.load(f)
                except:
                    create_options_file(file_path, force=True)
                    with open(file_path, 'r') as f:
                        options = json.load(f)
                if not 'restricted_to' in options:
                    options = write_options(options, str(gid), ['restricted_to'])

                channel_to_send = None
                for channel in server.text_channels:
                    if channel.permissions_for(server.me).send_messages:
                        channel_to_send = channel
                        break

                loop_mode[gid] = "off"
                dict_queue[gid] = []
                disable_play = False
                dict_current_song[gid] = 0
                try:
                    del song_start_times[gid]
                    del pause_start_times[gid]
                    del paused_durations[gid]
                except:
                    pass

                if not channel_to_send:
                    return
                if options['restricted_to'] != 'ALL_CHANNELS':
                    channel_to_send = discord.utils.get(server.channels, name=options['restricted_to'])
                await channel_to_send.send(random.choice(nobody_left_texts))



## BOT TASKS ##
@tasks.loop(seconds=1)
async def vote_skip():
    global vote_skip_dict, vote_skip_counter, message_id_dict, majority_dict, ctx_dict_skip
    if not ctx_dict_skip:
        vote_skip.stop()
        return
    temp_dict = ctx_dict_skip.copy()
    for gid in ctx_dict_skip:
        ctx = ctx_dict_skip[gid]
        try:
            message_id = message_id_dict[gid]
            majority = majority_dict[gid][0]
        except:
            continue
        message = discord.utils.get(bot.cached_messages, id=message_id)
        if not message:
            continue
        reactions = {reaction.emoji: -1 for reaction in message.reactions}
        for reaction in message.reactions:
            async for user in reaction.users():
                if user.id in majority_dict[gid][1]: reactions[reaction.emoji] += 1
        if reactions["✅"] >= majority:
            vote_skip_dict[gid], vote_skip_counter[gid] = 1, 0
            await message.delete()
            channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
            await channel_to_send.send(song_skipped, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            await skip(ctx)
            del temp_dict[gid]
            del message_id_dict[gid]
            del majority_dict[gid]
            vote_skip_dict[gid], vote_skip_counter[gid] = 1, 0
            continue
        if vote_skip_counter[gid] >= SKIP_TIMELIMIT - 1:
            del temp_dict[gid]
            del message_id_dict[gid]
            del majority_dict[gid]
            vote_skip_dict[gid], vote_skip_counter[gid] = -1, 0
            continue
        vote_skip_counter[gid] += 1
    ctx_dict_skip = temp_dict.copy()


## BOT COMMANDS ##
@bot.command(name='help', aliases=['h'])
async def help(ctx, *, command_name=None):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_help"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if command_name:
            command_name = command_name.lower().strip().replace(" ", "_")
            command, command_info = find_command_info(command_name)
            if command_info:
                command = command.replace("_", r"\_").replace("*", r"\*")
                embed = discord.Embed(
                    title=help_title.replace("%command", ": " + command),
                    color=EMBED_COLOR
                )
                embed.add_field(name=help_word_usage, value=command_info['usage'], inline=False)
                if 'aliases_show' in command_info:
                    embed.add_field(name=help_word_aliases, value=', '.join(command_info['aliases_show']).replace("_", r"\_").replace("*", r"\*"), inline=False)
                embed.add_field(name=help_word_desc, value=command_info['description'], inline=False)
                embed.add_field(name=help_word_perm, value=command_info['permission'].replace("_", r"\_").replace("*", r"\*"), inline=False)
                await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            else:
                await channel_to_send.send(not_existing_command.replace("%command", command_name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        else:
            file_path = f'options_{ctx.guild.id}.json'
            create_options_file(file_path)
            try:
                with open(file_path, 'r') as f:
                    options = json.load(f)
            except:
                create_options_file(file_path, force=True)
                with open(file_path, 'r') as f:
                    options = json.load(f)
            if not 'custom_prefixes' in options:
                options = write_options(options, str(ctx.guild.id), ['custom_prefixes'])
            embed = discord.Embed(
                title=help_title.replace("%command", ""),
                description=help_desc.replace("%prefix", ', '.join(['`{}`'.format(item) for item in options['custom_prefixes']])),
                color=EMBED_COLOR
            )
            await channel_to_send.send(embed=embed, view=HelpView(), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='perms', aliases=['prm'])
async def perms(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_perms"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        permissions = ctx.guild.me.guild_permissions
        true_permissions = {name: value for name, value in permissions if value}
        formatted_permissions = ', '.join([f'`{perm[0]}`' for perm in true_permissions.items()])
        embed = discord.Embed(
            title=bot_perms.replace("%botname", BOT_NAME).replace("%server", ctx.guild.name),
            description=formatted_permissions,
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed)
    except:
        traceback.print_exc()


@bot.command(name='add_perm', aliases=['add_perms'])
async def add_perm(ctx, name, perm):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_add_perms"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        file_path = f'user_perms_{ctx.guild.id}.json'
        create_perms_file(ctx, file_path)
        with open(file_path, 'r') as f:
            user_perms = json.load(f)

        server = ctx.guild
        perm = perm.lower()
        if perm == "use_parameter":
            await channel_to_send.send(parameter_perm_added_externally, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if name == "ALL" or name == "*":
            P = 1
            for member in server.members:
                user_perms[str(member.id)] = user_perms.setdefault(str(member.id),
                                                                   ADMIN_PERMS if member.guild_permissions.administrator else DEFAULT_USER_PERMS)
                if perm in AVAILABLE_PERMS:
                    if perm not in user_perms[str(member.id)]: user_perms[str(member.id)].append(perm)
                elif perm in ["ALL", "*"]:
                    user_perms[str(member.id)] = AVAILABLE_PERMS.copy()
                    P = 2
                else:
                    await channel_to_send.send(invalid_perm.replace("%perm", perm))
                    P = 0
                    break
            if P == 1: await channel_to_send.send(perm_added_everyone.replace("%perm", perm))
            if P == 2: await channel_to_send.send(all_perms_everyone)
        else:
            P = False
            for member in server.members:
                if member.name in [name, name.lower()]:
                    P = True
                    try:
                        user_perms[str(member.id)]
                    except:
                        if member.guild_permissions.administrator:
                            user_perms[str(member.id)] = ADMIN_PERMS
                        else:
                            user_perms[str(member.id)] = DEFAULT_USER_PERMS
                    if perm in AVAILABLE_PERMS:
                        if perm in user_perms[str(member.id)]:
                            await channel_to_send.send(perm_already_added.replace("%name", member.name).replace("%perm", perm))
                            break
                        user_perms[str(member.id)].append(perm)
                        await channel_to_send.send(perm_added.replace("%perm", perm).replace("%name", member.name))
                    elif perm in ["ALL", "*"]:
                        user_perms[str(member.id)] = AVAILABLE_PERMS.copy()
                        await channel_to_send.send(all_perms_added.replace("%name", member.name))
                    else:
                        await channel_to_send.send(invalid_perm.replace("%perm", perm))
                        break
            if not P:
                await channel_to_send.send(couldnt_find_user.replace("%name", name))

        with open(file_path, 'w') as f:
            json.dump(user_perms, f)
    except:
        traceback.print_exc()


@bot.command(name='del_perm', aliases=['del_perms'])
async def del_perm(ctx, name, perm):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_del_perms"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        file_path = f'user_perms_{ctx.guild.id}.json'
        create_perms_file(ctx, file_path)
        with open(file_path, 'r') as f:
            user_perms = json.load(f)

        server = ctx.guild
        perm = perm.lower()
        if name == "ALL" or name == "*":
            P = True
            for member in server.members:
                user_perms[str(member.id)] = user_perms.setdefault(str(member.id),
                                                                   ADMIN_PERMS if member.guild_permissions.administrator else DEFAULT_USER_PERMS)
                if perm in AVAILABLE_PERMS:
                    if perm in user_perms[str(member.id)]: user_perms[str(member.id)].remove(perm)
                else:
                    await channel_to_send.send(invalid_perm.replace("%perm", perm))
                    P = False
                    break
            if P: await channel_to_send.send(perm_del_everyone.replace("%perm", perm))
        else:
            P = False
            for member in server.members:
                if member.name in [name, name.lower()]:
                    P = True
                    user_perms[str(member.id)] = user_perms.setdefault(str(member.id),
                                                                       ADMIN_PERMS if member.guild_permissions.administrator else DEFAULT_USER_PERMS)
                    if perm in AVAILABLE_PERMS:
                        if perm not in user_perms[str(member.id)]:
                            await channel_to_send.send(perm_not_added.replace("%name", member.name).replace("%perm", perm))
                            break
                        user_perms[str(member.id)].remove(perm)
                        await channel_to_send.send(perm_removed.replace("%perm", perm).replace("%name", member.name))
                    else:
                        await channel_to_send.send(invalid_perm.replace("%perm", perm))
                        break
            if not P:
                await channel_to_send.send(couldnt_find_user.replace("%name", name))

        with open(file_path, 'w') as f:
            json.dump(user_perms, f)
    except:
        traceback.print_exc()


@bot.command(name='available_perms', aliases=[])
async def available_perms(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_available_perms"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed_aval = discord.Embed(
            title=default_perms_title,
            description=f"{', '.join(['`{}`'.format(item) for item in DEFAULT_USER_PERMS])}",
            color=EMBED_COLOR
        )
        embed_def = discord.Embed(
            title=available_perms_title,
            description=f"{', '.join(['`{}`'.format(item) for item in AVAILABLE_PERMS])}",
            color=EMBED_COLOR
        )
        await channel_to_send.send(embeds=[embed_aval, embed_def], reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='fastplay', aliases=['fp'])
async def fastplay(ctx, *, url):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_fastplay"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        await play(ctx, url=url, search=False)
    except:
        traceback.print_exc()


@bot.command(name='rewind', aliases=['rw', 'r', 'back'])
async def rewind(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_rewind"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global loop_mode, go_back
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, [])
        queue = dict_queue[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client is None or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] == 'one': loop_mode[gid] = 'off'
        go_back = True
        if voice_client.is_paused(): voice_client.resume()
        if voice_client.is_playing(): voice_client.stop()
        else: await play_next(ctx, rewinded=1)
    except:
        traceback.print_exc()


@bot.command(name='join', aliases=['connect'])
async def join(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_join"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return None
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        channel = ctx.author.voice.channel
        if voice_client is not None:
            if channel != voice_client.channel:
                await channel_to_send.send(already_on_another_vc, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            elif voice_client.is_connected():
                await channel_to_send.send(random.choice(already_connected_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        await channel.connect()
        change_active(ctx, mode='a')
        txt = random.choice(entering_texts) + channel.name + "."
        await channel_to_send.send(txt, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='leave', aliases=['l', 'dis', 'disconnect', 'd'])
async def leave(ctx, *, tmp='', ignore=False, disconnect=True, ended_queue=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        global loop_mode, dict_current_song, disable_play, dict_queue
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not ignore:
            if not check_perms(ctx, "use_leave"):
                await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if not ctx.author.voice:
                await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if voice_client is None:
                await channel_to_send.send(random.choice(not_connected_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if ctx.author.voice.channel != voice_client.channel:
                await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        gid = str(ctx.guild.id)
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if ended_queue:
            await channel_to_send.send(song_queue_ended, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        if disconnect:
            loop_mode[gid] = "off"
            try:
                if voice_client is not None and voice_client.is_connected():
                    await voice_client.disconnect()
            except:
                traceback.print_exc()
                pass
            change_active(ctx, mode='d')
            dict_queue[gid] = []
            disable_play = False
            dict_current_song[gid] = 0
            try:
                del song_start_times[gid]
                del pause_start_times[gid]
                del paused_durations[gid]
            except:
                pass
    except:
        traceback.print_exc()


@bot.command(name='nowplaying', aliases=['info', 'np', 'playing'])
async def info(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_info"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID:
            await channel_to_send.send(random.choice(no_api_key_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is not None and voice_client.is_playing() or voice_client.is_paused():
            gid = str(ctx.guild.id)
            dict_queue.setdefault(gid, list())
            dict_current_song.setdefault(gid, 0)
            queue = dict_queue[gid]
            current_song = dict_current_song[gid]
            vid = queue[current_song]
            current_time = get_current_time(gid)
            if isinstance(vid, str):
                dict_queue[gid][current_song] = vid = info_from_url(vid)
            titulo, duracion, actual = vid['title'], convert_seconds(int(vid['length'])), convert_seconds(current_time)
            vid_channel = vid['channel'] if vid['channel'] else '???'
            if SPOTIFY_SECRET and SPOTIFY_ID: artista = utilidades.get_spotify_artist(titulo+vid_channel*(vid_channel != "???"), is_song=True)
            else: artista = vid_channel
            if not artista or vid['type'] == 'raw_audio': artista = vid['channel'] if vid['channel'] else '???'
            embed = discord.Embed(
                title=song_info_title,
                description="",
                color=EMBED_COLOR,
                url=vid['url']
            )
            embed.add_field(name=word_title, value=titulo)
            embed.add_field(name=word_artist, value=artista)
            embed.add_field(name=word_duration, value=f"`{str(duracion)}`")
            embed.add_field(name="", value=utilidades.get_bar(int(vid['length']), current_time), inline=False)
            embed.set_footer(text=f"{vid_channel}", icon_url=vid['channel_image'])
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        else:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='ping')
async def ping(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_ping"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        await channel_to_send.send(f"Pong! {round(bot.latency * 1000)}ms", reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='options', aliases=['cfg', 'config', 'opt'])
async def options(ctx, option="", *, query="", ignore=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not ignore:
            if not check_perms(ctx, "use_options"):
                await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            embed = discord.Embed(
                title="",
                description="",
                color=EMBED_COLOR
            )

        file_path = f'options_{ctx.guild.id}.json'
        create_options_file(file_path)

        try:
            with open(file_path, 'r') as f:
                options = json.load(f)
        except:
            create_options_file(file_path, force=True)
            with open(file_path, 'r') as f:
                options = json.load(f)
        if not all(key in options for key in DEFAULT_OPTIONS):
            options = write_options(options, str(ctx.guild.id), DEFAULT_OPTIONS.keys())
        search_limit, recomm_limit, custom_prefixes, restricted_to = options['search_limit'], options['recomm_limit'],\
                                                                  options['custom_prefixes'], options['restricted_to']
        original = search_limit, recomm_limit, custom_prefixes
        if not ignore:
            if not option:
                embed.title = config_title
                embed.description = config_desc.replace("%search_limit", str(search_limit))\
                    .replace("%recomm_limit", str(recomm_limit)).replace("%custom_prefixes", ' '.join(custom_prefixes))\
                    .replace("%restricted_to", str(restricted_to))
                await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            elif option in ["restart", "default"]:
                query = 10
            elif query == "":
                await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            try:
                query = min(max(float(query), 0), 25)
            except:
                await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if option == "search_limit":
                options['search_limit'], p = int(query), 0
            elif option == "recomm_limit":
                options['recomm_limit'], p = int(query), 1
            elif option in ["restart", "default"]:
                options['search_limit'], options['recomm_limit'], options[
                    'custom_prefixes'] = DEFAULT_SEARCH_LIMIT, DEFAULT_RECOMMENDATION_LIMIT, DEFAULT_PREFIXES
            else:
                await channel_to_send.send(random.choice(prefix_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        elif option == "restricted_to":
            options['restricted_to'] = query
        else:
            return
        with open(file_path, 'w') as f:
            json.dump(options, f)
        if not ignore:
            embed.title = f"{config_title}: `{option}`"
            if option in ["restart", "default", "reset"]:
                embed.description = config_default.replace("%sl", str(original[0])).replace("%rl",
                                                                                            str(original[1])).replace(
                    "%cust_p", ' '.join(original[2])) \
                    .replace("%def_sl", str(DEFAULT_SEARCH_LIMIT)).replace("%def_rl",
                                                                           str(DEFAULT_RECOMMENDATION_LIMIT)).replace(
                    "%def_cust_p", ' '.join(DEFAULT_PREFIXES))
            else:
                embed.description = config_changed.replace("%option", option).replace("%original",
                                                                                      str(original[p])).replace("%newvalue",
                                                                                                                str(options[
                                                                                                                        option]))
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='search', aliases=['find'])
async def search(ctx, tipo, *, query=""):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_search"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not tipo:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not query: query = tipo
        embed = discord.Embed(
            title="",
            description="",
            color=EMBED_COLOR
        )
        file_path = f'options_{ctx.guild.id}.json'
        create_options_file(file_path)
        try:
            with open(file_path, 'r') as f:
                options = json.load(f)
        except:
            create_options_file(file_path, force=True)
            with open(file_path, 'r') as f:
                options = json.load(f)
        if not 'search_limit' in options:
            options = write_options(options, str(ctx.guild.id), ['search_limit'])
        if tipo.lower() in ['youtube', 'yt', 'yotube'] or (tipo not in ['spotify', 'sp', 'spotipy', 'spoti', 'spoty']
                                                           and tipo not in ['youtube', 'yt', 'yotube']):
            for i in range(5):
                results = shortened_youtube_search(query, max_results=options['search_limit'])
                if results: break
            if not results:
                await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            embed.set_thumbnail(url=results[0]['thumbnail_url'])
            for vid in results:
                texto = f"➤ [{vid['title']}]({vid['url']})\n"
                embed.add_field(name="", value=texto, inline=False)
            embed.title = youtube_search_title
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        elif tipo.lower() in ['spotify', 'sp', 'spotipy', 'spoti', 'spoty']:
            if not SPOTIFY_SECRET or not SPOTIFY_ID:
                await channel_to_send.send(random.choice(no_api_key_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            results = utilidades.spotify_search(query, lim=options['search_limit'])
            if not results:
                await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            embed.set_thumbnail(url=results[0]['image_url'])
            for result in results:
                name, artist, url = result['name'], result['artist'], result['url']
                texto = spotify_search_desc.replace("%name", name).replace("%url", url).replace("%artist", artist)
                embed.add_field(name="", value=texto, inline=False)
            embed.title = spotify_search_title
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='genre', aliases=['genres', 'recomm', 'recommendation', 'recommendations'])
async def genre(ctx, *, query=""):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_genre"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID:
            await channel_to_send.send(random.choice(no_api_key_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed = discord.Embed(
            title="",
            description="",
            color=EMBED_COLOR
        )
        file_path = f'options_{ctx.guild.id}.json'
        create_options_file(file_path)
        try:
            with open(file_path, 'r') as f:
                options = json.load(f)
        except:
            create_options_file(file_path, force=True)
            with open(file_path, 'r') as f:
                options = json.load(f)
        if not 'recomm_limit' in options:
            options = write_options(options, str(ctx.guild.id), ['recomm_limit'])
        results = utilidades.genre_spotify_search(query, lim=options['recomm_limit'])
        if not query or results[1]:
            texto, i = "", 0
            genrelist = results[0]
            for genre in genrelist:
                genre = genre.replace("-", " ").title()
                texto += f"➤ *{genre}*" + "‎ " * (15 - len(genre))
                i += 1
                if i % 5 == 0:
                    texto += "\n"
                    embed.add_field(name="", value=texto, inline=False)
                    texto, i = "", 0
            embed.title = available_genres
        else:
            if not results[0]:
                await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            songs = results[0]
            for result in songs:
                name, artist, url = result['name'], result['artist'], result['url']
                texto = spotify_search_desc.replace("%name", name).replace("%url", url).replace("%artist", artist)
                embed.add_field(name="", value=texto, inline=False)
            embed.title = genre_search_title.replace("%genre", results[2].replace('-', ' ').title())
            embed.set_thumbnail(url=result['image_url'])
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='play', aliases=['p'])
async def play(ctx, *, url="", append=True, gif=False, search=True, force_play=False, silent=False, attachment=True):
    global dict_current_song, disable_play, vote_skip_dict
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not check_perms(ctx, "use_play"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)
        if disable_play: return
        if not ctx.author.voice and attachment:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not url and not ctx.message.attachments:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if attachment:
            voice_channel = ctx.author.voice.channel
            if not voice_channel.permissions_for(ctx.me).connect:
                await channel_to_send.send(random.choice(private_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        else:
            try:
                voice_channel = voice_client.channel
            except:
                return
        if voice_client:
            if voice_client.channel != voice_channel:
                await channel_to_send.send(already_on_another_vc, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        try:
            await voice_channel.connect()
        except:
            pass
        if ctx.message.attachments and attachment:
            for attachment in ctx.message.attachments:
                await play(ctx, url=f"{attachment.url} -opt force", search=False, attachment=False)
        if not url: return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        change_active(ctx, mode='a')

        all_chosen = False
        if isinstance(url, dict):
            video_select = url.copy()
        else:
            separate_commands = str(url).split('-opt')
            url = separate_commands[0].strip().strip("\n")
            if len(separate_commands) > 1:
                command = separate_commands[1].strip().strip("\n").lower()
                if command in ['1', 'true', 'si', 'y', 'yes', 'gif']: gif = True
                if command in ['force', 'forceplay', 'force_play', 'play']: force_play = True
            if not is_url(url):
                search_message = await channel_to_send.send(searching_text)
                for i in range(5): # retry the search max 5 times
                    results = shortened_youtube_search(url, max_results=MAX_SEARCH_SELECT if search else 1)
                    if results: break
                    print(f"failed search {i+1}")
                if not results:
                    await search_message.delete()
                    await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                    return
                num_pages = -(-len(results)//5) # ceil function without math module lol
                current_page = 1
                if search:
                    choice_embed = discord.Embed(
                        title=choose_song_title.replace("%page", f"1/{num_pages}"),
                        description="",
                        color=EMBED_COLOR
                    )
                    choice_embed.set_footer(text=timeout_footer.replace("%time", str(TIMELIMIT)))
                    emojis_reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '❌']
                    emoji_to_number = {
                        '1️⃣': 1,
                        '2️⃣': 2,
                        '3️⃣': 3,
                        '4️⃣': 4,
                        '5️⃣': 5,
                        '❌': None
                    }
                    choice_embed.set_thumbnail(url=results[0]['thumbnail_url'])
                    for i in range(len(results[:5])):
                        texto = f"{emojis_reactions[i]} [{results[i]['title']}]({results[i]['url']}) `{convert_seconds(results[i]['length'])}`\n"
                        choice_embed.add_field(name="", value=texto, inline=False)
                    await search_message.delete()
                    disable_play = True
                    if USE_BUTTONS:
                        button_choice[gid] = -1
                        menu = SongChooseMenu(gid)
                        message = await channel_to_send.send(embed=choice_embed, view=menu, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                        try:
                            def check(interaction: discord.interactions.Interaction):
                                return interaction.user.id == ctx.author.id
                            temp_TIMELIMIT = TIMELIMIT
                            for _ in range(60):
                                start_time = time.time()
                                intrc = await bot.wait_for('interaction', timeout=temp_TIMELIMIT, check=check)
                                end_time = time.time() - start_time
                                temp_TIMELIMIT -= end_time
                                if intrc.data['custom_id'] not in {'6', '8'}: break
                                if intrc.data['custom_id'] == '8' and current_page < num_pages:  # next page
                                    current_page += 1
                                elif intrc.data['custom_id'] == '6' and current_page > 1:  # prev page
                                    current_page -= 1
                                await intrc.response.defer()
                                new_results_embed = discord.Embed(
                                    title=choose_song_title.replace("%page", f"{current_page}/{num_pages}"),
                                    description="",
                                    color=EMBED_COLOR
                                )
                                new_results_embed.set_footer(text=timeout_footer.replace("%time", str(TIMELIMIT)))
                                val = 5 * (current_page - 1)
                                left = len(results[val:val+5])
                                new_results_embed.set_thumbnail(url=results[val]['thumbnail_url'])
                                for i in range(val, val+left):
                                    texto = f"{emojis_reactions[i-val]} [{results[i]['title']}]({results[i]['url']}) `{convert_seconds(results[i]['length'])}`\n"
                                    new_results_embed.add_field(name="", value=texto, inline=False)
                                await message.edit(embed=new_results_embed)
                        except asyncio.TimeoutError:
                            await channel_to_send.send(random.choice(song_not_chosen_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                            await message.delete()
                            disable_play = False
                            return
                        except:
                            traceback.print_exc()
                            return
                        disable_play = False
                        await message.delete()
                        if button_choice[gid] < 0:
                            await channel_to_send.send(random.choice(cancel_selection_texts))
                            return
                        if button_choice[gid] == 5:
                            button_choice[gid] = random.randint(0, len(results[(5 * (current_page - 1)):(5 * current_page)]))
                        if button_choice[gid] == 9:
                            chosen_results = results[(5 * (current_page - 1)):(5 * current_page)].copy()
                            links = [info_from_url(chosen_results[0]['url'])] + [vid['url'] for vid in chosen_results[1:]]
                            all_chosen = True
                            await channel_to_send.send(all_selected.replace("%page", str(current_page)), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                        else:
                            chosen = min(len(results[5*(current_page-1):5*current_page])+5*(current_page-1)-1, button_choice[gid]+5*(current_page-1))
                            video_select = info_from_url(results[chosen]['url'])
                            if voice_client:
                                await channel_to_send.send(song_selected.replace("%title", video_select['title']), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                            else:
                                return
                    else:
                        points = ":" if ":" in choose_song_title else ""
                        choice_embed.title = choose_song_title[:choose_song_title.find(" (")]+points
                        emoji_choice = await choice(ctx, choice_embed, emojis_reactions)
                        disable_play = False
                        if not emoji_choice or emoji_choice == '❌':
                            await channel_to_send.send(random.choice(cancel_selection_texts))
                            return
                        video_select = results[emoji_to_number.get(emoji_choice, None) - 1]
                        if voice_client:
                            await channel_to_send.send(song_selected.replace("%title", video_select['title']), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                        else:
                            return
                else:
                    video_select = info_from_url(results[0]['url'])
                    await search_message.delete()
            else:
                video_select = {
                    'obj': None, 'title': None, 'channel': None, 'length': None, 'id': None, 'thumbnail_url': None,
                    'url': url, 'type': None, 'stream_url': None, 'views': None, 'channel_url': None, 'channel_image': None,
                    'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'channels': 2, 'bass': 0.0, 'high': 0.0}
                    # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
                }
        end = False

        if not all_chosen:
            vtype, vid_id, full_url = check_link_type(video_select['url'])
            video_select['url'] = full_url  # for shortened urls
            not_loaded_list = []
            failed_check = False

            if vtype == 'unknown':
                try:
                    if not isinstance(url, dict) and not video_select['stream_url']:
                        links = [info_from_url(video_select['url'])]
                        if not links[0]['stream_url']:
                            not_loaded_list.append(f"[{links[0]['title']}]({links[0]['url']})")
                            end = True
                    else:
                        links = [video_select]
                except:
                    if not force_play:
                        await channel_to_send.send(random.choice(invalid_link_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                        return
                    else:
                        links = [url]
                        vtype = 'raw_audio'
            elif vtype == 'playlist':
                try:
                    playlist = Playlist(video_select['url'])
                    links = list(playlist.video_urls)
                except:
                    # check if link type is not compatible
                    try:
                        playlist = Playlist(f"https://www.youtube.com/playlist?list={vid_id}")
                        links = list(playlist.video_urls)
                    except:
                        # assume playlist doesnt exist and its a video only
                        vtype = 'video'
                        failed_check = True
                if not failed_check:
                    video_count = len(links)
                    links = links[:PLAYLIST_MAX_LIMIT]
                    total_duration, total_videos, fetched_videos = get_playlist_duration(playlist.playlist_url, links, len(links))
                    if total_videos != fetched_videos:
                        await channel_to_send.send(playlist_videos_unavailable.replace("%total", str(total_videos)).replace("%unavailable", str(total_videos-fetched_videos-max(0, video_count-PLAYLIST_MAX_LIMIT))))
                    if video_count > PLAYLIST_MAX_LIMIT:
                        await channel_to_send.send(playlist_max_reached.replace("%pl_length", str(video_count)).replace("%over", str(abs(
                            PLAYLIST_MAX_LIMIT - video_count))).replace("%discarded", str(abs(PLAYLIST_MAX_LIMIT - video_count))))
                    links[0] = info_from_url(links[0])
                    embed_playlist = discord.Embed(
                        title=playlist_added_title,
                        description=playlist_added_desc.replace("%name", ctx.author.global_name)
                            .replace("%title", str(playlist.title)).replace("%ch_name", voice_channel.name.replace("*", r"\*"))
                            .replace("%pl_length", str(len(links))),
                        color=EMBED_COLOR
                    )
                    embed_playlist.add_field(name=playlist_link, value=playlist.playlist_url, inline=False)
                    embed_playlist.add_field(name=word_title, value=f"*{playlist.title}*"+INV_CHAR_PADDING)
                    embed_playlist.add_field(name=word_duration, value=f"`{convert_seconds(total_duration)}`"+2*INV_CHAR_PADDING)
                    embed_playlist.add_field(name=word_views, value=f"`{format_views(playlist.views)}`")
            elif vtype == 'sp_track':
                track = sp.track(vid_id)
                links = [search_youtube(f"+{track['name']}, {' '.join([artist['name'] for artist in track['artists']])} audio", max_results=1)[0]]
            elif vtype == 'sp_album':
                def fetch_video_data(track):
                    videos = Search(f"+{track['name']}, {' '.join([artist['name'] for artist in track['artists']])} audio").results
                    video = videos[0]
                    try:
                        streaming_data = video.streaming_data
                        stream_url = get_stream_url(streaming_data['adaptiveFormats'],
                                                    itags=ITAGS_LIST)  # get best stream url if possible
                        if not stream_url:
                            stream_url = get_stream_url(streaming_data['formats'],
                                                        itags=ITAGS_LIST)  # get best stream url if possible
                            if not stream_url: return
                    except:
                        not_loaded_list.append(f"[{video.title}]({video.watch_url})")
                        return
                    return {
                        'obj': video, 'title': video.title, 'views': video.views, 'channel': video.author,
                        'url': video.watch_url, 'stream_url': stream_url, 'thumbnail_url': video.thumbnail_url,
                        'channel_url': video.channel_url, 'length': int(video.length), 'id': video.video_id, 'channel_image': get_channel_picture(video.channel_url),
                        'type': 'video', 'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'channels': 2, 'bass': 0.0, 'high': 0.0}
                                        # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
                    }
                album = sp.album(vid_id)
                tracks = album['tracks']['items']
                for _ in range(SPOTIFY_LIMIT // 100 + 1):
                    if not album['tracks']['next']: break
                    album['tracks'] = sp.next(album['tracks'])
                    tracks.extend(album['tracks']['items'])
                if len(tracks) > SPOTIFY_LIMIT:
                    await channel_to_send.send(playlist_max_reached.replace("%pl_length", str(len(tracks))).replace("%over", str(abs(
                        SPOTIFY_LIMIT - len(tracks)))).replace("%discarded",
                                                                   str(abs(SPOTIFY_LIMIT - len(tracks)))))
                    tracks = tracks[:SPOTIFY_LIMIT]
                with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
                    links = list(filter(None, executor.map(fetch_video_data, tracks)))
            elif vtype == 'sp_playlist':
                def fetch_video_data(track):
                    track = track['track']
                    videos = Search(
                        f"+{track['name']}, {' '.join([artist['name'] for artist in track['artists']])} audio").results
                    video = videos[0]
                    try:
                        streaming_data = video.streaming_data
                        stream_url = get_stream_url(streaming_data['adaptiveFormats'],
                                                    itags=ITAGS_LIST)  # get best stream url if possible
                        if not stream_url:
                            stream_url = get_stream_url(streaming_data['formats'],
                                                        itags=ITAGS_LIST)  # get best stream url if possible
                            if not stream_url: return
                    except:
                        not_loaded_list.append(f"[{video.title}]({video.watch_url})")
                        return
                    return {
                        'obj': video, 'title': video.title, 'views': video.views, 'channel': video.author,
                        'url': video.watch_url, 'stream_url': stream_url, 'thumbnail_url': video.thumbnail_url,
                        'channel_url': video.channel_url, 'length': int(video.length), 'id': video.video_id, 'channel_image': get_channel_picture(video.channel_url),
                        'type': 'video', 'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'channels': 2, 'bass': 0.0, 'high': 0.0}
                                        # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
                    }
                playlist = sp.playlist(vid_id)
                tracks = playlist['tracks']['items']
                for _ in range(SPOTIFY_LIMIT // 100 + 1):
                    if not playlist['tracks']['next']: break
                    playlist['tracks'] = sp.next(playlist['tracks'])
                    tracks.extend(playlist['tracks']['items'])
                if len(tracks) > SPOTIFY_LIMIT:
                    await channel_to_send.send(playlist_max_reached.replace("%pl_length", str(len(tracks))).replace("%over", str(abs(
                        SPOTIFY_LIMIT - len(tracks)))).replace("%discarded", str(abs(SPOTIFY_LIMIT - len(tracks)))))
                    tracks = tracks[:SPOTIFY_LIMIT]
                with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
                    links = list(filter(None, executor.map(fetch_video_data, tracks)))
            elif vtype == 'raw_audio':
                if isinstance(url, dict):
                    links = [url]
                else:
                    links = [info_from_url(video_select['url'])]
            if vtype in {'video', 'live'}:
                if not isinstance(url, dict) and not video_select['stream_url']:
                    links = [info_from_url(video_select['url'])]
                    if not links[0]['stream_url']:
                        not_loaded_list.append(f"[{links[0]['title']}]({links[0]['url']})")
                        end = True
                else:
                    links = [video_select]
            for video in not_loaded_list:
                await channel_to_send.send(couldnt_load_song.replace("%title", video), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            if end: return
        else:
            vtype = 'video'

        try: vid = links[0].copy()
        except: vid = links[0]
        if vid['length'] > MAX_VIDEO_LENGTH:
            await channel_to_send.send(video_max_duration.replace("%video_limit", str(convert_seconds(MAX_VIDEO_LENGTH))),
                           reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            await skip(ctx)
            return
        titulo, duracion = vid['title'], convert_seconds(int(vid['length']))
        if vid['type'] == 'live': duracion = 'LIVE'
        vid['url'] = url if isinstance(url, str) and is_url(url) else vid['url']

        embed = discord.Embed(
            title="",
            description=song_chosen_desc.replace("%name", ctx.author.global_name).replace("%title", titulo).replace(
                "%ch_name", voice_channel.name.replace("*", r"\*")).replace("%url", vid['url']),
            color=EMBED_COLOR
        )
        embed2 = discord.Embed(
            title="",
            description=added_queue_desc.replace("%name", ctx.author.global_name).replace("%title", titulo).replace("%url", vid['url']),
            color=EMBED_COLOR
        )
        embed.set_author(name=song_chosen_title, icon_url=ctx.author.avatar)
        embed.add_field(name=word_title, value=f"*{titulo}*"+INV_CHAR_PADDING)
        embed.add_field(name=word_duration, value=f"`{duracion}`"+2*INV_CHAR_PADDING)
        embed.add_field(name=word_views, value=f"`{format_views(vid['views'])}`")
        embed.set_footer(text=f"{vid['channel']}", icon_url=vid['channel_image'])

        embed2.set_author(name=added_queue_title, icon_url=ctx.author.avatar)
        embed2.add_field(name=word_title, value=f"*{titulo}*"+INV_CHAR_PADDING)
        embed2.add_field(name=word_duration, value=f"`{duracion}`"+2*INV_CHAR_PADDING)
        embed2.add_field(name=word_views, value=f"`{format_views(vid['views'])}`")
        embed2.set_footer(text=f"{vid['channel']}", icon_url=vid['channel_image'])

        if embed.__len__() > 1024 or embed2.__len__() > 1024:
            silent = True
            await channel_to_send.send(embed_too_large, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        img = None
        if gif and TENOR_API_KEY: img = search_gif(titulo, TENOR_API_KEY)
        if not img: img = vid['thumbnail_url']
        if gif:
            embed.set_image(url=img)
            embed2.set_image(url=img)
        else:
            embed.set_thumbnail(url=img)
            embed2.set_thumbnail(url=img)

        if not vid['stream_url']:
            await channel_to_send.send(content=random.choice(rip_audio_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return

        if append:
            dict_queue[gid] = dict_queue.setdefault(gid, list())
            dict_current_song[gid] = dict_current_song.setdefault(gid, 0)
            for video in links:
                dict_queue[gid].append(video)

        # LVL HANDLE
        await update_level_info(ctx, ctx.author.id, LVL_PLAY_ADD)
        vote_skip_dict[gid] = -1

        if vtype == 'playlist':
            await channel_to_send.send(embed=embed_playlist, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        if voice_client is not None and voice_client.is_playing() and not silent:
            await channel_to_send.send(embed=embed2, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        else:
            song_start_times[gid] = datetime.datetime.now()
            paused_durations[gid] = datetime.timedelta()
            pause_start_times[gid] = None
            if not silent: await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)

        if voice_client and not voice_client.is_paused():
            try:
                if not voice_client.is_playing():
                    updated_options = FFMPEG_OPTIONS.copy()
                    if isinstance(url, dict):  # means song was already loaded, aka could have been changed in volume, pitch, etc
                        updated_options['options'] += get_updated_options(vid, get_current_time(gid), get_options_only=True)
                    stream_url = vid['stream_url'] if isinstance(vid, dict) else url
                    voice_client.play(discord.FFmpegPCMAudio(stream_url, **updated_options), after=lambda e: on_song_end(ctx, e))
                    voice_client.is_playing()


            except Exception as e:
                print(e)
                pass
    except:
        traceback.print_exc()


@bot.command(name='level', aliases=['lvl'])
async def level(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_level"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        id = ctx.author.id
        level_file_path = f'level_data_{ctx.guild.id}.json'
        if not os.path.exists(level_file_path):
            await restart_levels(ctx)
        with open(level_file_path, 'r') as f:
            level_data = json.load(f)
        for data in level_data:
            if id == data['id']:
                lvl, xp, next_xp = data['lvl'], data['xp'], data['next_xp']
        embed = discord.Embed(
            title=level_title,
            description=level_desc.replace("%name", ctx.author.global_name).replace("%level", str(lvl)).replace("%xp",
                                                                                                                str(xp)).replace(
                "%next_xp", str(next_xp)),
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='restart_levels', aliases=['rl'])
async def restart_levels(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        level_file_path = f'level_data_{ctx.guild.id}.json'
        if not os.path.exists(level_file_path):
            pass
        elif not check_perms(ctx, "use_restart_levels"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        server = ctx.guild
        datos = list()
        for member in server.members:
            username, id, lvl, xp, next_xp = member.name, member.id, 1, 0, 25
            datos.append({
                'name': username,
                'id': id,
                'lvl': lvl,
                'xp': xp,
                'next_xp': next_xp
            })
        with open(f'level_data_{server.id}.json', 'w') as f:
            json.dump(datos, f)
    except:
        traceback.print_exc()


@bot.command(name="remove", aliases=['rm'])
async def remove(ctx, index):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_remove"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is None or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        try:
            index = int(index) - 1
            if not 0 <= index < len(queue): raise Exception
        except:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[index]
        if isinstance(vid, str):
            vid = info_from_url(vid)
        queue.pop(index)
        await channel_to_send.send(removed_from_queue.replace("%title", vid['title']), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        if index == current_song:
            dict_current_song[gid] = current_song - 2 if current_song > 1 else -1
            del song_start_times[gid]
            del pause_start_times[gid]
            del paused_durations[gid]
            await skip(ctx)
        elif index < current_song:
            dict_current_song[gid] = current_song - 1
    except Exception as e:
        traceback.print_exc()


@bot.command(name='backward', aliases=['backwards', 'bw'])
async def backward(ctx, time):
    try:
        try:
            time = -1*int(time)
            await forward(ctx, time)
        except:
            await forward(ctx, -1*int(convert_formated(time)))
    except:
        traceback.print_exc()


@bot.command(name='forward', aliases=['fw', 'forwards', 'ff'])
async def forward(ctx, time):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_forward"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global seek_called, dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if not voice_client or not queue or not voice_client.is_playing() and not voice_client.is_paused():
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        if vid['type'] == 'live':
            await channel_to_send.send(cannot_change_time_live.replace("%command", "forward/backward"), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if str(time).replace('-', '').replace('+', '').isnumeric():
            time = int(time)
        else:
            symbol = ''
            temptime = time
            if '+' in time: temptime = time.replace('+', '')
            if '-' in time: temptime, symbol = time.replace('-', ''), '-'
            time = int(symbol + str(convert_formated(temptime)))
        if time > 0: song_start_times[gid] -= datetime.timedelta(seconds=time)
        else: song_start_times[gid] += datetime.timedelta(seconds=-1*time)
        current_time = get_current_time(gid)
        if current_time > vid['length'] and not vid['type'] == 'raw_audio':
            await skip(ctx)
            return
        if current_time < 0:
            current_time = 0
            song_start_times[gid] = datetime.datetime.now()
            paused_durations[gid] = datetime.timedelta()
            pause_start_times[gid] = None
        seek_called = True
        if voice_client.is_paused(): voice_client.resume()
        voice_client.stop()
        updated_options = get_updated_options(vid, current_time)
        voice_client.play(
                discord.FFmpegPCMAudio(vid['stream_url'], **updated_options),
            after=lambda e: on_song_end(ctx, e))

        duracion, actual = convert_seconds(int(vid['length'])), convert_seconds(current_time)
        bar = utilidades.get_bar(int(vid['length']), current_time)
        tmp_mode = fast_forwarding.replace("%emoji", ":fast_forward:") if time >= 0 else rewinding.replace("%emoji", ":arrow_backward:")
        modetype = INV_CHAR_PADDING + tmp_mode
        embed = discord.Embed(
            title=forward_title.replace("%modetype", modetype).replace("%sec", str(convert_seconds(abs(time)))).replace(
                "%time", str(actual)),
            description=f"{bar}",
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()
        await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)


@bot.command(name='seek', aliases=['sk'])
async def seek(ctx, time):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_seek"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global seek_called, dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue or not voice_client.is_playing() and not voice_client.is_paused():
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        if vid['type'] == 'live':
            await channel_to_send.send(cannot_change_time_live.replace("%command", "seek"), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if str(time).replace("-", "").isnumeric():
            time = int(time)
        else:
            time = int(convert_formated(time))
        if time < 0: time = 0
        if time > vid['length'] and not vid['type'] == 'raw_audio':
            await skip(ctx)
            return
        current_time = datetime.datetime.now()
        song_start_times[gid] = current_time - datetime.timedelta(seconds=time)
        paused_durations[gid] = datetime.timedelta()
        pause_start_times[gid] = None
        current_time = get_current_time(gid)

        seek_called = True
        if voice_client.is_paused(): voice_client.resume()
        voice_client.stop()
        updated_options = get_updated_options(vid, current_time)
        voice_client.play(
            discord.FFmpegPCMAudio(vid['stream_url'], **updated_options),
            after=lambda e: on_song_end(ctx, e))

        duracion, actual = convert_seconds(int(vid['length'])), convert_seconds(current_time)
        embed = discord.Embed(
            title=INV_CHAR_PADDING + seek_title.replace("%time", str(actual)),
            description=f"{utilidades.get_bar(int(vid['length']), current_time)}",
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()
        await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)


@bot.command(name='loop', aliases=['lp'])
async def loop(ctx, *, mode="change"):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_loop"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global loop_mode
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        mode = mode.lower()
        if mode == "change": mode = "all" if loop_mode[gid] == "off" else "off"
        if mode not in {'queue', 'all', 'shuffle', 'random', 'one', 'off', 'autodj'}:
            await channel_to_send.send(not_loop_mode.replace("%mode", str(mode)),
                           reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        loop_mode[gid] = str(mode)
        await channel_to_send.send(loop_mode_changed.replace("%loop", loop_mode[gid]) if loop_mode[gid] != 'off' else loop_disable,
                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='shuffle', aliases=['sf', 'random'])
async def shuffle(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_shuffle"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        queue = dict_queue[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client.is_playing(): voice_client.pause()
        dict_current_song[gid] = -1
        random.shuffle(queue)
        del song_start_times[gid]
        del pause_start_times[gid]
        del paused_durations[gid]
        await skip(ctx)
        return True
    except:
        traceback.print_exc()


@bot.command(name='queue', aliases=['q'])
async def cola(ctx, *, tmp='', silent=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_queue"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        if not queue:
            await channel_to_send.send(random.choice(no_queue_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not silent:
            num_pages = (len(queue) - 1) // QUEUE_VIDEOS_PER_PAGE + 1
            view = QueueMenu(queue, num_pages, ctx, gid)
            embed = view.create_embed()
            await channel_to_send.send(embed=embed, view=view, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='pause', aliases=['stop'])
async def pause(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_pause"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        queue = dict_queue[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue or not voice_client.is_playing():
            if voice_client.is_paused(): return
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client.pause()
        pause_start_times[gid] = datetime.datetime.now()
    except:
        traceback.print_exc()


@bot.command(name='resume', aliases=[])
async def resume(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_resume"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        queue = dict_queue[gid]
        if voice_client is None or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client.resume()
        pause_duration = datetime.datetime.now() - pause_start_times[gid]
        paused_durations[gid] += pause_duration
        pause_start_times[gid] = None
    except:
        traceback.print_exc()


@bot.command(name='skip', aliases=['s', 'next'])
async def skip(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        global vote_skip_dict, loop_mode, vote_skip_counter, message_id_dict, majority_dict, ctx_dict_skip
        gid = str(ctx.guild.id)
        vote_skip_dict.setdefault(gid, -1)
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if vote_skip_dict[gid] == -1:
            if voice_client is None:
                await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if not check_perms(ctx, "use_skip"):
                if not check_perms(ctx, "use_vote_skip"):
                    await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                    return
                members = voice_client.channel.members
                member_amount = len(members) - 1
                majority = member_amount // 2 + 1
                vote_message = await channel_to_send.send(vote_skip_text.replace("%num", str(majority)))
                await vote_message.add_reaction("❌")
                await vote_message.add_reaction("✅")
                await asyncio.sleep(0.25)
                vote_skip_dict[gid], vote_skip_counter[gid] = 0, 0
                message_id_dict[gid], majority_dict[gid] = vote_message.id, [majority, list(user.id for user in voice_client.channel.members)]
                ctx_dict_skip[gid] = ctx
                vote_skip.start()
        if vote_skip_dict[gid] == 0: return
        vote_skip_dict[gid], vote_skip_counter[gid] = -1, 0
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] == 'one': loop_mode[gid] = 'off'
        if voice_client.is_paused(): voice_client.resume()
        if voice_client.is_playing(): voice_client.stop()
        else: await play_next(ctx, rewinded=2)
    except:
        traceback.print_exc()


@bot.command(name='goto')
async def goto(ctx, num):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_goto"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, [])
        queue = dict_queue[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client is None or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        try:
            num = min(max(int(num), -1), len(queue))
            if num == 0:
                dict_current_song[gid] = -1
            elif num == -1:
                dict_current_song[gid] = len(queue)-2
            else:
                dict_current_song[gid] = num - 2
            await skip(ctx)
        except:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name="pfp", aliases=['profile', 'avatar'])
async def pfp(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_avatar"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed = discord.Embed(
            title=profile_title.replace("%name", ctx.author.global_name),
            color=EMBED_COLOR
        )
        embed.set_image(url=ctx.author.avatar.url)
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        await channel_to_send.send(random.choice(avatar_error_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        traceback.print_exc()


@bot.command(name='steam')
async def steam(ctx, name):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_steam"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        name = name.lower()
        url = f'https://steamcommunity.com/id/{name}'
        embed = discord.Embed(
            title=steam_title.replace("%name", name),
            color=EMBED_COLOR,
            url=url
        )
        imgurl = utilidades.get_steam_avatar(url)
        if not imgurl:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed.set_image(url=imgurl)
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='chatgpt', aliases=['chat', 'gpt', 'ask'])
async def chatgpt(ctx, *, msg):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_chatgpt"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not OPENAI_KEY:
            await channel_to_send.send(random.choice(no_api_key_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed = discord.Embed(
            title=chatgpt_title,
            description=f"{utilidades.chatgpt(msg, OPENAI_KEY, language)}",
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()
        await channel_to_send.send(random.choice(no_api_credits_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)


@bot.command(name='lyrics', aliases=['lyric'])
async def lyrics(ctx, *, query=None):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_lyrics"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID or not GENIUS_ACCESS_TOKEN:
            await channel_to_send.send(random.choice(no_api_key_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if query is None and voice_client is None:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not query:
            gid = str(ctx.guild.id)
            dict_queue.setdefault(gid, list())
            dict_current_song.setdefault(gid, 0)
            queue = dict_queue[gid]
            current_song = dict_current_song[gid]
            vid = queue[current_song]
            if isinstance(vid, str):
                dict_queue[gid][current_song] = vid = info_from_url(vid)
            titulo = vid['title']
            vid_channel = vid['channel'] if vid['channel'] else '???'
        else:
            titulo = query
            vid_channel = '???'

        artista = utilidades.get_spotify_artist(titulo+vid_channel*(vid_channel != "???"), is_song=True)
        cancion = utilidades.get_spotify_song(titulo)
        if not all([artista, cancion]):
            await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed = discord.Embed(
            title=lyrics_title,
            description=lyrics_desc.replace("%title", cancion).replace("%artist", artista),
            color=EMBED_COLOR
        )
        lyrics = utilidades.get_lyrics(titulo, (artista, cancion))
        if not all(lyrics):
            await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        if len(lyrics) > 9000:
            await channel_to_send.send(random.choice(lyrics_too_long_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        for i in range(0, len(lyrics), 2000):
            await channel_to_send.send(lyrics[i:i + 2000], reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except Exception as e:
        traceback.print_exc()


@bot.command(name='songs', aliases=['song', 'top'])
async def songs(ctx, number=None, *, artista=""):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_songs"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID:
            await channel_to_send.send(random.choice(no_api_key_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if number is None and artista == "":
            if voice_client is not None and voice_client.is_playing():
                gid = str(ctx.guild.id)
                dict_queue.setdefault(gid, list())
                dict_current_song.setdefault(gid, 0)
                queue = dict_queue[gid]
                current_song = dict_current_song[gid]
                artista = queue[current_song]['title']
                number = 10
                m = True
            else:
                await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        else:
            try:
                number = int(number)
                if number < 1: number = 1
                if number > 10: number = 10
            except:
                artista = str(number) + str(artista)
                number = 10
            m = False
        artista = utilidades.get_spotify_artist(artista, is_song=m)
        canciones = utilidades.get_top_songs(artista, number)

        if not canciones or not artista:
            await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed = discord.Embed(
            title=top_songs_title.replace("%number", str(number)).replace("%artist", artista),
            description=''.join(f"➤ *{cancion}*\n" for cancion in canciones),
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=utilidades.get_artist_image_url(artista))
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except Exception as e:
        traceback.print_exc()


@bot.command(name='chords', aliases=[])
async def chords(ctx, *, query=""):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_chords"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not SPOTIFY_ID or not SPOTIFY_SECRET:
            await channel_to_send.send(random.choice(no_api_key_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        traspose = None
        if query:
            for opts in {'-traspose', '-t', '-trs', '-tp', '-tone', '-tonality'}:
                vals = query.split(opts)
                vals = vals if len(vals) > 1 else [vals[0], ""]
                tquery, ttraspose = vals[0], vals[1]
                if ttraspose: break
            query, traspose = tquery.strip(), ttraspose.strip()
        if not query and voice_client is not None and voice_client.is_playing():
            gid = str(ctx.guild.id)
            dict_queue.setdefault(gid, list())
            dict_current_song.setdefault(gid, 0)
            queue = dict_queue[gid]
            current_song = dict_current_song[gid]
            vid = queue[current_song]
            if isinstance(vid, str):
                dict_queue[gid][current_song] = vid = info_from_url(vid)
            vid_channel = vid['channel'] if vid['channel'] else '???'
            query = vid['title']+vid_channel*(vid_channel != '???')
        elif not query:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        artista, cancion = utilidades.get_artist_and_song(query)

        if not traspose: traspose = 0
        try: traspose = int(traspose)
        except: traspose = 0
        msg, tuning_info = utilidades.get_chords_and_lyrics(query, traspose=traspose)
        if not msg:
            msg, tuning_info = await utilidades.search_cifraclub(query, traspose=traspose)
        if not msg:
            await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not tuning_info['tuning_name']:
            tuning_info['tuning_name'] = '???'
        capo = tuning_info['capo']
        if capo == 'None':
            capo = no_capo_chords
            th_val = ""
        elif int(capo) == 1:
            th_val = "st fret"
        elif int(capo) == 2:
            th_val = "nd fret"
        elif int(capo) == 3:
            th_val = "rd fret"
        else:
            th_val = "th fret"
        tuning_embed = discord.Embed(
            title=tuning_embed_title,
            description=tuning_embed_desc.replace("%tonality", tuning_info['tonality']).replace("%capo", capo).replace("%th", th_val)
                .replace("%tuning_name", tuning_info['tuning_name']).replace("%tuning_value", tuning_info['tuning_value'])
                .replace("%traspose", "+"*int(traspose >= 0)+str(traspose)),
            color=EMBED_COLOR
        )
        for i in range(0, len(msg), 4000):
            embed = discord.Embed(
                title="",
                description=msg[i:i + 4000],
                color=EMBED_COLOR
            )
            if i == 0: embed.title = chords_title.replace("%song", cancion).replace("%artist", artista)

            await channel_to_send.send(embeds=[tuning_embed, embed], reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='nightcore', aliases=['spedup', 'speedup'])
async def nightcore(ctx):
    try:
        await pitch(ctx, semitones=4, speed=1+4/12, silent=True)
    except:
        traceback.print_exc()


@bot.command(name='daycore', aliases=['slowed', 'slow'])
async def daycore(ctx):
    try:
        await pitch(ctx, semitones=-2, speed=1-2/12, silent=True)
    except:
        traceback.print_exc()


@bot.command(name='pitch', aliases=['tone'])
async def pitch(ctx, semitones=None, speed=1.0, *, silent=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_pitch"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        speed = max(min(speed, 5), 0.2)
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client.is_playing(): voice_client.pause()
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        if not semitones: semitones = 0  # return to default
        pitch_factor = min(max(0.01, 2**((float(semitones))/12)), 2)
        vid['audio_options']['pitch'] = pitch_factor
        vid['audio_options']['speed'] = speed
        updated_options = get_updated_options(vid, get_current_time(gid))
        voice_client.play(discord.FFmpegPCMAudio(queue[current_song]['stream_url'], **updated_options),
                              after=lambda e: on_song_end(ctx, e))
        if not silent:
            embed = discord.Embed(
                title=pitch_title,
                description=pitch_desc.replace("%sign", "+" if float(semitones) >= 0 else "-").replace("%tone", str(abs(float(semitones)))).replace("%speed", str(speed)),
                color=EMBED_COLOR
            )
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='volume', aliases=['vol'])
async def volume(ctx, volume: str):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_volume"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        try:
            volume = volume.lower().replace("%", "")
            if "db" not in volume:
                volume = max(min(float(volume), 300), 0.01)
                vol_db = 20 * math.log10(volume / 100)
            else:
                vol_db = max(min(9.54, float(volume.replace("db", ""))), -80)
        except:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client.is_playing(): voice_client.pause()
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        vid['audio_options']['volume'] = vol_db
        updated_options = get_updated_options(vid, get_current_time(gid))
        voice_client.play(discord.FFmpegPCMAudio(queue[current_song]['stream_url'], **updated_options),
                              after=lambda e: on_song_end(ctx, e))
        embed = discord.Embed(
            title=volume_title,
            description=volume_desc.replace("%vol", f"{vol_db:.2f}dB").replace("%perc", f"%{100*(10**(vol_db/20)):.2f}"),
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='eq', aliases=['equalize', 'equalizer'])
async def eq(ctx, eqtype="bass", strength="5", silent=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_eq"):
            await channel_to_send.send(random.choice(insuff_perms_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        try:
            strength = str(min(max(float(strength), 0), 12))
            if eqtype not in {'bass', 'high'}:
                raise Exception
        except:
            await channel_to_send.send(random.choice(invalid_use_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client.is_playing(): voice_client.pause()
        vid['audio_options'][eqtype] = strength
        updated_options = get_updated_options(vid, get_current_time(gid))
        voice_client.play(discord.FFmpegPCMAudio(queue[current_song]['stream_url'], **updated_options),
                          after=lambda e: on_song_end(ctx, e))
        if not silent:
            embed = discord.Embed(
                title=eq_title,
                description=eq_desc.replace("%freq", "300Hz" if eqtype == 'bass' else "8.0kHz")
                    .replace("%width", "120Hz" if eqtype == 'bass' else "3.0kHz")
                    .replace("%vol", f"{float(strength):.2f}dB"),
                color=EMBED_COLOR
            )
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='bassboost', aliases=['bass', 'low', 'lowboost'])
async def bassboost(ctx):
    try:
        await eq(ctx, eqtype='bass', strength='5', silent=True)
    except:
        traceback.print_exc()


@bot.command(name='highboost', aliases=['high'])
async def highboost(ctx):
    try:
        await eq(ctx, eqtype='high', strength='8', silent=True)
    except:
        traceback.print_exc()


@bot.command(name='mono')
async def mono(ctx):
    try:
        await change_channels(ctx, channels=1)
    except:
        traceback.print_exc()


@bot.command(name='stereo')
async def stereo(ctx):
    try:
        await change_channels(ctx, channels=2)
    except:
        traceback.print_exc()


@bot.command(name='shazam', aliases=['recognize', 'thissong', 'current', 'this', 'currentsong'])
async def shazam(ctx, clip_length='15'):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_shazam"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        start_time = get_current_time(gid)
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        msg = await channel_to_send.send(recognizing_song, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        recognized_song = await find_song_shazam(vid['stream_url'], start_time, vid['length'], vid['type'], clip_length=float(clip_length))
        if not recognized_song:
            await channel_to_send.send(shazam_no_song, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        try:
            genres_dict = recognized_song['genres']
            genres = genres_dict['primary']
            if len(genres_dict.keys()) > 1:
                for genre in genres_dict:
                    genres += genres_dict[genre]
                plural = True
            else:
                plural = False
        except:
            genres = "Unknown"
            plural = False
        try:
            album = recognized_song['sections'][0]['metadata']
            album_info = f"{album[0]['text']} ({album[2]['text']}, {album[1]['text']})"
        except:
            album_info = no_album_info_found
        embed = discord.Embed(
            title=shazam_title,
            description=shazam_desc.replace("%title", recognized_song['title']).replace("%artist", recognized_song['subtitle'])
                .replace("%genres", genres).replace("%plural", "s" if plural else "").replace("%album", album_info),
            color=EMBED_COLOR,
            url=recognized_song['url']
        )
        try:
            embed.set_image(url=recognized_song['images']['coverarthq'])
            embed.set_thumbnail(url=recognized_song['images']['background'])
        except:
            try:
                embed.set_image(url=recognized_song['images']['coverart'])
            except:
                pass
        await msg.delete()
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='autodj', aliases=['auto', 'autoplaylist', 'autopl', 'autoplay'])
async def autodj(ctx, *, url="", ignore=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_autodj"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song, loop_mode
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if not ignore and not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not queue and not url:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if url:
            await fastplay(ctx, url=url)
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is None: return
        start_time = get_current_time(gid)
        vid = queue[current_song-int(1*ignore)]
        if isinstance(vid, str):
            dict_queue[gid][current_song] = vid = info_from_url(vid)
        recognized_song = await find_song_shazam(vid['stream_url'], start_time, vid['length'], vid['type'], clip_length=15)
        try:
            related = requests.get(recognized_song['relatedtracksurl']).json()['tracks']
        except:
            await channel_to_send.send(autodj_no_song,
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        tracks = [random.choice(related[:3])]
        if AUTO_DJ_MAX_ADD > 1:
            tmp_tracks = random.sample(related[3:], k=AUTO_DJ_MAX_ADD-1)
        else:
            tmp_tracks = []
        tracks = tmp_tracks + tracks + related
        loop_mode[gid] = "autodj"
        queue_vids = list(filter(lambda vid: not isinstance(vid, str), queue))

        def clean(title):
            return re.sub(r'[\(\)\{\}\[\]]|audio|live|official|video|lyrics|lyric', '', title.lower()).strip()

        queue_titles = [clean(vid['title']) for vid in queue_vids]
        song_count = 0
        for track in tracks:
            if song_count >= AUTO_DJ_MAX_ADD: break
            try:
                query = f"+{track['title']}, {track['subtitle']} audio"
                if not process.extractOne(clean(query), queue_titles)[1] >= 88:
                    song = search_youtube(query=query, max_results=1)[0]
                    await play(ctx, url=song, silent=True, attachment=False)
                    song_count += 1
            except:
                traceback.print_exc()
                pass
        await channel_to_send.send(autodj_added_songs.replace("%num", str(song_count)), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='add_prefix', aliases=['prefix', 'set_prefix'])
async def add_prefix(ctx, prefix):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_add_prefix"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)
        file_path = f'options_{gid}.json'
        create_options_file(file_path)

        try:
            with open(file_path, 'r') as f:
                options = json.load(f)
        except:
            create_options_file(file_path, force=True)
            with open(file_path, 'r') as f:
                options = json.load(f)
        if not 'custom_prefixes' in options:
            options = write_options(options, gid, ['custom_prefixes'])
        if prefix not in options['custom_prefixes']: options['custom_prefixes'].append(prefix)
        embed = discord.Embed(
            title=prefix_add_title,
            description=prefix_add_desc.replace("%prefix", prefix).replace("%prfixes",
                                                                           ' '.join(options['custom_prefixes'])),
            color=EMBED_COLOR
        )

        with open(file_path, 'w') as f:
            json.dump(options, f)

        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='del_prefix', aliases=['remove_prefix', 'rm_prefix'])
async def del_prefix(ctx, prefix):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_del_prefix"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)
        file_path = f'options_{gid}.json'
        create_options_file(file_path)

        try:
            with open(file_path, 'r') as f:
                options = json.load(f)
        except:
            create_options_file(file_path, force=True)
            with open(file_path, 'r') as f:
                options = json.load(f)
        if not 'custom_prefixes' in options:
            options = write_options(options, gid, ['custom_prefixes'])
        if prefix in options['custom_prefixes']: options['custom_prefixes'].remove(prefix)

        embed = discord.Embed(
            title=prefix_del_title,
            description=prefix_del_desc.replace("%prefix", prefix).replace("%prfixes",
                                                                           ' '.join(options['custom_prefixes'])),
            color=EMBED_COLOR
        )

        with open(file_path, 'w') as f:
            json.dump(options, f)

        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='lang', aliases=['language', 'change_lang', 'change_language'])
async def lang(ctx, lng=None, silent=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_lang"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not lng or lng.lower() not in ['es', 'en']:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return

        subprocess.run(["python.exe", "lang/lang.py"])
        with open(f"lang/{lng.lower()}.json", "r") as f:
            lang_dict = json.load(f)

        config.set("Config", "lang", lng.lower())
        with open(config_path, "w") as f:
            config.write(f)

        globals().update(lang_dict)

        if not silent: await channel_to_send.send(lang_changed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name="restrict", aliases=['channel'])
async def restrict(ctx, name=""):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_restrict"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not name or name in {"ALL_CHANNELS"}:
            await options(ctx, option="restricted_to", query="ALL_CHANNELS", ignore=True)
            await channel_to_send.send(not_restricted, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        else:
            channel = discord.utils.get(ctx.guild.channels, name=name)
            if channel:
                if channel.permissions_for(ctx.guild.me).send_messages:
                    await options(ctx, option="restricted_to", query=name, ignore=True)
                    await channel_to_send.send(restricted_to_channel.replace("%name", name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                else:
                    await channel_to_send.send(cant_access_channel.replace("%name", name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            else:
                await channel_to_send.send(channel_doesnt_exist.replace("%name", name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='download')
async def download(ctx, choose_song=""):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_download"):
            await channel_to_send.send(random.choice(insuff_perms_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if choose_song:
            try:
                current_song = min(max(int(choose_song)-1, 0), len(queue)-1)
            except:
                pass
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not voice_client or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[current_song]
        if isinstance(vid, str):
            dict_queue[gid][dict_queue[gid].index(vid)] = vid = info_from_url(vid, is_url=is_url(vid))
        url = vid['stream_url']
        original_url = vid['url']
        if vid['type'] == 'live':
            await channel_to_send.send(cannot_download_live, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if 'manifest' in url or '.m3u8' in url:
            await channel_to_send.send(cannot_download_m3u8, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        await channel_to_send.send(download_url.replace("%url", url).replace("%original_url", original_url), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='reverse')
async def reverse(ctx):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_reverse"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song

        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        queue = dict_queue[gid]
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is None:
            await channel_to_send.send(random.choice(nothing_on_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return

        voice_channel = ctx.author.voice.channel
        if voice_client.channel != voice_channel:
            await channel_to_send.send(already_on_another_vc, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return

        if not queue:
            await channel_to_send.send(random.choice(no_queue_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return

        dict_current_song[gid] = -1
        del song_start_times[gid]
        del pause_start_times[gid]
        del paused_durations[gid]
        queue.reverse()
        await skip(ctx)
        await channel_to_send.send(queue_reversed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        return 1
    except:
        traceback.print_exc()


@bot.command(name='reload', aliases=['reload_params'])
@commands.has_permissions(administrator=True)
async def reload(ctx):
    try:
        parameters = read_param()
        if len(parameters.keys()) < ALL_PARAM_COUNT:
            input(f"\033[91m{missing_parameters}\033[0m")
            write_param()
            parameters = read_param()

        globals().update(parameters)
        print("Parameters successfully reloaded.")
    except:
        traceback.print_exc()


@bot.command(name='parameter', aliases=['param', 'parameters'])
async def parameter(ctx, parameter=None, *, value=None):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_parameter"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        parameters = read_param()
        if len(parameters.keys()) < ALL_PARAM_COUNT:
            input(f"\033[91m{missing_parameters}\033[0m")
            write_param()
            parameters = read_param()
        if parameter is None:
            embed = discord.Embed(
                title=parameters_title,
                description=', '.join([f"`{param}`" for param in parameters]),
                color=EMBED_COLOR
            )
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        parameter = parameter.upper()
        if parameter in {'DEFAULT', 'RESET', 'RESTART'}:
            write_param()
            parameters = read_param()
            globals().update(parameters)
            print("Parameters succesfully reloaded.")
            await channel_to_send.send(parameters_to_default, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if parameter not in parameters:
            await channel_to_send.send(invalid_parameter, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if value is None:
            embed = discord.Embed(
                title=parameter_value_title,
                description=f"{parameter} = {parameters[parameter]}",
                color=EMBED_COLOR
            )
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        parameters[parameter] = value
        write_param(parameters)
        parameters = read_param()
        globals().update(parameters)
        if parameter == 'FONT':
            config = configparser.ConfigParser()
            try:
                with open(config_path, "r") as f:
                    config.read_string(f.read())
            except:
                config.add_section("Config")
                config.set("Config", "lang", "en")
                with open(config_path, "w") as f:
                    config.write(f)
            await lang(ctx, lng=config.get('Config', 'lang').lower(), silent=True)
        print("Parameters succesfully reloaded.")
        await channel_to_send.send(parameter_changed_value.replace("%pname", parameter).replace("%value", value), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        return
    except:
        traceback.print_exc()


@bot.command(name='playlist', aliases=['playlists', 'favorites', 'favourites', 'fav', 'favs'])
async def playlist(ctx, mode, playlist_name="", *, query=""):
    try:
        global dict_queue, dict_current_song
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not check_perms(ctx, "use_playlist"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)

        mode = mode.lower()
        if not mode in {'load', 'import'}: playlist_name = playlist_name.lower()
        playlist_name = playlist_name.strip()
        file_path = f"playlists_{gid}.json"
        playlists = read_playlists(file_path, bot)
        if mode in {'playlists', 'names', 'created'}:
            if not playlists:
                await channel_to_send.send(no_playlists_created.replace("%server_name", ctx.guild.name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            embed = discord.Embed(
                title=playlist_list_title,
                description=""
            )
            desc = "\n".join([f"- **{key}**: `{len(playlists[key]['songs'])}` "+playlist_info.replace("%name", playlists[key]['creator']['name']) for key in playlists.keys()])
            embed.description = playlist_list_desc.replace("%playlists", desc)
            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not playlist_name:
            playlist_name = 'favs'
        if mode in {'load', 'import'}:
            try:
                if ctx.message.attachments:
                    str_data = None
                    for attachment in ctx.message.attachments:
                        if attachment.filename.endswith('.txt'):
                            await attachment.save(attachment.filename)
                            with open(attachment.filename, 'r') as f:
                                str_data = f.read()
                            break
                    if not str_data:
                        str_data = playlist_name
                else:
                    str_data = playlist_name
                loaded_name, loaded_gid = str_data.rsplit("%PL%", 1)
                if not loaded_gid.isnumeric():
                    loaded_urls = []
                    b85 = False
                    for i in range(0, len(loaded_gid), 11):
                        video_id = loaded_gid[i:i + 11]
                        if not re.match("^[a-zA-Z0-9_-]{11}$", video_id):
                            b85 = True
                            break
                        loaded_urls.append("https://youtube.com/watch?v="+video_id)
                    if b85:
                        loaded_urls = b85decode(loaded_gid).decode().split(";")
                    loaded_playlist = {'songs': loaded_urls, 'creator': {'avatar': str(ctx.author.avatar), 'display_name': str(ctx.author.display_name), 'name': str(ctx.author.name)}}
                else:
                    playlist_path = f"playlists_{loaded_gid}.json"
                    loaded_playlist = read_playlists(playlist_path, bot)[loaded_name]
                    loaded_urls = loaded_playlist['songs']
                playlists[loaded_name] = {}
                playlists[loaded_name].update(loaded_playlist)
                write_to_playlist(file_path, playlists)
            except:
                traceback.print_exc()
                await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            await channel_to_send.send(playlist_loaded.replace("%pl_name", loaded_name).replace("%len", str(len(loaded_urls))),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if mode == 'create':
            if playlist_name in playlists.keys():
                await channel_to_send.send(playlist_already_exists.replace("%pl_name", playlist_name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            playlists[playlist_name] = {'songs': [], 'creator': {'avatar': str(ctx.author.avatar), 'display_name': str(ctx.author.display_name), 'name': str(ctx.author.name)}}
            write_to_playlist(file_path, playlists)
            await channel_to_send.send(playlist_created.replace("%pl_name", playlist_name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not playlist_name in playlists.keys():
            await channel_to_send.send(playlist_not_found.replace("%pl_name", playlist_name),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if mode == 'share':
            await channel_to_send.send(shared_playlist_code.replace("%code", get_share_code(gid=gid, playlist_name=playlist_name)),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        if mode in {'sharecomp', 'sharecomplete', 'compshare', 'completeshare', 'fullshare', 'sharefull'}:
            share_code = get_share_code(urls=playlists[playlist_name]['songs'], playlist_name=playlist_name, shortened=False)
            with open(r"code.txt", "w") as f:
                f.write(share_code)
            await channel_to_send.send(file=discord.File(r"code.txt"), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        if mode == 'add':
            if not query:
                dict_queue.setdefault(gid, [])
                dict_current_song.setdefault(gid, 0)
                queue = dict_queue[gid]
                if not voice_client or not queue:
                    await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                    return
                current_song = dict_current_song[gid]
                vid = queue[current_song]
                if isinstance(vid, str):
                    dict_queue[gid][current_song] = vid = info_from_url(vid)
                playlists[playlist_name]['songs'].append(vid['url'])
                write_to_playlist(file_path, playlists)
            else:
                if not is_url(query):
                    vid = search_youtube(query, max_results=1)[0]
                else:
                    vid = info_from_url(query, is_url=True)
                if not vid:
                    await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                    return
                playlists[playlist_name]['songs'].append(vid['url'])
                write_to_playlist(file_path, playlists)
            await channel_to_send.send(added_to_playlist_url.replace("%pl_name", playlist_name).replace("%title", vid['title'])
                                       .replace("%url", vid['url']), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        elif mode in {'queue', 'addqueue', 'queueadd'}:
            queue = dict_queue[gid]
            if not queue:
                await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            for vid in queue:
                if isinstance(vid, str):
                    url = vid
                else:
                    url = vid['url']
                playlists[playlist_name]['songs'].append(url)
            write_to_playlist(file_path, playlists)
            await channel_to_send.send(queue_added_to_playlist.replace("%pl_name", playlist_name).replace("%num_songs", str(len(queue))),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        elif mode in {'rm', 'remove'}:
            queue = playlists[playlist_name]['songs']
            if not queue:
                await channel_to_send.send(playlist_no_songs.replace("%pl_name", playlist_name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            try:
                query = min(int(query), len(queue))
            except:
                await channel_to_send.send(random.choice(invalid_use_texts),
                                           reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if query < 0: query = len(queue)
            if query == 0: query = 1
            url = playlists[playlist_name]['songs'][query-1]
            playlists[playlist_name]['songs'].pop(query-1)
            write_to_playlist(file_path, playlists)
            await channel_to_send.send(removed_from_playlist.replace("%pl_name", playlist_name).replace("%url", url).replace("%number", str(query)),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        elif mode == 'clear':
            playlists[playlist_name]['songs'] = []
            write_to_playlist(file_path, playlists)
            await channel_to_send.send(playlist_cleared.replace("%pl_name", playlist_name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        elif mode in {'list', 'songs', 'videos'}:
            queue = playlists[playlist_name]['songs']
            if not queue:
                await channel_to_send.send(playlist_no_songs.replace("%pl_name", playlist_name),
                                           reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            num_pages = (len(queue) - 1) // QUEUE_VIDEOS_PER_PAGE + 1
            creator = playlists[playlist_name]['creator']
            view = PlaylistQueueMenu(queue, num_pages, ctx, gid, playlist_name, creator)
            embed = view.create_embed()
            await channel_to_send.send(embed=embed, view=view,
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        elif mode == 'play':
            links = playlists[playlist_name]['songs'].copy()
            if not links:
                await channel_to_send.send(playlist_no_songs.replace("%pl_name", playlist_name),
                                           reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if not voice_client or not voice_client.is_playing() and not voice_client.is_paused():
                await play(ctx, url=links[0], search=False)
            else:
                links.insert(0, links[0])
            dict_queue[gid] = dict_queue[gid] + links[1:]
            await channel_to_send.send(playlist_played.replace("%pl_name", playlist_name),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        elif mode in {'delete', 'del'}:
            data = {}
            for pl in playlists:
                if pl == playlist_name:
                    continue
                data.update({f"{pl}": playlists[pl]})
            with open(file_path, 'w') as f:
                json.dump(data, f)
            await channel_to_send.send(playlist_deleted.replace("%pl_name", playlist_name),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


if os.path.exists('extra_commands.py'):
    import extra_commands
    extra_commands.add_commands(bot, {'EMBED_COLOR': EMBED_COLOR, 'logged_in': logged_in})


bot.run(DISCORD_APP_KEY)
