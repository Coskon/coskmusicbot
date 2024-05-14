import discord
import asyncio
import requests
import utilidades
import librosa
import subprocess
import soundfile as sf
import numpy as np
import os, random, re, json, traceback, time, ast
from discord.ext import commands, tasks
from pytube import YouTube, exceptions, Search, Playlist
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

## BOT INITIALIZATION ##
intents = discord.Intents.default()
intents.voice_states, intents.message_content, intents.members = (True for _ in range(3))
activity = discord.Activity(type=discord.ActivityType.listening, name=".play")

## PARAMETER VARIABLES ##
with open(r'PARAMETERS.txt', 'r') as f:
    lines = f.readlines()

var_values = []
for line in lines:
    if line == "\n": continue
    var_values.append(line[:line.find("#")].split("=")[1].strip())

BOT_NAME = str(var_values[0])  # name of your bot
MAX_VIDEO_LENGTH = int(var_values[1])  # in seconds
PLAYLIST_MAX_LIMIT = int(var_values[2])  # max videos on playlist
PLAYLIST_TIME_LIMIT = int(var_values[3])  # max videos to see their total duration
TIMELIMIT = int(var_values[4])  # (in seconds) timelimit for the popup of the search choice embed
REQUEST_LIMIT = float(var_values[5])  # (in seconds) time should pass between command calls from each user
MEMBERS_LEFT_TIMEOUT = int(var_values[6])  # (in seconds) time between each check for members left
EMBED_COLOR = int(var_values[7], 16)  # color for the side of the embed
DEFAULT_SEARCH_LIMIT = int(var_values[8])  # how many videos to show using the search command by default
DEFAULT_RECOMMENDATION_LIMIT = int(var_values[9])  # how many videos to show in recommendations by default
LVL_PLAY_ADD = int(var_values[10])  # how much to add per play command called
LVL_NEXT_XP = int(var_values[11])  # how much required xp added per next level
LVL_BASE_XP = int(var_values[12])
NUM_THREADS_HIGH = int(var_values[13])  # number of threads to use for tasks that need high performance
NUM_THREADS_LOW = int(var_values[14])  # number of threads to use for tasks that don't need as much performance
USE_LOGIN = bool(var_values[15].capitalize())
DOWNLOAD_PATH = str(var_values[16])  # download output folder
DEFAULT_PREFIXES = ast.literal_eval(var_values[17])  # prefixes to use by default
EXCLUDED_CASES = ast.literal_eval(var_values[18])  # list of cases to exclude from being recognized as commands
AVAILABLE_PERMS = ast.literal_eval(var_values[19])  # all permissions available
DEFAULT_USER_PERMS = ast.literal_eval(var_values[20])  # permissions each user gets by default
ADMIN_PERMS = ast.literal_eval(var_values[21])  # permissions admin users get by default

# The bot will send these texts (will randomly select if there are multiple texts in the list)
already_connected_texts = ["I'm already connected.", "I'm already here."]
entering_texts = ["Entering ", "Going into "]
nothing_on_texts = ["Nothing is playing."]
song_not_chosen_texts = ["No song chosen in `30` seconds..."]
not_existing_command_texts = ["Invalid command."]
nobody_left_texts = ["Nobody left, disconnecting..."]
invalid_use_texts = ["Invalid use (check `help` for more info)."]
prefix_use_texts = ["To add or remove a prefix, use `add_prefix [prefix]` or `del_prefix [prefix]`."]
couldnt_complete_search_texts = ["Couldn't complete search."]
not_in_vc_texts = ["You are not in a voice channel."]
private_channel_texts = ["I can't enter that channel."]
cancel_selection_texts = ["Selection canceled."]
invalid_link_texts = ["Invalid link."]
restricted_video_texts = ["Invalid video (private or age restricted)."]
rip_audio_texts = ["Audio error."]
no_queue_texts = ["There are no songs in the queue."]
avatar_error_texts = ["Couldn't retrieve profile picture."]
no_api_credits_texts = ["No API Credits to use this."]
lyrics_too_long_texts = ["The lyrics are too long."]
no_game_texts = ["Game not available."]
no_api_key_texts = ["This function is disabled."]
insuff_perms_texts = ["You don't have permission to do this."]

## API KEYS ##
with open('API_KEYS.txt', 'r') as f:
    DISCORD_APP_KEY = f.read().split("\n")[0].split("=")[1]
if not DISCORD_APP_KEY:
    print("\033[91mDISCORD_APP_KEY not found. Go into 'API_KEYS.txt' to set it.\033[0m")
    raise Exception
TENOR_API_KEY = utilidades.TENOR_API_KEY
OPENAI_KEY = utilidades.OPENAI_API_KEY
GENIUS_ACCESS_TOKEN = utilidades.GENIUS_ACCESS_TOKEN
SPOTIFY_ID = utilidades.SPOTIFY_ID
SPOTIFY_SECRET = utilidades.SPOTIFY_SECRET

## GLOBAL VARIABLES ##
dict_queue, active_servers, ctx_dict = dict(), dict(), dict()
user_cooldowns = {}
loop_mode = "off"
dict_current_song, dict_current_time = dict(), dict()
go_back, seek_called, disable_play = (False for _ in range(3))


## NORMAL FUNCTIONS ##
def is_url(input_string):
    try:
        result = urlsplit(input_string)
        return bool(result.scheme)
    except ValueError:
        return False


def search_gif(query):
    query = re.sub(r'[^a-zA-Z0-9 ]', '', query)
    query = str(query).replace(' ', '+').replace('shorts', '')

    try:
        r = requests.get(f"https://tenor.googleapis.com/v2/search?q={query}&key={TENOR_API_KEY}&limit=1")
        if r.status_code == 200:
            if not json.loads(r.content)['results']: return None
            return json.loads(r.content)['results'][0]['media_formats']['mediumgif']['url']
        else:
            return None

    except requests.RequestException as e:
        print(f"Error making API request: {e}")
        return None


def convert_seconds(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours == 0:
        return "{:0}:{:02d}".format(int(minutes), int(seconds))
    else:
        return "{:0}:{:02d}:{:02d}".format(int(hours), int(minutes), int(seconds))


def convert_formated(time_str):
    time_components = time_str.split(':')
    num_components = len(time_components)
    hours = 0
    if num_components == 3:
        hours = int(time_components[0])
        minutes = int(time_components[1])
        seconds = int(time_components[2])
    elif num_components == 2:
        minutes = int(time_components[0])
        seconds = int(time_components[1])
    else:
        raise ValueError("Invalid time format. Please use either HH:MM:SS or MM:SS.")
    return hours * 3600 + minutes * 60 + seconds


def check_link_type(link):
    try:
        playlist = Playlist(link)
        return 'playlist', playlist.title
    except:
        try:
            video = YouTube(link, use_oauth=USE_LOGIN, allow_oauth_cache=True)
            return 'video', video.title
        except:
            return 'unknown', None


def get_playlist_videos(link):
    try:
        playlist = Playlist(link)
        video_urls = [video.watch_url for video in playlist.videos]
        return video_urls
    except Exception as e:
        print(f"Error: {e}")
        return []


def get_playlist_total_duration_seconds(links):
    try:
        def get_video_duration(video_url):
            try:
                yt = YouTube(video_url, use_oauth=USE_LOGIN, allow_oauth_cache=True)
                return yt.length
            except Exception as e:
                print(f"Error processing {video_url}: {e}")
                return 0

        with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
            durations = list(executor.map(get_video_duration, links))

        total_duration_seconds = sum(durations)
        return total_duration_seconds

    except Exception as e:
        print(f"Error: {e}")
        return None


def find_file(folder_path, file_name):
    for filename in os.listdir(folder_path):
        if filename.startswith(file_name) and os.path.isfile(os.path.join(folder_path, filename)):
            return filename
    return None


def create_options_file(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({"search_limit": DEFAULT_SEARCH_LIMIT, "recomm_limit": DEFAULT_RECOMMENDATION_LIMIT,
                       "custom_prefixes": DEFAULT_PREFIXES}, f)


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


def on_song_end(ctx, error):
    global dict_current_song, go_back, seek_called, loop_mode
    if error:
        print(f"Error in on_song_end: {error}")
    if seek_called:
        seek_called = False
    else:
        gid = str(ctx.guild.id)
        if loop_mode == 'one':
            pass
        elif go_back:
            dict_current_song[gid] -= 1
        else:
            dict_current_song[gid] += 1
        go_back = False
        if update_current_time.is_running(): update_current_time.stop()
        bot.loop.create_task(play_next(ctx))


def get_video_info(url):
    try:
        return YouTube(url).title
    except Exception as e:
        traceback.print_exc()


def cut_string(input_string, max_length):
    if len(input_string) <= max_length:
        return input_string

    newline_position = input_string.rfind('\n', 0, max_length)
    cut_position = newline_position if newline_position != -1 else max_length

    return input_string[:cut_position], input_string[cut_position:]


def format_title(title):
    new_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)
    return new_title.replace(" ", "_") if new_title != '' else 'NoTitle'


def change_active(ctx, mode="a"):
    global active_servers
    active_servers[str(ctx.guild.id)] = 1 if mode == "a" else 0
    print(f"{'active on' if mode == 'a' else 'left'} {ctx.guild.name}")


def check_perms(ctx, perm):
    file_path = f'user_perms_{ctx.guild.id}.json'
    create_perms_file(ctx, file_path)
    with open(file_path, 'r') as f:
        user_perms = json.load(f)
    if perm not in user_perms[str(ctx.author.id)]:
        return False
    return True


## ASYNC FUNCTIONS ##
async def choice(ctx, embed, reactions):
    try:
        message = await ctx.send(embed=embed, reference=ctx.message)
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
            await ctx.send(random.choice(song_not_chosen_texts), reference=ctx.message)
            return
    except:
        traceback.print_exc()


async def play_next(ctx):
    global dict_current_song, loop_mode
    gid = str(ctx.guild.id)
    queue = dict_queue[gid]
    current_song = dict_current_song[gid]
    if current_song < 0: dict_current_song[gid] = 0
    if current_song >= len(queue):
        if loop_mode in ['queue', 'all']:
            dict_current_song[gid] = 0
        elif loop_mode in ['random', 'shuffle']:
            dict_current_song[gid] = random.randint(0, len(queue) - 1)
        else:
            await leave(ctx)
    if queue:
        url = queue[dict_current_song[gid]]
        await ctx.invoke(bot.get_command('play'), url=url, append=False)


bot = commands.Bot(command_prefix=DEFAULT_PREFIXES, activity=activity, intents=intents, help_command=None,
                   case_insensitive=True)


## BOT EVENTS ##
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


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
                message.content = '.' + message.content[len(prefix):]
                print(f'\033[92m>>> Command from {message.author}: {message.content}\033[0m')
                if message.author.id in user_cooldowns:
                    curr_time = time.time()
                    cooldown_time = user_cooldowns[message.author.id]
                    time_elapsed = curr_time - cooldown_time
                    if time_elapsed < REQUEST_LIMIT:
                        await message.channel.send(
                            f"{message.author.mention}, wait `{round(REQUEST_LIMIT - time_elapsed, 1)}` seconds.")
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
            await ctx.send(random.choice(not_existing_command_texts), reference=ctx.message)


## BOT TASKS ##
@tasks.loop(seconds=1)
async def update_current_time(ctx):
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
            if not ctx.voice_client and all(i == 0 for i in list(active_servers.values())):
                members_left.stop()
                return
            if len(ctx.voice_client.channel.members) <= 1:
                await ctx.send(random.choice(nobody_left_texts))
                if loop_mode != "off": await loop(ctx, 'off')
                await ctx.voice_client.disconnect()
                change_active(ctx, mode='d')
                gid = str(ctx.guild.id)
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


## BOT COMMANDS ##
@bot.command(name='help', aliases=['h'])
async def help(ctx, comando=None):
    try:
        if not check_perms(ctx, "use_help"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if comando:
            if comando in ['help', 'h']:
                command_text = f"➤ Use: `help [nothing/command]`\n➤ Aliases: `h`\n" \
                               f"➤ Description: Shows all commands, if a command is given it shows more info about it."
            elif comando in ['play', 'p']:
                command_text = f"➤ Use: `play [query or url] [nothing/---1]`\n➤ Aliases: `p`\n" \
                               f"➤ Description: Plays the given song. If ---1 is added at the end, a gif is added (try it!)."
            elif comando in ['leave', 'l', 'dis', 'disconnect', 'd']:
                command_text = f"➤ Use: `leave`\n➤ Aliases: `l`, `dis`, `disconnect`, `d`\n" \
                               f"➤ Description: Disconnects the bot from the voice channel and clears the queue."
            elif comando in ['skip', 's', 'next']:
                command_text = f"➤ Use: `skip`\n➤ Aliases: `s`, `next`\n" \
                               f"➤ Description: Skips to the next song."
            elif comando in ['join', 'connect']:
                command_text = f"➤ Use: `join`\n➤ Aliases: `connect`\n" \
                               f"➤ Description: Connects to the voice channel."
            elif comando in ['pause', 'stop']:
                command_text = f"➤ Use: `pause`\n➤ Aliases: `stop`\n" \
                               f"➤ Description: Pauses the song."
            elif comando in ['resume']:
                command_text = f"➤ Use: `resume`\n" \
                               f"➤ Description: Resumes the song."
            elif comando in ['queue', 'q']:
                command_text = f"➤ Use: `queue`\n➤ Aliases: `q`\n" \
                               f"➤ Description: Shows the song queue."
            elif comando in ['loop', 'lp']:
                command_text = f"➤ Use: `loop [all/queue/shuffle/random/off]`\n➤ Aliases: `lp`\n" \
                               f"➤ Description: Changes the loop mode; `all/queue` repeats the whole queue, " \
                               f"`shuffle/random` randomize the next song when the current one is finished, " \
                               f"`one` repeats the current song, `off` disables the loop."
            elif comando in ['shuffle', 'sf', 'random']:
                command_text = f"➤ Use: `shuffle`\n➤ Aliases: `sf`, `random`\n" \
                               f"➤ Description: Randomizes the queue, then goes to the first song."
            elif comando in ['np', 'info', 'nowplaying', 'playing']:
                command_text = f"➤ Use: `np`\n➤ Aliases: `info`, `nowplaying`, `playing`\n" \
                               f"➤ Description: Shows information of the current song."
            elif comando in ['lyrics', 'lyric']:
                command_text = f"➤ Use: `lyrics [nothing/song name]`\n➤ Aliases: `lyric`\n" \
                               f"➤ Description: Shows the lyrics of the current playing song, if given a name of a song " \
                               f"it shows the lyrics to that song."
            elif comando in ['songs', 'song']:
                command_text = f"➤ Use: `songs [nothing/NUM] [artist]`\n➤ Aliases: `song`\n" \
                               f"➤ Description: Shows the top NUM songs of the given artist (10 if no NUM provided)." \
                               f" If no artist is provided, it retrieves it from the current playing song."
            elif comando in ['steam']:
                command_text = f"➤ Use: `steam [user]`\n➤ Description: Shows the steam profile of the given user."
            elif comando in ['remove', 'rm']:
                command_text = f"➤ Use: `remove [song number]`\n➤ Aliases: `rm`" \
                               f"➤ Description: Removes the given song from the queue (use `queue` to see the songs and their numbers)."
            elif comando in ['goto']:
                command_text = f"➤ Use: `goto [song number]`\n➤ Description: Goes to the chosen song."
            elif comando in ['ping']:
                command_text = f"➤ Use: `ping`\n➤ Description: Shows the bot latency."
            elif comando in ['avatar', 'pfp', 'profile']:
                command_text = f"➤ Use: `avatar`\n➤ Aliases: `pfp`, `profile`\n" \
                               f"➤ Description: Shows your profile picture (HD)."
            elif comando in ['level', 'lvl']:
                command_text = f"➤ Use: `level`\n➤ Aliases: `lvl`\n" \
                               f"➤ Description: Shows your level."
            elif comando in ['chatgpt', 'chat', 'gpt']:
                command_text = f"➤ Use: `chatgpt [message]`\n➤ Aliases: `chat`, `gpt`\n" \
                               f"➤ Description: Answers with ChatGPT your message."
            elif comando in ['seek', 'sk']:
                command_text = f"➤ Use: `seek [time]`\n➤ Aliases: `sk`\n" \
                               f"➤ Description: Goes to the given time. Time should be given in seconds or in format HH:MM:SS."
            elif comando in ['chords']:
                command_text = f"➤ Use: `chords [nothing/song]`\n" \
                               f"➤ Description: Shows the chords of the current song, if given a song it shows the chords to that song."
            elif comando in ['genre', 'genres', 'recomm', 'recommendation', 'recommendations']:
                command_text = f"➤ Use: `genre [nothing/genre]`\n➤ Aliases: `genres`, `recomm`, `recommendation`, `recommendations`\n" \
                               f"➤ Description: Shows songs of the given genre, if nothing (or available) is put, shows the list of genres."
            elif comando in ['search', 'find']:
                command_text = f"➤ Use: `search [nothing/youtube/spotify] [query]`\n➤ Aliases: `find`\n" \
                               f"➤ Description: Searches in youtube (default) or spotify the given query and shows the results."
            elif comando in ['rewind', 'back', 'r', 'rw']:
                command_text = f"➤ Use: `rewind`\n➤ Aliases: `rw`, `r`, `back`\n" \
                               f"➤ Description: Goes back to the previous song."
            elif comando in ['forward', 'fw', 'forwards', 'bw', 'backward', 'backwards']:
                command_text = f"➤ Use: `forward [time]`\n➤ Aliases: `fw`, `forwards`, `bw`, `backward`, `backwards`\n" \
                               f"➤ Description: Fast forwards or rewinds the song (depending if the time is positive/negative). " \
                               f"Time should be given in seconds or in format HH:MM:SS."
            elif comando in ['options', 'config', 'cfg', 'opt']:
                command_text = f"➤ Use: `config [nothing/option] [value]`\n➤ Aliases: `options`, `opt`, `cfg`\n" \
                               f"➤ Description: Changes the value of the given option to the given value, if no option is given, " \
                               f"shows the list of options."
            elif comando in ['fastplay', 'fp']:
                command_text = f"➤ Use: `fastplay [song name or url]`\n➤ Aliases: `fp`\n" \
                               f"➤ Description: Plays a song without having to choose."
            elif comando in ['perms', 'prm']:
                command_text = f"➤ Use: `perms`\n➤ Aliases: `prm`\n" \
                               f"➤ Description: Shows {BOT_NAME} (the bot) current permissions in the server."
            elif comando in ['add_prefix', 'prefix', 'set_prefix']:
                command_text = f"➤ Use: `add_prefix [prefix]`\n➤ Aliases: `prefix`, `set_prefix`\n" \
                               f"➤ Description: Adds the given prefix to use it for commands."
            elif comando in ['del_prefix', 'remove_prefix', 'rem_prefix']:
                command_text = f"➤ Use: `del_prefix [prefix]`\n➤ Aliases: `remove_prefix`, `rem_prefix`\n" \
                               f"➤ Description: Removes the given prefix."
            elif comando in ['add_perm']:
                command_text = f"➤ Use: `add_perm [name/ALL] [permission]`\n" \
                               f"➤ Description: Adds the given permission to the specified user (or all users)."
            elif comando in ['del_perm']:
                command_text = f"➤ Use: `del_perm [name/ALL] [permission]`\n" \
                               f"➤ Description: Removes the given permission from the specified user (or all users)."
            elif comando in ['available_perms']:
                command_text = f"➤ Use: `available_perms`\n" \
                               f"➤ Description: Shows the available permissions and the ones that are given by default to" \
                               f" all users (admins get all permissions)."
            elif comando in ['pitch', 'tone']:
                command_text = f"➤ Use: `pitch [semitones]`\n➤ Aliases: `tone`\n" \
                               f"➤ Description: Changes the pitch of the current song in the given semitones. " \
                               f"(positive: higher pitch, negative: lower pitch)."
            else:
                await ctx.send(random.choice(not_existing_command_texts), reference=ctx.message)
                return
            embed = discord.Embed(
                title=f"Command: {comando}",
                description=command_text,
                color=EMBED_COLOR
            )
        else:
            comandos = "➤ `help [nothing/command] (h)`\n➤ `play [query or url] [nothing/---1] (p)`\n" \
                       "➤ `leave (l, dis, disconnect, d)`\n➤ `skip (s, next)`\n➤ `join (connect)`\n➤ `pause (stop)`\n" \
                       "➤ `resume`\n➤ `queue (q)`\n➤ `loop [all/queue/shuffle/random/one/off] (lp)`\n➤ `shuffle (sf, random)`\n" \
                       "➤ `np (info, nowplaying, playing)`\n➤ `lyrics [nothing/song name] (lyric)`\n" \
                       "➤ `songs [nothing/NUM] [artist] (song)`\n➤ `steam [user]`\n➤ `remove [song number] (rm)`" \
                       "\n➤ `goto [song number]`\n➤ `search [nothing/youtube/spotify] [query] (find)`\n➤ `ping`\n➤ `avatar (pfp, profile)`\n" \
                       "➤ `level (lvl)`\n➤ `chatgpt [message] (chat, gpt)`\n➤ `seek [time] (sk)`\n➤ `chords [nothing/song name]`\n" \
                       "➤ `genre [nothing/genre] (genres, recomm, recommendation, recommendations)`\n" \
                       "➤ `forward [time] (fw, forwards, bw, backward, backwards)`\n➤ `config [nothing/option] [value] " \
                       "(cfg, options, opt)`\n➤ `fastplay [query or url] (fp)`\n➤ `perms (prm)`\n" \
                       "➤ `add_prefix [prefix] (prefix, set_prefix)`\n➤ `del_prefix [prefix] (rem_prefix, remove_prefix)`\n" \
                       "➤ `add_perm [name/ALL] [permission]`\n➤ `del_perm [name/ALL] [permission]`\n➤ `available_perms`\n" \
                       "➤ `pitch [semitones] (tone)`"

            file_path = f'options_{ctx.guild.id}.json'
            create_options_file(file_path)
            with open(file_path, 'r') as f:
                options = json.load(f)

            embed = discord.Embed(
                title="Help",
                description=f"Command list -> command [use] (aliases) | Prefixes: {', '.join(['`{}`'.format(item) for item in options['custom_prefixes']])}:\n{comandos}",
                color=EMBED_COLOR
            )
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='perms', aliases=['prm'])
async def perms(ctx):
    try:
        if not check_perms(ctx, "use_perms"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        permissions = ctx.guild.me.guild_permissions
        true_permissions = {name: value for name, value in permissions if value}
        formatted_permissions = ', '.join([f'`{perm[0]}`' for perm in true_permissions.items()])
        embed = discord.Embed(
            title=f'{BOT_NAME} permissions in {ctx.guild.name}:',
            description=formatted_permissions,
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)
    except:
        traceback.print_exc()


@bot.command(name='add_perm', aliases=[])
async def add_perm(ctx, name, perm):
    try:
        if not check_perms(ctx, "use_add_perms"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        file_path = f'user_perms_{ctx.guild.id}.json'
        create_perms_file(ctx, file_path)
        with open(file_path, 'r') as f:
            user_perms = json.load(f)

        server = ctx.guild
        perm = perm.lower()
        if name == "ALL":
            P = True
            for member in server.members:
                try:
                    user_perms[str(member.id)]
                except:
                    if member.guild_permissions.administrator:
                        user_perms[str(member.id)] = ADMIN_PERMS
                    else:
                        user_perms[str(member.id)] = DEFAULT_USER_PERMS
                if perm in AVAILABLE_PERMS:
                    if perm not in user_perms[str(member.id)]: user_perms[str(member.id)].append(perm)
                else:
                    await ctx.send(f"Permission `{perm}` is not a valid permission, use `available_perms`.")
                    P = False
                    break
            if P: await ctx.send(f"Permission `{perm}` added to *everyone*.")
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
                            await ctx.send(f"`{member.name}` already has `{perm}` permission.")
                            break
                        user_perms[str(member.id)].append(perm)
                        await ctx.send(f"Permission `{perm}` added to `{member.name}`.")
                    else:
                        await ctx.send(f"Permission `{perm}` is not a valid permission, use `available_perms`.")
                        break
            if not P:
                await ctx.send(f"Couldn't find user `{name}`.")

        with open(file_path, 'w') as f:
            json.dump(user_perms, f)
    except:
        traceback.print_exc()


@bot.command(name='del_perm', aliases=[])
async def del_perm(ctx, name, perm):
    try:
        if not check_perms(ctx, "use_del_perms"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        file_path = f'user_perms_{ctx.guild.id}.json'
        create_perms_file(ctx, file_path)
        with open(file_path, 'r') as f:
            user_perms = json.load(f)

        server = ctx.guild
        perm = perm.lower()
        if name == "ALL":
            P = True
            for member in server.members:
                try:
                    user_perms[str(member.id)]
                except:
                    if member.guild_permissions.administrator:
                        user_perms[str(member.id)] = ADMIN_PERMS
                    else:
                        user_perms[str(member.id)] = DEFAULT_USER_PERMS
                if perm in AVAILABLE_PERMS:
                    if perm in user_perms[str(member.id)]: user_perms[str(member.id)].remove(perm)
                else:
                    await ctx.send(f"Permission `{perm}` is not a valid permission, use `available_perms`.")
                    P = False
                    break
            if P: await ctx.send(f"Permission `{perm}` removed from everyone.")
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
                        if perm not in user_perms[str(member.id)]:
                            await ctx.send(f"`{member.name}` doesn't have `{perm}` permission.")
                            break
                        user_perms[str(member.id)].remove(perm)
                        await ctx.send(f"Permission `{perm}` removed from `{member.name}`.")
                    else:
                        await ctx.send(f"Permission `{perm}` is not a valid permission, use `available_perms`.")
                        break
            if not P:
                await ctx.send(f"Couldn't find user `{name}`.")

        with open(file_path, 'w') as f:
            json.dump(user_perms, f)
    except:
        traceback.print_exc()


@bot.command(name='available_perms', aliases=[])
async def available_perms(ctx):
    try:
        if not check_perms(ctx, "use_available_perms"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        embed = discord.Embed(
            title="**Available perms**",
            description=f"{', '.join(['`{}`'.format(item) for item in AVAILABLE_PERMS])}",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed, reference=ctx.message)
        embed.title = "**Default perms**"
        embed.description = f"{', '.join(['`{}`'.format(item) for item in DEFAULT_USER_PERMS])}"
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='fastplay', aliases=['fp'])
async def fastplay(ctx, *, url):
    try:
        if not check_perms(ctx, "use_fastplay"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        await play(ctx, url=url, search=False)
    except:
        traceback.print_exc()


@bot.command(name='rewind', aliases=['rw', 'r', 'back'])
async def rewind(ctx):
    try:
        if not check_perms(ctx, "use_rewind"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global loop_mode, go_back
        if loop_mode == 'one': loop_mode = 'off'
        go_back = True
        if ctx.voice_client.is_paused(): ctx.voice_client.resume()
        if ctx.voice_client.is_playing(): ctx.voice_client.stop()
    except:
        traceback.print_exc()


@bot.command(name='join', aliases=['connect'])
async def join(ctx):
    try:
        if not check_perms(ctx, "use_join"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if ctx.voice_client is not None and ctx.voice_client.is_connected():
            await ctx.send(random.choice(already_connected_texts), reference=ctx.message)
            return
        if not ctx.author.voice: return None
        channel = ctx.author.voice.channel
        await channel.connect()
        change_active(ctx, mode='a')
        txt = random.choice(entering_texts) + channel.name + "."
        await ctx.send(txt, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='leave', aliases=['l', 'dis', 'disconnect', 'd'])
async def leave(ctx):
    try:
        if not check_perms(ctx, "use_leave"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global loop_mode, dict_current_song, dict_current_time, disable_play
        if not ctx.author.voice: return
        if loop_mode != "off": await loop(ctx, 'off')
        try:
            await ctx.voice_client.disconnect()
        except:
            traceback.print_exc()
            pass
        change_active(ctx, mode='d')
        gid = str(ctx.guild.id)
        dict_queue[gid].clear()
        disable_play = False
        dict_current_song[gid], dict_current_time[gid] = 0, 0
        [os.remove(os.path.join(DOWNLOAD_PATH, file)) for file in os.listdir(DOWNLOAD_PATH)]
    except:
        traceback.print_exc()


@bot.command(name='np', aliases=['info', 'nowplaying', 'playing'])
async def info(ctx):
    try:
        if not check_perms(ctx, "use_info"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID:
            await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
            return
        if ctx.voice_client and ctx.voice_client.is_playing():
            gid = str(ctx.guild.id)
            queue = dict_queue[gid]
            current_song = dict_current_song[gid]
            yt = YouTube(queue[current_song], use_oauth=USE_LOGIN, allow_oauth_cache=True)
            titulo, duracion, actual = yt.title, convert_seconds(int(yt.length)), convert_seconds(
                dict_current_time[gid])
            artista = utilidades.get_spotify_artist(titulo, is_song=True)
            if not artista: artista = "???"
            embed = discord.Embed(
                title="**Information of the song**",
                description=f"➤ **Title**: {titulo}\n➤ **Artist**: {artista}\n➤ **Duration**: `{duracion}`\n\n {utilidades.get_bar(int(yt.length), dict_current_time[gid])}",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, reference=ctx.message)
        else:
            await ctx.send(random.choice(nothing_on_texts), reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='ping')
async def ping(ctx):
    try:
        if not check_perms(ctx, "use_ping"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        await ctx.send(f"Pong! {round(bot.latency * 1000)}ms", reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='options', aliases=['cfg', 'config', 'opt'])
async def options(ctx, option="", *, query=""):
    try:
        if not check_perms(ctx, "use_options"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
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
        search_limit, recomm_limit, custom_prefixes = options['search_limit'], options['recomm_limit'], options[
            'custom_prefixes']
        original = search_limit, recomm_limit, custom_prefixes
        if not option:
            embed.title = "Configuration"
            embed.description = f"➤ Options: `search_limit={search_limit}`, `recomm_limit={recomm_limit}`, `custom_prefixes={' '.join(custom_prefixes)}`"
            await ctx.send(embed=embed, reference=ctx.message)
            return
        elif option in ["restart", "default"]:
            query = 10
        elif query == "":
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
            return
        try:
            query = float(query)
            if query > 25: query = 25
            if query < 0: query = 0
        except:
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
            return
        if option == "search_limit":
            options['search_limit'], p = int(query), 0
        elif option == "recomm_limit":
            options['recomm_limit'], p = int(query), 1
        elif option in ["restart", "default"]:
            options['search_limit'], options['recomm_limit'], options[
                'custom_prefixes'] = DEFAULT_SEARCH_LIMIT, DEFAULT_RECOMMENDATION_LIMIT, DEFAULT_PREFIXES
        else:
            await ctx.send(random.choice(prefix_use_texts), reference=ctx.message)
            return
        with open(file_path, 'w') as f:
            json.dump(options, f)
        embed.title = f"Configuration: `{option}`"
        if option in ["restart", "default"]:
            embed.description = f"➤ `search_limit` changed from `{original[0]}` to `{DEFAULT_SEARCH_LIMIT}`\n" \
                                f"➤ `recomm_limit` changed from `{original[1]}` to `{DEFAULT_RECOMMENDATION_LIMIT}`\n" \
                                f"➤ `custom_prefixes` changed from `{' '.join(original[2])}` to `{' '.join(DEFAULT_PREFIXES)}`\n"
        else:
            embed.description = f"➤ `{option}` changed from `{original[p]}` to `{options[option]}`"
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='search', aliases=['find'])
async def search(ctx, tipo, *, query=""):
    try:
        if not check_perms(ctx, "use_search"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not tipo:
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
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
                resultados = Search(query).results
            except:
                traceback.print_exc()
                await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
                return
            urls = [f"https://www.youtube.com/watch?v={result.video_id}" for result in resultados]
            urls = urls[:options['search_limit']]
            for url in urls:
                yt = YouTube(url, use_oauth=USE_LOGIN, allow_oauth_cache=True)
                texto = f"➤ [{yt.title}]({url})\n"
                embed.add_field(name="", value=texto, inline=False)
            embed.title = "YouTube search results"
            embed.set_thumbnail(url=yt.thumbnail_url)
            await ctx.send(embed=embed, reference=ctx.message)
        elif tipo.lower() in ['spotify', 'sp', 'spotipy', 'spoti', 'spoty']:
            if not SPOTIFY_SECRET or not SPOTIFY_ID:
                await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
                return
            results = utilidades.spotify_search(query, lim=options['search_limit'])
            for result in results:
                name, artist, url = result['name'], result['artist'], result['url']
                texto = f"➤ **Title**: [{name}]({url}) | **Artist**: {artist}\n"
                embed.add_field(name="", value=texto, inline=False)
            embed.title = "Spotify search results"
            embed.set_thumbnail(url=result['image_url'])
            await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='genre', aliases=['genres', 'recomm', 'recommendation', 'recommendations'])
async def genre(ctx, *, query=""):
    try:
        if not check_perms(ctx, "use_genre"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID:
            await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
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
            embed.title = "Available genres"
        else:
            if not results[0]:
                await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
                return
            songs = results[0]
            for result in songs:
                name, artist, url = result['name'], result['artist'], result['url']
                texto = f"➤ **Title**: [{name}]({url}) | **Artist**: {artist}\n"
                embed.add_field(name="", value=texto, inline=False)
            embed.title = f"Spotify search results by genre: {results[2].replace('-', ' ').title()}"
            embed.set_thumbnail(url=result['image_url'])
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='play', aliases=['p'])
async def play(ctx, *, url, append=True, gif=False, search=True):
    try:
        if not check_perms(ctx, "use_play"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global dict_current_song, dict_current_time, disable_play, ctx_dict
        gid = str(ctx.guild.id)
        if disable_play: return
        if not ctx.author.voice:
            await ctx.send(random.choice(not_in_vc_texts), reference=ctx.message)
            return
        voice_channel = ctx.author.voice.channel

        if not voice_channel.permissions_for(ctx.me).connect:
            await ctx.send(random.choice(private_channel_texts), reference=ctx.message)
            return

        if ctx.voice_client is None or not ctx.voice_client.is_connected():
            await voice_channel.connect()
        change_active(ctx, mode='a')
        ctx_dict[gid] = ctx

        separate_commands = str(url).split('---')
        url = separate_commands[0]
        if len(separate_commands) > 1:
            command = separate_commands[1]
            if command in ['1', 'true', 'si', 'y', 'yes', 'gif']: gif = True

        if not is_url(url):
            results = Search(url).results[:5]
            if search:
                choice_embed = discord.Embed(
                    title="Choose a song:",
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

                urls = [f"https://www.youtube.com/watch?v={result.video_id}" for result in results]
                i, firstyt = 0, None
                for url, emoji in zip(urls, emojis_reactions):
                    yt = YouTube(url, use_oauth=USE_LOGIN, allow_oauth_cache=True)
                    if i == 0: firstyt = yt
                    texto = f"{emoji} [{yt.title}]({url}) `{convert_seconds(yt.length)}`\n"
                    choice_embed.add_field(name="", value=texto, inline=False)
                    i += 1
                if not firstyt: firstyt = yt
                choice_embed.set_thumbnail(url=firstyt.thumbnail_url)

                disable_play = True
                emoji_choice = await choice(ctx, choice_embed, emojis_reactions)
                disable_play = False
                if not emoji_choice or emoji_choice == '❌':
                    await ctx.send(random.choice(cancel_selection_texts))
                    if not members_left.is_running(): members_left.start()
                    return
                url = f"https://www.youtube.com/watch?v={results[emoji_to_number.get(emoji_choice, None) - 1].video_id}"
                if ctx.voice_client:
                    await ctx.send(f"Chosen: {YouTube(url, use_oauth=USE_LOGIN, allow_oauth_cache=True).title}",
                                   reference=ctx.message)
                else:
                    return
            else:
                url = f"https://www.youtube.com/watch?v={results[0].video_id}"

        vtype = check_link_type(url)

        if vtype[0] == 'unknown':
            await ctx.send(random.choice(invalid_link_texts), reference=ctx.message)
            return
        elif vtype[0] == 'playlist':
            links = get_playlist_videos(url)
            if len(links) > PLAYLIST_MAX_LIMIT:
                await ctx.send(
                    f"The playlist has `{len(links)}` videos, `{abs(PLAYLIST_MAX_LIMIT - len(links))}` more than the maximum. "
                    f"The last `{abs(PLAYLIST_MAX_LIMIT - len(links))}` videos were discarded.")
                links = links[:PLAYLIST_MAX_LIMIT]
            embed_playlist = discord.Embed(
                title='Playlist added',
                description=f'**{ctx.author.global_name}** put **{vtype[1]}** in *{ctx.voice_client.channel.name}*!\nA total of `{len(links)}` songs have been added.',
                color=EMBED_COLOR
            )
            sec = 0
            if len(links) > PLAYLIST_TIME_LIMIT:
                durt = 0
            else:
                durt, sec = 1, convert_seconds(get_playlist_total_duration_seconds(links))
            embed_playlist.add_field(
                name='Playlist link',
                value=f'{url}\n\n➤ **Title**: *{vtype[1]}*' + f"\n➤ **Total duration**: `{sec}`" * durt)
        else:
            links = [url]
        yt = YouTube(links[0], use_oauth=USE_LOGIN, allow_oauth_cache=True)
        if yt.length > MAX_VIDEO_LENGTH:
            await ctx.send(f"Video is too long (`{convert_seconds(MAX_VIDEO_LENGTH)}` limit).", reference=ctx.message)
            await skip(ctx)
            return
        titulo, duracion = yt.title, convert_seconds(int(yt.length))
        embed = discord.Embed(
            title='Song chosen',
            description=f'User **{ctx.author.global_name}** put **{titulo}** in *{ctx.voice_client.channel.name}*!',
            color=EMBED_COLOR
        )
        embed2 = discord.Embed(
            title='Added to queue',
            description=f'{links[0]}\n\n➤ **Title**: *{titulo}*\n➤ **Duration**: `{duracion}`',
            color=EMBED_COLOR
        )
        embed.add_field(name='Playing:', value=f'{links[0]}\n\n➤ **Title**: *{titulo}*\n➤ **Duration**: `{duracion}`',
                        inline=False)
        img = None
        if gif and TENOR_API_KEY: img = search_gif(titulo)
        if not img: img = yt.thumbnail_url
        titulo = format_title(titulo)
        if gif:
            embed.set_image(url=img)
            embed2.set_image(url=img)
        else:
            embed.set_thumbnail(url=img)
            embed2.set_thumbnail(url=img)
        audio_streams = yt.streams.filter(only_audio=True)
        sorted_streams = sorted(audio_streams, key=lambda x: int(x.abr[:-4]))
        try:
            if 0 <= yt.length < 300:
                audio_stream = sorted_streams[-1]
            elif 300 <= yt.length < 2000:
                audio_stream = sorted_streams[-2]
            elif 2000 <= yt.length < 3500:
                audio_stream = sorted_streams[1]
            else:
                audio_stream = sorted_streams[0]
        except:
            audio_stream = sorted_streams[0]
        if append:
            try:
                dict_queue[gid]
            except:
                dict_queue[gid] = list()
                dict_current_song[gid] = 0
            for video in links: dict_queue[gid].append(video)
        if audio_stream:
            audio_stream.download(output_path=DOWNLOAD_PATH)
            og_path = DOWNLOAD_PATH + audio_stream.default_filename
            audio_path = DOWNLOAD_PATH + titulo + ".mp4"
            if not os.path.exists(audio_path):
                os.rename(og_path, audio_path)
            if vtype[0] == 'playlist':
                await ctx.send(embed=embed_playlist, reference=ctx.message)
            elif ctx.voice_client.is_playing():
                await ctx.send(embed=embed2, reference=ctx.message)
            else:
                dict_current_time[gid] = 0
                await ctx.send(embed=embed, reference=ctx.message)
            if not update_current_time.is_running(): update_current_time.start(ctx)

            # LVL HANDLE
            await update_level_info(ctx, ctx.author.id, LVL_PLAY_ADD)
            if not ctx.voice_client.is_paused():
                ctx.voice_client.play(discord.FFmpegPCMAudio(audio_path), after=lambda e: on_song_end(ctx, e))
        else:
            await ctx.send(random.choice(rip_audio_texts), reference=ctx.message)
    except exceptions.VideoUnavailable:
        traceback.print_exc()
        await ctx.send(random.choice(restricted_video_texts), reference=ctx.message)
    except Exception as e:
        traceback.print_exc()
        raise e


@bot.command(name='level', aliases=['lvl'])
async def level(ctx):
    try:
        if not check_perms(ctx, "use_level"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        id = ctx.author.id
        guild = ctx.guild
        with open(f'level_data_{guild.id}.json', 'r') as f:
            level_data = json.load(f)
        for data in level_data:
            if id == data['id']:
                lvl, xp, next_xp = data['lvl'], data['xp'], data['next_xp']
        embed = discord.Embed(
            title=f'Level menu',
            description=f'➤ **Name**: {ctx.author.global_name}\n➤ **LVL**: `{lvl}`\n➤ **XP**: `{xp}/{next_xp}`',
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='restart_levels', aliases=['rl'])
async def restart_levels(ctx):
    try:
        if not check_perms(ctx, "use_restart_levels"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
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
        if not check_perms(ctx, "use_remove"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global dict_current_song, dict_current_time
        if not ctx.author.voice: return
        if not ctx.voice_client:
            await ctx.send(random.choice(nothing_on_texts), reference=ctx.message)
            return
        gid = str(ctx.guild.id)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        try:
            index = int(index) - 1
            if not 0 <= index < len(queue): raise Exception
        except:
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
            return
        yt = YouTube(queue[index], use_oauth=USE_LOGIN, allow_oauth_cache=True)
        queue.pop(index)
        await ctx.send(f"Deleted from queue: *{yt.title}*", reference=ctx.message)
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
        if not check_perms(ctx, "use_forward"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global dict_current_time, seek_called
        if not ctx.author.voice: return
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send(random.choice(nothing_on_texts), reference=ctx.message)
            return
        gid = str(ctx.guild.id)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        yt = YouTube(queue[current_song], use_oauth=USE_LOGIN, allow_oauth_cache=True)
        if str(time).replace('-', '').replace('+', '').isnumeric():
            time = int(time)
            dict_current_time[gid] += time
        else:
            symbol = ''
            temptime = time
            if '+' in time: temptime = time.replace('+', '')
            if '-' in time: temptime, symbol = time.replace('-', ''), '-'
            time = int(symbol + str(convert_formated(temptime)))
            current_time += time
        if dict_current_time[gid] > yt.length:
            await skip(ctx)
            return
        if dict_current_time[gid] < 0: dict_current_time[gid] = 0
        seek_called = True
        if ctx.voice_client.is_paused(): ctx.voice_client.resume()
        ctx.voice_client.stop()

        audio_path = find_file(DOWNLOAD_PATH, format_title(yt.title))
        if not audio_path:
            print("Error: No se pudo encontrar el archivo de audio.")
            return

        ctx.voice_client.play(
            discord.FFmpegPCMAudio(DOWNLOAD_PATH + audio_path, before_options=f"-ss {dict_current_time[gid]}"),
            after=lambda e: on_song_end(ctx, e))

        duracion, actual = convert_seconds(int(yt.length)), convert_seconds(dict_current_time[gid])
        modetype = ':fast_forward: Fast forwarding' if time >= 0 else ':arrow_backward: Rewinding'
        embed = discord.Embed(
            title=f"**{modetype} {convert_seconds(abs(time))} to {actual}**",
            description=f"{utilidades.get_bar(int(yt.length), dict_current_time[gid])}",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()
        await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)


@bot.command(name='seek', aliases=['sk'])
async def seek(ctx, time):
    try:
        if not check_perms(ctx, "use_seek"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global dict_current_time, seek_called
        if not ctx.author.voice: return
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send(random.choice(nothing_on_texts), reference=ctx.message)
            return
        gid = str(ctx.guild.id)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        yt = YouTube(queue[current_song], use_oauth=USE_LOGIN, allow_oauth_cache=True)
        audio_path = find_file(DOWNLOAD_PATH, format_title(yt.title))
        if not audio_path:
            print("Error: No se pudo encontrar el archivo de audio.")
            await ctx.send("Error.")
            return

        if str(time).isnumeric():
            time = int(time)
            if time < 0: time = 0
            if time > yt.length:
                await skip(ctx)
                return
            dict_current_time[gid] = time
        else:
            dict_current_time[gid] = int(convert_formated(time))
        seek_called = True
        if ctx.voice_client.is_paused(): ctx.voice_client.resume()
        ctx.voice_client.stop()

        ctx.voice_client.play(
            discord.FFmpegPCMAudio(DOWNLOAD_PATH + audio_path, before_options=f"-ss {dict_current_time[gid]}"),
            after=lambda e: on_song_end(ctx, e))

        duracion, actual = convert_seconds(int(yt.length)), convert_seconds(dict_current_time[gid])
        embed = discord.Embed(
            title=f"**Going to {actual}**",
            description=f"{utilidades.get_bar(int(yt.length), dict_current_time[gid])}",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed, reference=ctx.message)

    except:
        traceback.print_exc()
        await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)


@bot.command(name='loop', aliases=['lp'])
async def loop(ctx, mode="change"):
    try:
        if not check_perms(ctx, "use_loop"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global loop_mode
        if mode == "change": mode = "all" if loop_mode == "off" else "off"
        if mode not in ['queue', 'all', 'shuffle', 'random', 'one', 'off']:
            await ctx.send(f"`{mode}` is not a loop mode, use `queue/all`, `shuffle/random`, `one` or `off`.",
                           reference=ctx.message)
            return
        loop_mode = str(mode)
        await ctx.send(f"Loop mode: `{loop_mode}`." if loop_mode != 'off' else "Loop disabled.", reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='shuffle', aliases=['sf', 'random'])
async def shuffle(ctx):
    try:
        if not check_perms(ctx, "use_shuffle"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global dict_current_song
        gid = str(ctx.guild.id)
        dict_current_song[gid] = -1
        queue = dict_queue[gid]
        random.shuffle(queue)
        global dict_current_time
        await ctx.voice_client.stop()
        if update_current_time.is_running(): update_current_time.stop()
        dict_current_time[gid] = 0
    except:
        traceback.print_exc()


@bot.command(name='queue', aliases=['q'])
async def cola(ctx):
    try:
        if not check_perms(ctx, "use_queue"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        gid = str(ctx.guild.id)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]
        if not queue:
            await ctx.send(random.choice(no_queue_texts), reference=ctx.message)
            return
        titulos, i, titlelen = [], 1, 0
        with ThreadPoolExecutor(max_workers=NUM_THREADS_LOW) as executor:
            titulos = list(executor.map(get_video_info, queue))
        for k in range(len(titulos)):
            titulos[k] = f"`{i}. " + titulos[k] + "` ⮜ **Current song**" if current_song == i - 1 else f"{i}. *" + \
                                                                                                       titulos[k] + "*"
            i += 1
        titletext = '\n'.join(titulos)
        if len(titletext) > 3000:
            newtext = cut_string(titletext, 3000)
            nwlncount = newtext[1].count('\n')
            titletext = newtext[0] + f"\n... (`{nwlncount}` more video{'s' if nwlncount != 1 else ''})"
        embed = discord.Embed(
            title='Queue',
            description=titletext,
            color=EMBED_COLOR
        )
        print(dict_queue, "\n", dict_current_song)
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='pause', aliases=['stop'])
async def pause(ctx):
    try:
        if not check_perms(ctx, "use_pause"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        ctx.voice_client.pause()
        if update_current_time.is_running(): update_current_time.stop()
    except:
        traceback.print_exc()


@bot.command(name='resume', aliases=[])
async def resume(ctx):
    try:
        if not check_perms(ctx, "use_resume"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        ctx.voice_client.resume()
        if not update_current_time.is_running(): update_current_time.start(ctx)
    except:
        traceback.print_exc()


@bot.command(name='skip', aliases=['s', 'next'])
async def skip(ctx):
    try:
        if not check_perms(ctx, "use_skip"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global loop_mode
        if loop_mode == 'one': loop_mode = 'off'
        if ctx.voice_client.is_paused(): ctx.voice_client.resume()
        if ctx.voice_client.is_playing(): ctx.voice_client.stop()
    except:
        traceback.print_exc()


@bot.command(name='goto')
async def goto(ctx, num):
    try:
        if not check_perms(ctx, "use_goto"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        num = int(num)
        gid = str(ctx.guild.id)
        queue = dict_queue[gid]
        if 0 < num <= len(queue):
            global dict_current_song
            dict_current_song[gid] = num - 2
            await skip(ctx)
        else:
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name="avatar", aliases=['profile', 'pfp'])
async def avatar(ctx):
    try:
        if not check_perms(ctx, "use_avatar"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        embed = discord.Embed(
            title=f"Profile picture of {ctx.author.global_name}",
            color=EMBED_COLOR
        )
        embed.set_image(url=ctx.author.avatar.url)
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        await ctx.send(random.choice(avatar_error_texts), reference=ctx.message)
        traceback.print_exc()


@bot.command(name='steam')
async def steam(ctx, name):
    try:
        if not check_perms(ctx, "use_steam"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        name = name.lower()
        url = f'https://steamcommunity.com/id/{name}'
        embed = discord.Embed(
            title=f"Steam profile of {name}",
            description=f'{url}',
            color=EMBED_COLOR
        )
        imgurl = utilidades.get_steam_avatar(url)
        if not imgurl:
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
            return
        embed.set_image(url=imgurl)
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='chatgpt', aliases=['chat', 'gpt'])
async def chatgpt(ctx, *, msg):
    try:
        if not check_perms(ctx, "use_chatgpt"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not OPENAI_KEY:
            await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
            return
        embed = discord.Embed(
            title="ChatGPT Response",
            description=f"{utilidades.chatgpt(msg, OPENAI_KEY)}",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()
        await ctx.send(random.choice(no_api_credits_texts), reference=ctx.message)


@bot.command(name='lyrics', aliases=['lyric'])
async def lyrics(ctx, *, query=None):
    try:
        if not check_perms(ctx, "use_lyrics"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID or not GENIUS_ACCESS_TOKEN:
            await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
            return
        if query is None and not ctx.voice_client:
            await ctx.send(random.choice(nothing_on_texts), reference=ctx.message)
            return
        if not query:
            gid = str(ctx.guild.id)
            queue = dict_queue[gid]
            current_song = dict_current_song[gid]
            yt = YouTube(queue[current_song], use_oauth=USE_LOGIN, allow_oauth_cache=True)
            titulo = yt.title
        else:
            titulo = query
        artista = utilidades.get_spotify_artist(titulo, is_song=True)
        cancion = utilidades.get_spotify_song(titulo)
        print(artista, cancion)
        if not all([artista, cancion]):
            await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
            return
        embed = discord.Embed(
            title="Information",
            description=f"➤ **Title**: {cancion}\n➤ **Artist**: {artista}",
            color=EMBED_COLOR
        )
        lyrics = utilidades.get_lyrics(titulo, (artista, cancion))
        if not all(lyrics):
            await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
            return
        await ctx.send(embed=embed, reference=ctx.message)
        if len(lyrics) > 9000:
            await ctx.send(random.choice(lyrics_too_long_texts), reference=ctx.message)
            return
        for i in range(0, len(lyrics), 2000):
            await ctx.send(lyrics[i:i + 2000], reference=ctx.message)
    except Exception as e:
        traceback.print_exc()


@bot.command(name='songs', aliases=['song'])
async def songs(ctx, number=None, *, artista=""):
    try:
        if not check_perms(ctx, "use_songs"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not SPOTIFY_SECRET or not SPOTIFY_ID:
            await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
            return
        if number is None and artista == "":
            if ctx.voice_client and ctx.voice_client.is_playing():
                gid = str(ctx.guild.id)
                queue = dict_queue[gid]
                current_song = dict_current_song[gid]
                yt = YouTube(queue[current_song], use_oauth=USE_LOGIN, allow_oauth_cache=True)
                artista = yt.title
                number = 10
                m = True
            else:
                await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
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
            await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
            return
        embed = discord.Embed(
            title=f"Top {number} songs of {artista}",
            description=''.join(f"➤ *{cancion}*\n" for cancion in canciones),
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=utilidades.get_artist_image_url(artista))
        await ctx.send(embed=embed, reference=ctx.message)
    except Exception as e:
        traceback.print_exc()


@bot.command(name='chords', aliases=[])
async def chords(ctx, *, query=""):
    try:
        if not check_perms(ctx, "use_chords"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not GENIUS_ACCESS_TOKEN:
            await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
            return
        if not query and ctx.voice_client and ctx.voice_client.is_playing():
            gid = str(ctx.guild.id)
            queue = dict_queue[gid]
            current_song = dict_current_song[gid]
            yt = YouTube(queue[current_song], use_oauth=USE_LOGIN, allow_oauth_cache=True)
            query = yt.title
        elif not query:
            await ctx.send(random.choice(nothing_on_texts), reference=ctx.message)
            return
        artista, cancion = utilidades.get_artist_and_song(query)

        msg = utilidades.get_chords_and_lyrics(query)
        if not msg:
            msg = await utilidades.search_cifraclub(query)
        if not msg:
            await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
            return
        for i in range(0, len(msg), 4000):
            embed = discord.Embed(
                title="",
                description=msg[i:i + 4000],
                color=EMBED_COLOR
            )
            if i == 0: embed.title = f"Chords of {cancion}, {artista}"
            await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='pitch', aliases=['tone'])
async def pitch(ctx, semitones):
    try:
        if not check_perms(ctx, "use_pitch"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global dict_current_time
        ctx.voice_client.pause()
        if update_current_time.is_running(): update_current_time.stop()
        dict_current_time[gid] = 0
        gid = str(ctx.guild.id)
        queue = dict_queue[gid]
        current_song = dict_current_song[gid]

        yt = YouTube(queue[current_song], use_oauth=USE_LOGIN, allow_oauth_cache=True)
        audio_path = DOWNLOAD_PATH + find_file(DOWNLOAD_PATH, format_title(yt.title))
        y, sr = librosa.load(audio_path, mono=False)
        temp_new_y = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
        new_y = np.stack([temp_new_y[0], temp_new_y[1]], axis=-1)
        sf.write(audio_path[:-4] + ".wav", new_y, sr)
        audio_path, input_file = rf"{audio_path}", rf"{audio_path[:-4] + '.wav'}"
        command = f"ffmpeg -y -i {input_file} {audio_path}"
        subprocess.run(command.split())
        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_path),
                              after=lambda e: print('Player error: %s' % e) if e else None)
        embed = discord.Embed(
            title="Pitch changed",
            description=f'Pitch: {"+" if float(semitones) >= 0 else "-"}{abs(float(semitones))}',
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='add_prefix', aliases=['prefix', 'set_prefix'])
async def add_prefix(ctx, prefix):
    try:
        if not check_perms(ctx, "use_add_prefix"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        gid = str(ctx.guild.id)
        file_path = f'options_{gid}.json'
        create_options_file(file_path)

        with open(file_path, 'r') as f:
            options = json.load(f)

        if prefix not in options['custom_prefixes']: options['custom_prefixes'].append(prefix)

        embed = discord.Embed(
            title="Prefix added",
            description=f"➤ Prefix `{prefix}` has been added. Prefixes: `{' '.join(options['custom_prefixes'])}`",
            color=EMBED_COLOR
        )

        with open(file_path, 'w') as f:
            json.dump(options, f)

        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='remove_prefix', aliases=['del_prefix', 'rem_prefix'])
async def del_prefix(ctx, prefix):
    try:
        if not check_perms(ctx, "use_del_prefix"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        gid = str(ctx.guild.id)
        file_path = f'options_{gid}.json'
        create_options_file(file_path)

        with open(file_path, 'r') as f:
            options = json.load(f)
        if prefix in options['custom_prefixes']: options['custom_prefixes'].remove(prefix)

        embed = discord.Embed(
            title="Prefix removed",
            description=f"➤ Prefix `{prefix}` has been removed. Prefixes: `{' '.join(options['custom_prefixes'])}`",
            color=EMBED_COLOR
        )

        with open(file_path, 'w') as f:
            json.dump(options, f)

        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


bot.run(DISCORD_APP_KEY)
