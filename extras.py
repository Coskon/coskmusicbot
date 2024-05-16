import os, re, json
import requests
from urllib.parse import urlsplit
from pytube import YouTube, Playlist, exceptions

def write_param():
    with open('PARAMETERS.txt', 'w') as f:
        f.write("BOT_NAME = Coskquin  # name of your bot\n\nMAX_VIDEO_LENGTH = 18000  # in seconds\n\nPLAYLIST_MAX_LIMIT = 200  # max videos on playlist\n\nPLAYLIST_TIME_LIMIT = 100  # max videos to see their total duration\n\nTIMELIMIT = 30  # (in seconds) timelimit for the popup of the search choice embed\n\nREQUEST_LIMIT = 1.75  # (in seconds) time should pass between command calls from each user\n\nMEMBERS_LEFT_TIMEOUT = 20  # (in seconds) time between each check for members left\n\nEMBED_COLOR = 0xff0000  # color for the side of the embed\n\nDEFAULT_SEARCH_LIMIT = 5  # how many videos to show using the search command by default\n\nDEFAULT_RECOMMENDATION_LIMIT = 15  # how many videos to show in recommendations by default\n\nLVL_PLAY_ADD = 1  # how much to add per play command called\n\nLVL_NEXT_XP = 25  # how much required xp added per next level\n\nLVL_BASE_XP = 25  # base xp required for the first level\n\nNUM_THREADS_HIGH = 4  # number of threads to use for tasks that need high performance\n\nNUM_THREADS_LOW = 2  # number of threads to use for tasks that don't need as much performance\n\nUSE_LOGIN = True\n\nDOWNLOAD_PATH = downloads/  # download output folder\n\nDEFAULT_PREFIXES = ['.', '+', ',']  # prefixes to use by default\n\nEXCLUDED_CASES = ['._.', '.-.', ':)', '-.-']  # list of cases to exclude from being recognized as commands\n\nAVAILABLE_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_loop', 'use_shuffle', 'use_info', 'use_lyrics', 'use_songs', 'use_steam', 'use_remove', 'use_goto', 'use_search', 'use_ping', 'use_avatar', 'use_level', 'use_chatgpt', 'use_seek', 'use_chords', 'use_genre', 'use_forward', 'use_options', 'use_fastplay', 'use_perms', 'use_add_prefix', 'use_del_prefix', 'use_pitch', 'use_rewind', 'use_restart_levels', 'use_add_perms', 'use_del_perms', 'use_available_perms', 'use_lang']  # all permissions available\n\nDEFAULT_USER_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_rewind', 'use_loop', 'use_info', 'use_goto', 'use_level', 'use_seek', 'use_genre', 'use_forward', 'use_fastplay']  # permissions each user gets by default\n\nADMIN_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_loop', 'use_shuffle', 'use_info', 'use_lyrics', 'use_songs', 'use_steam', 'use_remove', 'use_goto', 'use_search', 'use_ping', 'use_avatar', 'use_level', 'use_chatgpt', 'use_seek', 'use_chords', 'use_genre', 'use_forward', 'use_options', 'use_fastplay', 'use_perms', 'use_add_prefix', 'use_del_prefix', 'use_pitch', 'use_rewind', 'use_restart_levels', 'use_add_perms', 'use_del_perms', 'use_available_perms', 'use_lang']  # permissions admin users get by default\n\nUSE_BUTTONS = False  # to use buttons to select a song, if False uses reactions\n\nUSE_GRADIO = True  # use gradio for the user interface")


def read_param(complete=False):
    if not os.path.exists("PARAMETERS.txt"): write_param()
    with open("PARAMETERS.txt", 'r') as f:
        lines = f.readlines()

    var_values = []
    for line in lines:
        if line == "\n": continue
        if complete: var_values.append(line[:line.find("#")].split("="))
        else: var_values.append(line[:line.find("#")].split("=")[1].strip())
    return var_values


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
        raise ValueError(f"{invalid_time_format}")
    return hours * 3600 + minutes * 60 + seconds


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
        print(f"{api_request_error}: {e}")
        return None


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


def find_file(folder_path, file_name):
    for filename in os.listdir(folder_path):
        if filename.startswith(file_name) and os.path.isfile(os.path.join(folder_path, filename)):
            return filename
    return None


def format_title(title):
    new_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)
    return new_title.replace(" ", "_") if new_title != '' else 'NoTitle'


def cut_string(input_string, max_length):
    if len(input_string) <= max_length:
        return input_string

    newline_position = input_string.rfind('\n', 0, max_length)
    cut_position = newline_position if newline_position != -1 else max_length

    return input_string[:cut_position], input_string[cut_position:]


def get_video_info(url):
    try:
        return YouTube(url).title
    except Exception as e:
        traceback.print_exc()
