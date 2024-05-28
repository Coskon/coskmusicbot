import discord
import asyncio
import utilidades
import spotipy
import os, random, re, json, traceback, time, configparser, math
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
if not os.path.exists(config_path):
    config.add_section("Config")
    config.set("Config", "lang", "en")
    with open(config_path, "w") as f:
        config.write(f)
with open(config_path, "r") as f:
    config.read_string(f.read())

language = config.get('Config', 'lang')
with open(f"lang/{language}.json", "r") as f:
    lang_dict = json.load(f)

globals().update(lang_dict)

## PARAMETER VARIABLES ##
parameters = read_param()
if len(parameters.keys()) < 31:
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
dict_queue, active_servers, ctx_dict = dict(), dict(), dict()
button_choice, vote_skip_dict, vote_skip_counter = dict(), dict(), dict()
message_id_dict, majority_dict, ctx_dict_skip = dict(), dict(), dict()
user_cooldowns = {}
loop_mode = dict()
dict_current_song, dict_current_time = dict(), dict()
go_back, seek_called, disable_play = (False for _ in range(3))
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
    'cookiefile': './cookies.txt' if os.path.exists('./cookies.txt') else None
}
PREFERRED_FORMATS = {'http', 'mp4', 'Audio_Only'}
EXTRA_FORMATS = {'160p', '360p', '480p', '720p60', '1080p60', '0', 'hls_mp3_128', 'http_mp3_128',
                 'hls_opus_64', 'hls'}

## NORMAL FUNCTIONS ##
def get_sp_id(url):
    # Extract the track ID from the Spotify URL
    pattern = r'\/track\/([a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Spotify URL")


def get_video_info(video, gid):
    global dict_queue
    try:
        if isinstance(video, str):
            dict_queue[gid][dict_queue[gid].index(video)] = info_from_url(video, is_url=is_url(video))
    except:
        traceback.print_exc()


def create_options_file(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({ "search_limit": DEFAULT_SEARCH_LIMIT, "recomm_limit": DEFAULT_RECOMMENDATION_LIMIT,
                       "custom_prefixes": DEFAULT_PREFIXES, "restricted_to": "ALL_CHANNELS" }, f)


def create_perms_file(ctx, file_path):
    if not os.path.exists(file_path):
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
        go_back = False
        if update_current_time.is_running(): update_current_time.stop()
        bot.loop.create_task(play_next(ctx))


def get_stream_url(stream_info: dict, itags: list):
    for itag in itags:
        stream_url = next((d.get("url") for d in stream_info if d.get("itag") == itag), None)
        if stream_url: return stream_url
    return


def fetch_info(result):
    vtype = 'video'
    try:
        streaming_data = result.vid_info['streamingData']
        stream_url = get_stream_url(streaming_data['formats'], itags=ITAGS_LIST)  # get best stream url if possible
        if not stream_url:
            stream_url = get_stream_url(streaming_data['adaptiveFormats'], itags=ITAGS_LIST)  # get best stream url if possible
    except:
        try:
            streaming_data = result.vid_info['streamingData']
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
    return {
        'obj': result, 'title': result.title, 'channel': result.author, 'views': result.views,
        'length': int(result.length), 'id': result.video_id, 'thumbnail_url': result.thumbnail_url,
        'url': result.watch_url, 'stream_url': stream_url, 'channel_url': result.channel_url, 'type': vtype,
        'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'bass': 0.0, 'high': 0.0}
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
        result = YouTube(url, use_oauth=USE_LOGIN, allow_oauth_cache=True)
        if result.vid_info['playabilityStatus']['status'] == 'ERROR':
            raise Exception
    except:
        not_youtube = True
    vtype = 'video'
    try:
        streaming_data = result.vid_info['streamingData']
        stream_url = get_stream_url(streaming_data['formats'], itags=ITAGS_LIST)  # get best stream url if possible
        if not stream_url:
            stream_url = get_stream_url(streaming_data['adaptiveFormats'], itags=ITAGS_LIST)  # get best stream url if possible
    except:
        try:
            streaming_data = result.vid_info['streamingData']
            stream_url = streaming_data['hlsManifestUrl']
            vtype = 'live'
        except: # ABSOLUTE LAST RESORT, THE MYTH THE LEGEND YT-DLP
            try:
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
        try: title = info['title']
        except: title = 'Some audio'
        try: channel = info['uploader']
        except: channel = 'Someone'
        try: views = info['view_count']
        except: views = 'A lot, probably'
        return {
            'obj': None, 'title': title, 'channel': channel, 'views': views,
            'length': dur, 'id': None, 'thumbnail_url': thumb,
            'url': url, 'stream_url': stream_url, 'channel_url': None, 'type': vtype,
            'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'bass': 0.0, 'high': 0.0}
            # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
        }
    return {
        'obj': result, 'title': result.title, 'channel': result.author, 'views': result.views,
        'length': int(result.length), 'id': result.video_id, 'thumbnail_url': result.thumbnail_url,
        'url': result.watch_url, 'stream_url': stream_url, 'channel_url': result.channel_url, 'type': vtype,
        'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'bass': 0.0, 'high': 0.0}
        # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
    }


def change_active(ctx, mode="a"):
    global active_servers
    active_servers[str(ctx.guild.id)] = 1 if mode == "a" else 0
    print(f"{'active on' if mode == 'a' else 'left'} -> {ctx.guild.name}")


def check_perms(ctx, perm):
    file_path = f'user_perms_{ctx.guild.id}.json'
    create_perms_file(ctx, file_path)
    with open(file_path, 'r') as f:
        user_perms = json.load(f)
    if perm not in user_perms[str(ctx.author.id)]:
        return False
    return True


def get_channel_restriction(ctx):
    file_path = f'options_{ctx.guild.id}.json'
    create_options_file(file_path)
    with open(file_path, 'r') as f:
        options = json.load(f)
    return (ctx, True) if options['restricted_to'] == 'ALL_CHANNELS' \
        else (discord.utils.get(ctx.guild.channels, name=options['restricted_to']), False)


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


async def play_next(ctx):
    global dict_current_song, loop_mode, dict_queue
    gid = str(ctx.guild.id)
    dict_queue.setdefault(gid, list())
    dict_current_song.setdefault(gid, 0)
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
            await leave(ctx, ignore=True)
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
    if start > total_length-10: start -= 10
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
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    try:
        AudioSegment.from_file(BytesIO(response.content), start_second=start, duration=clip_length).export(r'downloads/shazam.mp3', format='mp3')
    except:
        print("pydub failed, moving to ffmpeg...")
        start_time = '00:00:00' if vtype == 'live' else '00:'*(start < 3600)+convert_seconds(start)
        end_time = f'00:00:{clip_length}' if vtype == 'live' else '00:'*(start+10 < 3600)+convert_seconds(start+clip_length)
        subprocess.run(['ffmpeg', '-ss', start_time, '-to', end_time, '-i', url, '-y', 'downloads/shazam.mp3'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shazam = Shazam()
    out = await shazam.recognize(r'downloads/shazam.mp3')
    if not out or not out['matches']: return None
    return out['track']


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
        super().__init__()
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
                self.queue = [vid['title'] for vid in dict_queue[self.gid]]
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
                self.queue = [vid['title'] for vid in dict_queue[self.gid]]
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
        start_index = (self.current_page - 1) * 30
        end_index = start_index + 30
        MAX_LENGTH = 70
        page_content = [
            f"{pos+1}. {title[:(MAX_LENGTH-len(str(pos)))]}"+"..."*int(len(title) > (MAX_LENGTH-len(str(pos))))
            for pos, title in enumerate(self.queue[start_index:end_index])
        ]  # cut titles length
        curr = max(0, dict_current_song[self.gid])
        if (self.current_page - 1) * 30 <= curr <= self.current_page * 30:
            page_content[curr] = f"`{page_content[curr][:MAX_LENGTH-len(queue_current)]+'...'*int(len(page_content[curr][:MAX_LENGTH]) > MAX_LENGTH-3)}{queue_current}"
        embed = discord.Embed(
            title=f"Queue Page {self.current_page}/{self.num_pages}",
            description="\n".join(page_content),
            color=EMBED_COLOR
        )
        return embed


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
        with open(file_path, 'r') as f:
            options = json.load(f)

        temp_message = message.content
        succ = False
        for prefix in options['custom_prefixes']:
            if message.content.startswith(prefix):
                if message.content[len(prefix):] in EXCLUDED_CASES: return
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
        if not any(ctx.message.content.startswith(prefix) for prefix in EXCLUDED_CASES):
            channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
            await channel_to_send.send(random.choice(not_existing_command_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)


## BOT TASKS ##
@tasks.loop(seconds=1)
async def update_current_time():
    global dict_current_time
    for guild in dict_current_time:
        dict_current_time[guild] += 1


@tasks.loop(seconds=MEMBERS_LEFT_TIMEOUT)
async def members_left():
    global loop_mode, dict_current_song, dict_current_time, disable_play, active_servers, ctx_dict
    try:
        if not ctx_dict:
            members_left.stop()
            return
        temp_ctx = ctx_dict.copy()
        for gid2 in ctx_dict:
            ctx = ctx_dict[gid2]
            voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
            if not voice_client and all(i == 0 for i in list(active_servers.values())):
                members_left.stop()
                return
            if len(voice_client.channel.members) <= 1:
                try:
                    channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
                    await channel_to_send.send(random.choice(nobody_left_texts))
                except:
                    continue
                gid = str(ctx.guild.id)
                loop_mode[gid] = loop_mode.setdefault(gid, "off")
                if loop_mode[gid] != "off": await loop(ctx, 'off')
                try:
                    await voice_client.disconnect()
                except:
                    pass
                change_active(ctx, mode='d')
                active_servers[gid] = 0
                dict_queue[gid].clear()
                del temp_ctx[gid2]
                disable_play = False
                dict_current_song[gid], dict_current_time[gid] = -1, 0
                if all(i == 0 for i in list(active_servers.values())):
                    members_left.stop()
                try:
                    [os.remove(os.path.join(DOWNLOAD_PATH, file)) for file in os.listdir(DOWNLOAD_PATH)]
                except:
                    pass
        ctx_dict = temp_ctx.copy()
        return
    except:
        traceback.print_exc()


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
async def help(ctx, comando=None):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_help"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if comando:
            if comando in ['help', 'h']:
                command_text = command_desc_help
            elif comando in ['play', 'p']:
                command_text = command_desc_play
            elif comando in ['leave', 'l', 'dis', 'disconnect', 'd']:
                command_text = command_desc_leave
            elif comando in ['skip', 's', 'next']:
                command_text = command_desc_skip
            elif comando in ['join', 'connect']:
                command_text = command_desc_join
            elif comando in ['pause', 'stop']:
                command_text = command_desc_pause
            elif comando in ['resume']:
                command_text = command_desc_resume
            elif comando in ['queue', 'q']:
                command_text = command_desc_queue
            elif comando in ['loop', 'lp']:
                command_text = command_desc_loop
            elif comando in ['shuffle', 'sf', 'random']:
                command_text = command_desc_shuffle
            elif comando in ['np', 'info', 'nowplaying', 'playing']:
                command_text = command_desc_info
            elif comando in ['lyrics', 'lyric']:
                command_text = command_desc_lyrics
            elif comando in ['songs', 'song']:
                command_text = command_desc_songs
            elif comando in ['steam']:
                command_text = command_desc_steam
            elif comando in ['remove', 'rm']:
                command_text = command_desc_remove
            elif comando in ['goto']:
                command_text = command_desc_goto
            elif comando in ['ping']:
                command_text = command_desc_ping
            elif comando in ['avatar', 'pfp', 'profile']:
                command_text = command_desc_avatar
            elif comando in ['level', 'lvl']:
                command_text = command_desc_level
            elif comando in ['chatgpt', 'chat', 'gpt']:
                command_text = command_desc_chatgpt
            elif comando in ['seek', 'sk']:
                command_text = command_desc_seek
            elif comando in ['chords']:
                command_text = command_desc_chords
            elif comando in ['genre', 'genres', 'recomm', 'recommendation', 'recommendations']:
                command_text = command_desc_genre
            elif comando in ['search', 'find']:
                command_text = command_desc_search
            elif comando in ['rewind', 'back', 'r', 'rw']:
                command_text = command_desc_rewind
            elif comando in ['forward', 'fw', 'forwards', 'bw', 'backward', 'backwards']:
                command_text = command_desc_forward
            elif comando in ['options', 'config', 'cfg', 'opt']:
                command_text = command_desc_options
            elif comando in ['fastplay', 'fp']:
                command_text = command_desc_fastplay
            elif comando in ['perms', 'prm']:
                command_text = command_desc_perms.replace("%bot_name", BOT_NAME)
            elif comando in ['add_prefix', 'prefix', 'set_prefix']:
                command_text = command_desc_add_prefix
            elif comando in ['del_prefix', 'remove_prefix', 'rem_prefix']:
                command_text = command_desc_del_prefix
            elif comando in ['add_perm']:
                command_text = command_desc_add_perm
            elif comando in ['del_perm']:
                command_text = command_desc_del_perm
            elif comando in ['available_perms']:
                command_text = command_desc_available_perms
            elif comando in ['pitch', 'tone']:
                command_text = command_desc_pitch
            elif comando in ['lang', 'change_lang', 'language', 'change_language']:
                command_text = command_desc_lang
            else:
                await channel_to_send.send(random.choice(not_existing_command_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            embed = discord.Embed(
                title=f"Command: {comando}",
                description=command_text,
                color=EMBED_COLOR
            )
        else:
            comandos = command_commands
            file_path = f'options_{ctx.guild.id}.json'
            create_options_file(file_path)
            with open(file_path, 'r') as f:
                options = json.load(f)

            embed = discord.Embed(
                title=f"{help_title}",
                description=f"{help_desc}\n{comandos}".replace("%prefix", ', '.join(
                    ['`{}`'.format(item) for item in options['custom_prefixes']])),
                color=EMBED_COLOR
            )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
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
        embed = discord.Embed(
            title=available_perms_title,
            description=f"{', '.join(['`{}`'.format(item) for item in AVAILABLE_PERMS])}",
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        embed.title = default_perms_title
        embed.description = f"{', '.join(['`{}`'.format(item) for item in DEFAULT_USER_PERMS])}"
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
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
async def leave(ctx, ignore=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        global loop_mode, dict_current_song, dict_current_time, disable_play
        if not ignore:
            if not check_perms(ctx, "use_leave"):
                await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if not ctx.author.voice:
                await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            bot_vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            if not bot_vc:
                await channel_to_send.send(random.choice(not_connected_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if ctx.author.voice.channel != bot_vc.channel:
                await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        gid = str(ctx.guild.id)
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        try:
            if voice_client is not None and voice_client.is_connected():
                await voice_client.disconnect()
        except:
            traceback.print_exc()
            pass
        if loop_mode[gid] != "off": await loop(ctx, 'off')
        change_active(ctx, mode='d')
        try:
            dict_queue[gid].clear()
        except:
            pass
        disable_play = False
        dict_current_song[gid], dict_current_time[gid] = 0, 0
    except:
        traceback.print_exc()


@bot.command(name='np', aliases=['info', 'nowplaying', 'playing'])
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
        if voice_client is not None and voice_client.is_playing():
            gid = str(ctx.guild.id)
            dict_queue.setdefault(gid, list())
            dict_current_song.setdefault(gid, 0)
            queue = dict_queue[gid]
            current_song = dict_current_song[gid]
            vid = queue[current_song]
            titulo, duracion, actual = vid['title'], convert_seconds(int(vid['length'])), convert_seconds(dict_current_time[gid])
            vid_channel = vid['channel'] if vid['channel'] else '???'
            if SPOTIFY_SECRET and SPOTIFY_ID: artista = utilidades.get_spotify_artist(titulo+vid_channel*(vid_channel != "???"), is_song=True)
            else: artista = vid_channel
            if not artista or vid['type'] == 'raw_audio': artista = vid['channel'] if vid['channel'] else '???'
            embed = discord.Embed(
                title=song_info_title,
                description=song_info_desc.replace("%title", titulo).replace("%artist", artista).replace("%channel", vid_channel)
                    .replace("%duration", str(duracion)).replace("%bar", utilidades.get_bar(int(vid['length']), dict_current_time[gid])),
                color=EMBED_COLOR
            )
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

        with open(file_path, 'r') as f:
            options = json.load(f)
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
        with open(file_path, 'r') as f:
            options = json.load(f)
        if tipo.lower() in ['youtube', 'yt', 'yotube'] or (tipo not in ['spotify', 'sp', 'spotipy', 'spoti', 'spoty']
                                                           and tipo not in ['youtube', 'yt', 'yotube']):
            try:
                results = search_youtube(query, max_results=options['search_limit'])
            except:
                traceback.print_exc()
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
        with open(file_path, 'r') as f:
            options = json.load(f)
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
    global dict_current_song, dict_current_time, disable_play, ctx_dict, vote_skip_dict
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
            voice_channel = voice_client.channel
        if voice_client:
            if voice_client.channel != voice_channel:
                await channel_to_send.send(already_on_another_vc, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
            if not voice_client.is_connected():
                await voice_channel.connect()
        else:
            await voice_channel.connect()
        if ctx.message.attachments and attachment:
            for attachment in ctx.message.attachments:
                await play(ctx, url=f"{attachment.url} -opt force", search=False, attachment=False)
        if not url: return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        change_active(ctx, mode='a')
        ctx_dict[gid] = ctx

        all_chosen = False
        if not members_left.is_running(): members_left.start()
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
                results = search_youtube(url, max_results=MAX_SEARCH_SELECT if search else 1)

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
                            if not members_left.is_running(): members_left.start()
                            return
                        if button_choice[gid] == 5:
                            button_choice[gid] = random.randint(0, len(results[(5 * (current_page - 1)):(5 * current_page)]))
                        if button_choice[gid] == 9:
                            links = results[(5 * (current_page - 1)):(5 * current_page)].copy()
                            all_chosen = True
                            await channel_to_send.send(all_selected.replace("%page", str(current_page)), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                        else:
                            chosen = min(len(results[5*(current_page-1):5*current_page])+5*(current_page-1)-1, button_choice[gid]+5*(current_page-1))
                            video_select = results[chosen]
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
                            if not members_left.is_running(): members_left.start()
                            return
                        video_select = results[emoji_to_number.get(emoji_choice, None) - 1]
                        if voice_client:
                            await channel_to_send.send(song_selected.replace("%title", video_select['title']), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                        else:
                            return
                else:
                    await search_message.delete()
                    video_select = results[0].copy()
            else:
                video_select = {
                    'obj': None, 'title': None, 'channel': None, 'length': None, 'id': None, 'thumbnail_url': None,
                    'url': url, 'type': None, 'stream_url': None, 'views': None, 'channel_url': None,
                    'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'bass': 0.0, 'high': 0.0}
                    # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
                }
        end = False
        if not all_chosen:
            vtype, vid_id = check_link_type(video_select['url'])
            not_loaded_list = []
            failed_check = False
            if vtype == 'unknown':
                try:
                    if not isinstance(url, dict):
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
                    links[0] = info_from_url(links[0])
                    if len(links) > PLAYLIST_MAX_LIMIT:
                        await channel_to_send.send(playlist_max_reached.replace("%pl_length", str(len(links))).replace("%over", str(abs(
                            PLAYLIST_MAX_LIMIT - len(links)))).replace("%discarded", str(abs(PLAYLIST_MAX_LIMIT - len(links)))))
                        links = links[:PLAYLIST_MAX_LIMIT]
                    embed_playlist = discord.Embed(
                        title=playlist_added_title,
                        description=playlist_added_desc.replace("%name", ctx.author.global_name)
                            .replace("%title", str(playlist.title)).replace("%ch_name", voice_channel.name)
                            .replace("%pl_length", str(len(links))),
                        color=EMBED_COLOR
                    )

                    def get_duration(yt):
                        return yt.length

                    videos = playlist.videos
                    if len(videos) <= PLAYLIST_TIME_LIMIT:
                        with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
                            playlist_duration = sum(executor.map(get_duration, videos))
                        sec = convert_seconds(playlist_duration)
                    else:
                        sec = ""
                    embed_playlist.add_field(
                        name=playlist_link,
                        value=playlist_link_desc.replace("%url", playlist.playlist_url).replace("%title", playlist.title) +
                              playlist_link_desc_time.replace("%duration", playlist_duration_over_limit*(len(links) > PLAYLIST_TIME_LIMIT)+str(sec))
                    )
            elif vtype == 'sp_track':
                track = sp.track(vid_id)
                links = [search_youtube(f"+{track['name']}, {' '.join([artist['name'] for artist in track['artists']])} audio", max_results=1)[0]]
            elif vtype == 'sp_album':
                def fetch_video_data(track):
                    videos = Search(f"+{track['name']}, {' '.join([artist['name'] for artist in track['artists']])} audio").results
                    video = videos[0]
                    try:
                        streaming_data = video.vid_info['streamingData']
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
                        'channel_url': video.channel_url, 'length': int(video.length), 'id': video.video_id,
                        'type': 'video', 'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'bass': 0.0, 'high': 0.0}
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
                        streaming_data = video.vid_info['streamingData']
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
                        'channel_url': video.channel_url, 'length': int(video.length), 'id': video.video_id,
                        'type': 'video', 'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'bass': 0.0, 'high': 0.0}
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
                links = [url]
            if vtype in {'video', 'live'}:
                if not isinstance(url, dict):
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
        if vtype != 'raw_audio':
            if vid['length'] > MAX_VIDEO_LENGTH:
                await channel_to_send.send(video_max_duration.replace("%video_limit", str(convert_seconds(MAX_VIDEO_LENGTH))),
                               reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                await skip(ctx)
                return
            titulo, duracion = vid['title'], convert_seconds(int(vid['length']))
            if vid['type'] == 'live': duracion = 'LIVE'
            embed = discord.Embed(
                title=song_chosen_title,
                description=song_chosen_desc.replace("%name", ctx.author.global_name).replace("%title", titulo).replace(
                    "%ch_name", voice_channel.name),
                color=EMBED_COLOR
            )
            embed2 = discord.Embed(
                title=added_queue_title,
                description=added_queue_desc.replace("%url", vid['url']).replace("%title", titulo).replace("%duration",
                                                                                                         str(duracion)),
                color=EMBED_COLOR
            )
            embed.add_field(name=playing_title,
                            value=playing_desc.replace("%url", vid['url']).replace("%title", titulo).replace("%duration", str(duracion)),
                            inline=False)
            img = None
            if gif and TENOR_API_KEY: img = search_gif(titulo, TENOR_API_KEY)
            if not img: img = vid['thumbnail_url']
            if gif:
                embed.set_image(url=img)
                embed2.set_image(url=img)
            else:
                embed.set_thumbnail(url=img)
                embed2.set_thumbnail(url=img)
            if vid['stream_url']:
                if vtype == 'playlist':
                    await channel_to_send.send(embed=embed_playlist, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                elif voice_client is not None and voice_client.is_playing() and not silent:
                    await channel_to_send.send(embed=embed2, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                else:
                    dict_current_time[gid] = 0
                    if not silent: await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)

            else:
                await channel_to_send.send(content=random.choice(rip_audio_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
                return
        else:
            dict_current_time[gid] = 0
            raw_embed = discord.Embed(
                title=song_chosen_title,
                description=raw_audio_desc.replace("%name", ctx.author.global_name).replace("%ch_name", voice_client.channel.name),
                color=EMBED_COLOR
            )
            await channel_to_send.send(embed=raw_embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        if not update_current_time.is_running(): update_current_time.start()
        if append:
            dict_queue[gid] = dict_queue.setdefault(gid, list())
            dict_current_song[gid] = dict_current_song.setdefault(gid, 0)
            if vtype == 'raw_audio':
                for video in links: dict_queue[gid].append({
                    'obj': None, 'title': 'Raw audio file', 'channel': 'Someone', 'views': 'No views',
                    'length': 0, 'id': 'none', 'thumbnail_url': None, 'url': video, 'stream_url': video,
                    'channel_url': None, 'type': 'raw_audio',
                    'audio_options': {'pitch': 1.0, 'speed': 1.0, 'volume': 0.0, 'bass': 0.0, 'high': 0.0}
                    # pitch as freq multiplier, speed as tempo multiplier, volume/bass/high in dB
                })
            else:
                for video in links: dict_queue[gid].append(video)
        # LVL HANDLE
        await update_level_info(ctx, ctx.author.id, LVL_PLAY_ADD)
        vote_skip_dict[gid] = -1
        if voice_client and not voice_client.is_paused():
            try:
                if not voice_client.is_playing():
                    updated_options = FFMPEG_OPTIONS.copy()
                    if isinstance(url, dict):  # means song was already loaded, aka could have been changed in volume, pitch, etc
                        updated_options['options'] += f' -filter:a "rubberband=pitch={vid["audio_options"]["pitch"]}, ' \
                                                      f'rubberband=tempo={vid["audio_options"]["speed"]}, ' \
                                                      f'volume={vid["audio_options"]["volume"]}dB"'
                    voice_client.play(discord.FFmpegPCMAudio(vid['stream_url'] if vtype != 'raw_audio' else url, **updated_options), after=lambda e: on_song_end(ctx, e))
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
        global dict_current_song, dict_current_time
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
        queue.pop(index)
        await channel_to_send.send(removed_from_queue.replace("%title", vid['title']), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        dict_current_time[gid] = 0
        if index == current_song:
            dict_current_song[gid] = current_song - 2 if current_song > 1 else -1
            await skip(ctx)
        elif index < current_song:
            dict_current_song[gid] = current_song - 1
    except Exception as e:
        traceback.print_exc()


@bot.command(name='forward', aliases=['fw', 'forwards', 'bw', 'backward', 'backwards'])
async def forward(ctx, time):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_forward"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_current_time, seek_called, dict_queue, dict_current_song
        if not ctx.author.voice:
            await channel_to_send.send(random.choice(not_in_vc_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if not voice_client or not voice_client.is_playing() or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if voice_client is not None and ctx.author.voice.channel != voice_client.channel:
            await channel_to_send.send(random.choice(different_channel_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[current_song]
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
        dict_current_time[gid] += time
        if dict_current_time[gid] > vid['length'] and not vid['type'] == 'raw_audio':
            await skip(ctx)
            return
        if dict_current_time[gid] < 0: dict_current_time[gid] = 0
        seek_called = True
        if voice_client.is_paused(): voice_client.resume()
        voice_client.stop()
        updated_options = FFMPEG_OPTIONS.copy()
        updated_options['options'] += f' -filter:a "rubberband=pitch={vid["audio_options"]["pitch"]}, ' \
                                      f'rubberband=tempo={vid["audio_options"]["speed"]}, ' \
                                      f'volume={vid["audio_options"]["volume"]}dB"'
        updated_options['before_options'] += f' -ss {dict_current_time[gid]}'
        voice_client.play(
                discord.FFmpegPCMAudio(vid['stream_url'], **updated_options),
            after=lambda e: on_song_end(ctx, e))

        duracion, actual = convert_seconds(int(vid['length'])), convert_seconds(dict_current_time[gid])
        modetype = fast_forwarding if time >= 0 else rewinding
        embed = discord.Embed(
            title=forward_title.replace("%modetype", modetype).replace("%sec", str(convert_seconds(abs(time)))).replace(
                "%time", str(actual)),
            description=f"{utilidades.get_bar(int(vid['length']), dict_current_time[gid])}",
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
        global dict_current_time, seek_called, dict_queue, dict_current_song
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
        if not voice_client or not voice_client.is_playing() or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        vid = queue[current_song]
        if vid['type'] == 'live':
            await channel_to_send.send(cannot_change_time_live.replace("%command", "seek"), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if str(time).isnumeric():
            time = int(time)
            if time < 0: time = 0
            if time > vid['length'] and not vid['type'] == 'raw_audio':
                await skip(ctx)
                return
            dict_current_time[gid] = time
        else:
            dict_current_time[gid] = int(convert_formated(time))
        seek_called = True
        if voice_client.is_paused(): voice_client.resume()
        voice_client.stop()
        updated_options = FFMPEG_OPTIONS.copy()
        updated_options['options'] += f' -filter:a "rubberband=pitch={vid["audio_options"]["pitch"]}, ' \
                                      f'rubberband=tempo={vid["audio_options"]["speed"]}, ' \
                                      f'volume={vid["audio_options"]["volume"]}dB"'
        updated_options['before_options'] += f' -ss {dict_current_time[gid]}'
        voice_client.play(
            discord.FFmpegPCMAudio(vid['stream_url'], **updated_options),
            after=lambda e: on_song_end(ctx, e))

        duracion, actual = convert_seconds(int(vid['length'])), convert_seconds(dict_current_time[gid])
        embed = discord.Embed(
            title=seek_title.replace("%time", str(actual)),
            description=f"{utilidades.get_bar(int(vid['length']), dict_current_time[gid])}",
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)

    except:
        traceback.print_exc()
        await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)


@bot.command(name='loop', aliases=['lp'])
async def loop(ctx, mode="change"):
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
        if mode == "change": mode = "all" if loop_mode[gid] == "off" else "off"
        if mode not in ['queue', 'all', 'shuffle', 'random', 'one', 'off']:
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
        global dict_current_song, dict_current_time
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
        if update_current_time.is_running(): update_current_time.stop()
        dict_current_time[gid] = 0
        await skip(ctx)
        return True
    except:
        traceback.print_exc()


@bot.command(name='queue', aliases=['q'])
async def cola(ctx, silent=False):
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
        with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
            gids = [gid for _ in range(len(queue))]
            executor.map(get_video_info, queue, gids)
        print("Queue processed.")
        if not silent:
            num_pages = (len(queue) - 1) // 30 + 1
            title_queue = [vid['title'] for vid in queue]
            view = QueueMenu(title_queue, num_pages, ctx, gid)
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
        if not voice_client or not voice_client.is_playing() or not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        voice_client.pause()
        if update_current_time.is_running(): update_current_time.stop()
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
        if not update_current_time.is_running(): update_current_time.start()
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
                majority = round(member_amount / 2)
                vote_message = await channel_to_send.send(vote_skip_text.replace("%num", str(majority)))
                await vote_message.add_reaction("❌")
                await vote_message.add_reaction("✅")
                await asyncio.sleep(1)
                vote_skip_dict[gid], vote_skip_counter[gid] = 0, 0
                message_id_dict[gid], majority_dict[gid] = vote_message.id, [majority, list(
                    user.id for user in voice_client.channel.members)]
                ctx_dict_skip[gid] = ctx
                vote_skip.start()
        if vote_skip_dict[gid] == 0: return
        vote_skip_dict[gid], vote_skip_counter[gid] = -1, 0
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] == 'one': loop_mode[gid] = 'off'
        if voice_client.is_paused(): voice_client.resume()
        if voice_client.is_playing(): voice_client.stop()
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


@bot.command(name="avatar", aliases=['profile', 'pfp'])
async def avatar(ctx):
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
            description=f'{url}',
            color=EMBED_COLOR
        )
        imgurl = utilidades.get_steam_avatar(url)
        if not imgurl:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        embed.set_image(url=imgurl)
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='chatgpt', aliases=['chat', 'gpt'])
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
            titulo = queue[current_song]['title']
        else:
            titulo = query
        artista = utilidades.get_spotify_artist(titulo, is_song=True)
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


@bot.command(name='songs', aliases=['song'])
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
            query = queue[current_song]['title']
        elif not query:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        artista, cancion = utilidades.get_artist_and_song(query)

        if not traspose: traspose = 0
        try: traspose = int(traspose)
        except: traspose = 0
        msg, tuning_info = utilidades.get_chords_and_lyrics(query, traspose=traspose)
        if not msg:
            msg = await utilidades.search_cifraclub(query)
        if not msg:
            await channel_to_send.send(random.choice(couldnt_complete_search_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
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
        await channel_to_send.send(embed=tuning_embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        for i in range(0, len(msg), 4000):
            embed = discord.Embed(
                title="",
                description=msg[i:i + 4000],
                color=EMBED_COLOR
            )
            if i == 0: embed.title = chords_title.replace("%song", cancion).replace("%artist", artista)

            await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='nightcore', aliases=['spedup'])
async def nightcore(ctx):
    try:
        await pitch(ctx, semitones=4, speed=1+4/12, silent=True)
    except:
        traceback.print_exc()


@bot.command(name='daycore', aliases=['slowed'])
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
        global dict_queue, dict_current_song, dict_current_time
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
        if not semitones: semitones = 0  # return to default
        pitch_factor = min(max(0.01, 2**((float(semitones))/12)), 2)
        vid['audio_options']['pitch'] = pitch_factor
        vid['audio_options']['speed'] = speed
        updated_options = FFMPEG_OPTIONS.copy()
        updated_options['before_options'] += f' -ss {dict_current_time[gid]}'
        updated_options['options'] += f' -filter:a "rubberband=pitch={vid["audio_options"]["pitch"]}, ' \
                                      f'rubberband=tempo={vid["audio_options"]["speed"]}, ' \
                                      f'volume={vid["audio_options"]["volume"]}dB, ' \
                                      f'equalizer=f=120:width_type=q:width=3:g={vid["audio_options"]["bass"]}, ' \
                                      f'equalizer=f=8000:width_type=q:width=2:g={vid["audio_options"]["high"]}"'
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
        global dict_queue, dict_current_song, dict_current_time
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
        vid['audio_options']['volume'] = vol_db
        updated_options = FFMPEG_OPTIONS.copy()
        updated_options['before_options'] += f' -ss {dict_current_time[gid]}'
        updated_options['options'] += f' -filter:a "rubberband=pitch={vid["audio_options"]["pitch"]}, ' \
                                      f'rubberband=tempo={vid["audio_options"]["speed"]}, ' \
                                      f'volume={vid["audio_options"]["volume"]}dB, ' \
                                      f'equalizer=f=120:width_type=q:width=3:g={vid["audio_options"]["bass"]}, ' \
                                      f'equalizer=f=8000:width_type=q:width=2:g={vid["audio_options"]["high"]}"'
        voice_client.play(discord.FFmpegPCMAudio(queue[current_song]['stream_url'], **updated_options),
                              after=lambda e: on_song_end(ctx, e))
        embed = discord.Embed(
            title=volume_title,
            description=volume_desc.replace("%vol", f"{vol_db:.2f}dB"),
            color=EMBED_COLOR
        )
        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='eq', aliases=['equalizer'])
async def eq(ctx, eqtype="bass", strength="5", silent=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_eq"):
            await channel_to_send.send(random.choice(insuff_perms_texts),
                                       reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song, dict_current_time
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
        updated_options = FFMPEG_OPTIONS.copy()
        updated_options['before_options'] += f' -ss {dict_current_time[gid]}'
        updated_options['options'] += f' -filter:a "rubberband=pitch={vid["audio_options"]["pitch"]}, ' \
                                      f'rubberband=tempo={vid["audio_options"]["speed"]}, ' \
                                      f'volume={vid["audio_options"]["volume"]}dB, ' \
                                      f'equalizer=f=300:width_type=h:width=120:g={vid["audio_options"]["bass"]}, ' \
                                      f'equalizer=f=8000:width_type=h:width=3000:g={vid["audio_options"]["high"]}"'
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


@bot.command(name='shazam', aliases=['recognize', 'thissong', 'current', 'this', 'currentsong'])
async def shazam(ctx, clip_length = '15'):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_shazam"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song, dict_current_time
        gid = str(ctx.guild.id)
        dict_queue.setdefault(gid, list())
        dict_current_song.setdefault(gid, 0)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if not queue:
            await channel_to_send.send(random.choice(nothing_on_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        dict_current_time.setdefault(gid, 0)
        start_time = dict_current_time[gid]
        vid = queue[current_song]
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
                .replace("%url", recognized_song['url']).replace("%genres", genres).replace("%plural", "s" if plural else "").replace("%album", album_info),
            color=EMBED_COLOR
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


@bot.command(name='auto', aliases=['autodj', 'autoplaylist', 'autopl'])
async def autodj(ctx, *, url="", ignore=False):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_autodj"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        global dict_queue, dict_current_song, dict_current_time, loop_mode
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
        start_time = dict_current_time[gid]
        vid = queue[current_song-int(1*ignore)]
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
        queue_titles = [vid['title'] for vid in queue]
        song_count = 0
        for track in tracks:
            if song_count >= AUTO_DJ_MAX_ADD: break
            try:
                query = f"+{track['title']}, {track['subtitle']} audio"
                if not process.extractOne(query, queue_titles)[1] >= 88:
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

        with open(file_path, 'r') as f:
            options = json.load(f)

        if prefix not in options['custom_prefixes']: options['custom_prefixes'].append(prefix)

        embed = discord.Embed(
            title=prefix_add_title,
            description=prefix_add_desc.replace("%prefix", prefix).replace("%prefixes",
                                                                           ' '.join(options['custom_prefixes'])),
            color=EMBED_COLOR
        )

        with open(file_path, 'w') as f:
            json.dump(options, f)

        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='remove_prefix', aliases=['del_prefix', 'rem_prefix'])
async def del_prefix(ctx, prefix):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_del_prefix"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        gid = str(ctx.guild.id)
        file_path = f'options_{gid}.json'
        create_options_file(file_path)

        with open(file_path, 'r') as f:
            options = json.load(f)
        if prefix in options['custom_prefixes']: options['custom_prefixes'].remove(prefix)

        embed = discord.Embed(
            title=prefix_del_title,
            description=prefix_del_desc.replace("%prefix", prefix).replace("%prefixes",
                                                                           ' '.join(options['custom_prefixes'])),
            color=EMBED_COLOR
        )

        with open(file_path, 'w') as f:
            json.dump(options, f)

        await channel_to_send.send(embed=embed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
    except:
        traceback.print_exc()


@bot.command(name='lang', aliases=['language', 'change_lang', 'change_language'])
async def lang(ctx, lng=None):
    try:
        channel_to_send, CAN_REPLY = get_channel_restriction(ctx)
        if not check_perms(ctx, "use_lang"):
            await channel_to_send.send(random.choice(insuff_perms_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return
        if not lng or lng.lower() not in ['es', 'en']:
            await channel_to_send.send(random.choice(invalid_use_texts), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
            return

        with open(f"lang/{lng.lower()}.json", "r") as f:
            lang_dict = json.load(f)

        config.set("Config", "lang", lng.lower())
        with open(config_path, "w") as f:
            config.write(f)

        globals().update(lang_dict)

        await channel_to_send.send(lang_changed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
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
                await options(ctx, option="restricted_to", query=name, ignore=True)
                await channel_to_send.send(restricted_to_channel.replace("%name", name), reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
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
        global dict_queue, dict_current_song, dict_current_time

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
        dict_current_time[gid] = 0
        queue.reverse()
        await skip(ctx)
        await channel_to_send.send(queue_reversed, reference=ctx.message if REFERENCE_MESSAGES and CAN_REPLY else None)
        return 1
    except:
        traceback.print_exc()


bot.run(DISCORD_APP_KEY)
