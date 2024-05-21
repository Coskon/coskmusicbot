import discord
import asyncio
import utilidades
import librosa
import subprocess
import soundfile as sf
import numpy as np
import os, random, re, json, traceback, time, ast, configparser
from discord.ext import commands, tasks
from pytube import YouTube, exceptions, Search, Playlist
from concurrent.futures import ThreadPoolExecutor
from extras import *

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
if len(parameters.keys()) < 25:
    input(f"\033[91m{missing_parameters}\033[0m")
    write_param()
    parameters = read_param()

globals().update(parameters)

## API KEYS ##
USE_PRIVATE_TOKENS = True
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

## GLOBAL VARIABLES ##
dict_queue, active_servers, ctx_dict = dict(), dict(), dict()
button_choice, vote_skip_dict, vote_skip_counter = dict(), dict(), dict()
message_id_dict, majority_dict, ctx_dict_skip = dict(), dict(), dict()
user_cooldowns = {}
loop_mode = dict()
dict_current_song, dict_current_time = dict(), dict()
go_back, seek_called, disable_play = (False for _ in range(3))


## NORMAL FUNCTIONS ##
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


def get_video_info(url):
    try:
        return YouTube(url).title
    except Exception as e:
        traceback.print_exc()


def get_playlist_videos(link):
    try:
        playlist = Playlist(link)
        video_urls = [video.watch_url for video in playlist.videos]
        return video_urls
    except Exception as e:
        print(f"{generic_error}: {e}")
        return []


def get_playlist_total_duration_seconds(links):
    try:
        def get_video_duration(video_url):
            try:
                yt = YouTube(video_url, use_oauth=USE_LOGIN, allow_oauth_cache=True)
                return yt.length
            except Exception as e:
                print(f"{processing_error} {video_url}: {e}")
                return 0

        with ThreadPoolExecutor(max_workers=NUM_THREADS_HIGH) as executor:
            durations = list(executor.map(get_video_duration, links))

        total_duration_seconds = sum(durations)
        return total_duration_seconds

    except Exception as e:
        print(f"{generic_error}: {e}")
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


def on_song_end(ctx, error):
    global dict_current_song, go_back, seek_called, loop_mode
    if error:
        print(f"{generic_error}: {error}")
    if seek_called:
        seek_called = False
    else:
        gid = str(ctx.guild.id)
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] == 'one':
            pass
        elif go_back:
            dict_current_song[gid] -= 1
        else:
            dict_current_song[gid] += 1
        go_back = False
        if update_current_time.is_running(): update_current_time.stop()
        bot.loop.create_task(play_next(ctx))


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
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] in ['queue', 'all']:
            dict_current_song[gid] = 0
        elif loop_mode[gid] in ['random', 'shuffle']:
            dict_current_song[gid] = random.randint(0, len(queue) - 1)
        else:
            await leave(ctx, ignore=True)
    if queue:
        url = queue[dict_current_song[gid]]
        await ctx.invoke(bot.get_command('play'), url=url, append=False)


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


bot = commands.Bot(command_prefix="DEF_PREFIX", activity=activity, intents=intents, help_command=None,
                   case_insensitive=True)


## CLASSES ##
class PlayButton(discord.ui.Button):
    def __init__(self, song_index, gid, disabled=False):
        self.song_index = song_index
        self.gid = gid
        if song_index == -2:
            super().__init__(label=f"\0", style=discord.ButtonStyle.secondary, disabled=disabled)
        else:
            super().__init__(label=f"", style=discord.ButtonStyle.secondary,
                             emoji=f"{['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '❌'][song_index]}", disabled=disabled)

    # random, prev page, cancel, next page, play all: '🔀', '⬅️', '❌', '➡️', , '🇦'
    async def callback(self, interaction):
        global button_choice
        button_choice[self.gid] = self.song_index


class SongChooseMenu(discord.ui.View):
    def __init__(self, gid):
        super().__init__()
        for i in range(5): self.add_item(PlayButton(i, gid))
        for i in range(5):
            if i != 2:
                self.add_item(PlayButton(-2, gid, True))
            else:
                self.add_item(PlayButton(-1, gid))


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
                gid = str(ctx.guild.id)
                loop_mode[gid] = loop_mode.setdefault(gid, "off")
                if loop_mode[gid] != "off": await loop(ctx, 'off')
                try:
                    await ctx.voice_client.disconnect()
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
            await ctx.send(song_skipped)
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
        if not check_perms(ctx, "use_help"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
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
                await ctx.send(random.choice(not_existing_command_texts), reference=ctx.message)
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
            title=bot_perms.replace("%botname", BOT_NAME).replace("%server", ctx.guild.name),
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
                    await ctx.send(invalid_perm.replace("%perm", perm))
                    P = 0
                    break
            if P == 1: await ctx.send(perm_added_everyone.replace("%perm", perm))
            if P == 2: await ctx.send(all_perms_everyone)
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
                            await ctx.send(perm_already_added.replace("%name", member.name).replace("%perm", perm))
                            break
                        user_perms[str(member.id)].append(perm)
                        await ctx.send(perm_added.replace("%perm", perm).replace("%name", member.name))
                    elif perm in ["ALL", "*"]:
                        user_perms[str(member.id)] = AVAILABLE_PERMS.copy()
                        await ctx.send(all_perms_added.replace("%name", member.name))
                    else:
                        await ctx.send(invalid_perm.replace("%perm", perm))
                        break
            if not P:
                await ctx.send(couldnt_find_user.replace("%name", name))

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
        if name == "ALL" or name == "*":
            P = True
            for member in server.members:
                user_perms[str(member.id)] = user_perms.setdefault(str(member.id),
                                                                   ADMIN_PERMS if member.guild_permissions.administrator else DEFAULT_USER_PERMS)
                if perm in AVAILABLE_PERMS:
                    if perm in user_perms[str(member.id)]: user_perms[str(member.id)].remove(perm)
                else:
                    await ctx.send(invalid_perm.replace("%perm", perm))
                    P = False
                    break
            if P: await ctx.send(perm_del_everyone.replace("%perm", perm))
        else:
            P = False
            for member in server.members:
                if member.name in [name, name.lower()]:
                    P = True
                    user_perms[str(member.id)] = user_perms.setdefault(str(member.id),
                                                                       ADMIN_PERMS if member.guild_permissions.administrator else DEFAULT_USER_PERMS)
                    if perm in AVAILABLE_PERMS:
                        if perm not in user_perms[str(member.id)]:
                            await ctx.send(perm_not_added.replace("%name", member.name).replace("%perm", perm))
                            break
                        user_perms[str(member.id)].remove(perm)
                        await ctx.send(perm_removed.replace("%perm", perm).replace("%name", member.name))
                    else:
                        await ctx.send(invalid_perm.replace("%perm", perm))
                        break
            if not P:
                await ctx.send(couldnt_find_user.replace("%name", name))

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
            title=available_perms_title,
            description=f"{', '.join(['`{}`'.format(item) for item in AVAILABLE_PERMS])}",
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed, reference=ctx.message)
        embed.title = default_perms_title
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
        gid = str(ctx.guild.id)
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] == 'one': loop_mode[gid] = 'off'
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
        if not ctx.author.voice:
            await ctx.send(random.choice(not_in_vc_texts), reference=ctx.message)
            return None
        if ctx.voice_client is not None and ctx.voice_client.is_connected():
            await ctx.send(random.choice(already_connected_texts), reference=ctx.message)
            return
        channel = ctx.author.voice.channel
        await channel.connect()
        change_active(ctx, mode='a')
        txt = random.choice(entering_texts) + channel.name + "."
        await ctx.send(txt, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='leave', aliases=['l', 'dis', 'disconnect', 'd'])
async def leave(ctx, ignore=False):
    try:
        global loop_mode, dict_current_song, dict_current_time, disable_play
        if not ignore:
            if not check_perms(ctx, "use_leave"):
                await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
                return
            if not ctx.author.voice:
                await ctx.send(random.choice(not_in_vc_texts), reference=ctx.message)
                return
            bot_vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            if not bot_vc:
                await ctx.send(random.choice(not_connected_texts), reference=ctx.message)
                return
            if ctx.author.voice.channel != bot_vc.channel:
                await ctx.send(random.choice(different_channel_texts), reference=ctx.message)
                return
        gid = str(ctx.guild.id)
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] != "off": await loop(ctx, 'off')
        try:
            await ctx.voice_client.disconnect()
        except:
            traceback.print_exc()
            pass
        change_active(ctx, mode='d')
        try:
            dict_queue[gid].clear()
        except:
            pass
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
                title=song_info_title,
                description=song_info_desc.replace("%title", titulo).replace("%artist", artista).replace("%duration",
                                                                                                         str(duracion)).replace(
                    "%bar", utilidades.get_bar(int(yt.length), dict_current_time[gid])),
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
            embed.title = config_title
            embed.description = config_desc.replace("%search_limit", str(search_limit)).replace("%recomm_limit",
                                                                                                str(recomm_limit)).replace(
                "%custom_prefixes", ' '.join(custom_prefixes))
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
            embed.title = youtube_search_title
            embed.set_thumbnail(url=yt.thumbnail_url)
            await ctx.send(embed=embed, reference=ctx.message)
        elif tipo.lower() in ['spotify', 'sp', 'spotipy', 'spoti', 'spoty']:
            if not SPOTIFY_SECRET or not SPOTIFY_ID:
                await ctx.send(random.choice(no_api_key_texts), reference=ctx.message)
                return
            results = utilidades.spotify_search(query, lim=options['search_limit'])
            for result in results:
                name, artist, url = result['name'], result['artist'], result['url']
                texto = spotify_search_desc.replace("%name", name).replace("%url", url).replace("%artist", artist)
                embed.add_field(name="", value=texto, inline=False)
            embed.title = spotify_search_title
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
            embed.title = available_genres
        else:
            if not results[0]:
                await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
                return
            songs = results[0]
            for result in songs:
                name, artist, url = result['name'], result['artist'], result['url']
                texto = spotify_search_desc.replace("%name", name).replace("%url", url).replace("%artist", artist)
                embed.add_field(name="", value=texto, inline=False)
            embed.title = genre_search_title.replace("%genre", results[2].replace('-', ' ').title())
            embed.set_thumbnail(url=result['image_url'])
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='play', aliases=['p'])
async def play(ctx, *, url="", append=True, gif=False, search=True):
    try:
        if not check_perms(ctx, "use_play"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        global dict_current_song, dict_current_time, disable_play, ctx_dict, vote_skip_dict
        gid = str(ctx.guild.id)
        if disable_play: return
        if not ctx.author.voice:
            await ctx.send(random.choice(not_in_vc_texts), reference=ctx.message)
            return
        if not url:
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
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
                    title=choose_song_title,
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
                if USE_BUTTONS:
                    button_choice[gid] = -1
                    menu = SongChooseMenu(gid)
                    message = await ctx.send(embed=choice_embed, view=menu)
                    try:
                        def check(intrc: discord.interactions.Interaction):
                            if intrc.user.id == ctx.author.id: return True

                        await bot.wait_for('interaction', timeout=TIMELIMIT, check=check)
                    except asyncio.TimeoutError:
                        await ctx.send(random.choice(song_not_chosen_texts), reference=ctx.message)
                        await message.delete()
                        disable_play = False
                        return
                    disable_play = False
                    await message.delete()
                    if button_choice[gid] < 0:
                        await ctx.send(random.choice(cancel_selection_texts))
                        if not members_left.is_running(): members_left.start()
                        return
                    url = f"https://www.youtube.com/watch?v={results[button_choice[gid]].video_id}"
                    if ctx.voice_client:
                        await ctx.send(song_selected.replace("%title", YouTube(url, use_oauth=USE_LOGIN,
                                                                               allow_oauth_cache=True).title),
                                       reference=ctx.message)
                    else:
                        return

                else:
                    emoji_choice = await choice(ctx, choice_embed, emojis_reactions)
                    disable_play = False
                    if not emoji_choice or emoji_choice == '❌':
                        await ctx.send(random.choice(cancel_selection_texts))
                        if not members_left.is_running(): members_left.start()
                        return
                    url = f"https://www.youtube.com/watch?v={results[emoji_to_number.get(emoji_choice, None) - 1].video_id}"
                    if ctx.voice_client:
                        await ctx.send(song_selected.replace("%title", YouTube(url, use_oauth=USE_LOGIN,
                                                                               allow_oauth_cache=True).title),
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
                await ctx.send(playlist_max_reached.replace("%pl_length", str(len(links))).replace("%over", str(abs(
                    PLAYLIST_MAX_LIMIT - len(links)))).replace("%discarded", str(abs(PLAYLIST_MAX_LIMIT - len(links)))))
                links = links[:PLAYLIST_MAX_LIMIT]
            embed_playlist = discord.Embed(
                title=playlist_added_title,
                description=playlist_added_desc.replace("%name", ctx.author.global_name).replace("%title",
                                                                                                 str(vtype[1])).replace(
                    "%ch_name", ctx.voice_client.channel.name).replace("%pl_length", str(len(links))),
                color=EMBED_COLOR
            )
            sec = 0
            if len(links) > PLAYLIST_TIME_LIMIT:
                durt = 0
            else:
                durt, sec = 1, convert_seconds(get_playlist_total_duration_seconds(links))
            embed_playlist.add_field(
                name=playlist_link,
                value=playlist_link_desc.replace("%url", url).replace("%title", vtype[
                    1]) + durt * playlist_link_desc_time.replace("%duration", str(sec)))
        else:
            links = [url]
        yt = YouTube(links[0], use_oauth=USE_LOGIN, allow_oauth_cache=True)
        if yt.length > MAX_VIDEO_LENGTH:
            await ctx.send(video_max_duration.replace("%video_limit", str(convert_seconds(MAX_VIDEO_LENGTH))),
                           reference=ctx.message)
            await skip(ctx)
            return
        titulo, duracion = yt.title, convert_seconds(int(yt.length))
        embed = discord.Embed(
            title=song_chosen_title,
            description=song_chosen_desc.replace("%name", ctx.author.global_name).replace("%title", titulo).replace(
                "%ch_name", ctx.voice_client.channel.name),
            color=EMBED_COLOR
        )
        embed2 = discord.Embed(
            title=added_queue_title,
            description=added_queue_desc.replace("%url", links[0]).replace("%title", titulo).replace("%duration",
                                                                                                     str(duracion)),
            color=EMBED_COLOR
        )
        embed.add_field(name=playing_title,
                        value=playing_desc.replace("%url", links[0]).replace("%title", titulo).replace("%duration",
                                                                                                       str(duracion)),
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
            dict_queue[gid] = dict_queue.setdefault(gid, list())
            dict_current_song[gid] = dict_current_song.setdefault(gid, 0)
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
            vote_skip_dict[gid] = -1
            if not ctx.voice_client.is_paused():
                try:
                    ctx.voice_client.play(discord.FFmpegPCMAudio(audio_path), after=lambda e: on_song_end(ctx, e))
                except:
                    pass
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
        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='restart_levels', aliases=['rl'])
async def restart_levels(ctx):
    try:
        level_file_path = f'level_data_{ctx.guild.id}.json'
        if not os.path.exists(level_file_path):
            pass
        elif not check_perms(ctx, "use_restart_levels"):
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
        await ctx.send(removed_from_queue.replace("%title", yt.title), reference=ctx.message)
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
            print(couldnt_find_audiofile)
            return

        ctx.voice_client.play(
            discord.FFmpegPCMAudio(DOWNLOAD_PATH + audio_path, before_options=f"-ss {dict_current_time[gid]}"),
            after=lambda e: on_song_end(ctx, e))

        duracion, actual = convert_seconds(int(yt.length)), convert_seconds(dict_current_time[gid])
        modetype = fast_forwarding if time >= 0 else rewinding
        embed = discord.Embed(
            title=forward_title.replace("%modetype", modetype).replace("%sec", str(convert_seconds(abs(time)))).replace(
                "%time", str(actual)),
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
            print(couldnt_find_audiofile)
            await ctx.send(generic_error)
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
            title=seek_title.replace("%time", str(actual)),
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
        gid = str(ctx.guild.id)
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if mode == "change": mode = "all" if loop_mode[gid] == "off" else "off"
        if mode not in ['queue', 'all', 'shuffle', 'random', 'one', 'off']:
            await ctx.send(not_loop_mode.replace("%mode", str(mode)),
                           reference=ctx.message)
            return
        loop_mode[gid] = str(mode)
        await ctx.send(loop_mode_changed.replace("%loop", loop_mode[gid]) if loop_mode[gid] != 'off' else loop_disable,
                       reference=ctx.message)
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
            titulos[k] = f"`{i}. " + titulos[k] + queue_current if current_song == i - 1 else f"{i}. *" + titulos[
                k] + "*"
            i += 1
        titletext = '\n'.join(titulos)
        if len(titletext) > 3000:
            newtext = cut_string(titletext, 3000)
            nwlncount = newtext[1].count('\n')
            titletext = newtext[0] + queue_more_videos.replace("%more_videos", str(nwlncount)).replace("%plural",
                                                                                                       "s" if nwlncount != 1 else "")
        embed = discord.Embed(
            title=queue_title,
            description=titletext,
            color=EMBED_COLOR
        )
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
        global vote_skip_dict, loop_mode, vote_skip_counter, message_id_dict, majority_dict, ctx_dict_skip
        gid = str(ctx.guild.id)
        vote_skip_dict.setdefault(gid, -1)
        if vote_skip_dict[gid] == -1:
            if not ctx.voice_client:
                await ctx.send(random.choice(not_in_vc_texts), reference=ctx.message)
                return
            if not check_perms(ctx, "use_skip"):
                if not check_perms(ctx, "use_vote_skip"):
                    await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
                    return
                members = ctx.voice_client.channel.members
                member_amount = len(members) - 1
                majority = round(member_amount / 2)
                vote_message = await ctx.send(vote_skip_text.replace("%num", str(majority)))
                await vote_message.add_reaction("❌")
                await vote_message.add_reaction("✅")
                await asyncio.sleep(1)
                vote_skip_dict[gid], vote_skip_counter[gid] = 0, 0
                message_id_dict[gid], majority_dict[gid] = vote_message.id, [majority, list(
                    user.id for user in ctx.voice_client.channel.members)]
                ctx_dict_skip[gid] = ctx
                vote_skip.start()
        if vote_skip_dict[gid] == 0: return
        vote_skip_dict[gid], vote_skip_counter[gid] = -1, 0
        loop_mode[gid] = loop_mode.setdefault(gid, "off")
        if loop_mode[gid] == 'one': loop_mode[gid] = 'off'
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
            title=profile_title.replace("%name", ctx.author.global_name),
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
            title=steam_title.replace("%name", name),
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
            title=chatgpt_title,
            description=f"{utilidades.chatgpt(msg, OPENAI_KEY, language)}",
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
        if not all([artista, cancion]):
            await ctx.send(random.choice(couldnt_complete_search_texts), reference=ctx.message)
            return
        embed = discord.Embed(
            title=lyrics_title,
            description=lyrics_desc.replace("%title", cancion).replace("%artist", artista),
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
            title=top_songs_title.replace("%number", str(number)).replace("%artist", artista),
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
            if i == 0: embed.title = chords_title.replace("%song", cancion).replace("%artist", artista)
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
                              after=lambda e: print(f"{generic_error}: %s" % e) if e else None)
        embed = discord.Embed(
            title=pitch_title,
            description=pitch_desc.replace("%sign", "+" if float(semitones) >= 0 else "-").replace("%tone", str(abs(
                float(semitones)))),
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
            title=prefix_add_title,
            description=prefix_add_desc.replace("%prefix", prefix).replace("%prefixes",
                                                                           ' '.join(options['custom_prefixes'])),
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
            title=prefix_del_title,
            description=prefix_del_desc.replace("%prefix", prefix).replace("%prefixes",
                                                                           ' '.join(options['custom_prefixes'])),
            color=EMBED_COLOR
        )

        with open(file_path, 'w') as f:
            json.dump(options, f)

        await ctx.send(embed=embed, reference=ctx.message)
    except:
        traceback.print_exc()


@bot.command(name='lang', aliases=['language', 'change_lang', 'change_language'])
async def lang(ctx, lng=None):
    try:
        if not check_perms(ctx, "use_lang"):
            await ctx.send(random.choice(insuff_perms_texts), reference=ctx.message)
            return
        if not lng or lng.lower() not in ['es', 'en']:
            await ctx.send(random.choice(invalid_use_texts), reference=ctx.message)
            return

        with open(f"lang/{lng.lower()}.json", "r") as f:
            lang_dict = json.load(f)

        config.set("Config", "lang", lng.lower())
        with open(config_path, "w") as f:
            config.write(f)

        globals().update(lang_dict)

        await ctx.send(lang_changed, reference=ctx.message)
    except:
        traceback.print_exc()


bot.run(DISCORD_APP_KEY)
