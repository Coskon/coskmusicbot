import os, re, json, ast
import requests
from urllib.parse import urlsplit


def write_param():
    threads = os.cpu_count() // 2
    with open('PARAMETERS.txt', 'w') as f:
        f.write(f"BOT_NAME = Coskquin  # name of your bot\n\nMAX_VIDEO_LENGTH = 216000  # in seconds\n\nPLAYLIST_MAX_LIMIT = 1000  # max videos on playlist\n\nSPOTIFY_LIMIT = 200  # max videos for a spotify playlist/album\n\nTIMELIMIT = 40  # (in seconds) timelimit for the popup of the search choice embed\n\nREQUEST_LIMIT = 1.25  # (in seconds) time should pass between command calls from each user\n\nMEMBERS_LEFT_TIMEOUT = 30  # (in seconds) time between each check for members left\n\nEMBED_COLOR = 0xff0000  # color for the side of the embed\n\nITAGS_LIST = [22, 151, 132, 17, 36, 92, 5, 139, 140, 141, 249, 250, 251, 18]  # list of itags allowed, dont touch if not sure\n\nDEFAULT_SEARCH_LIMIT = 5  # how many videos to show using the search command by default\n\nDEFAULT_RECOMMENDATION_LIMIT = 15  # how many videos to show in recommendations by default\n\nLVL_PLAY_ADD = 1  # how much to add per play command called\n\nLVL_NEXT_XP = 25  # how much required xp added per next level\n\nLVL_BASE_XP = 25  # base xp required for the first level\n\nNUM_THREADS_HIGH = {threads if threads > 0 else 1}  # number of threads to use for tasks that need high performance\n\nNUM_THREADS_LOW = {threads // 2 if threads // 2 > 0 else 1}  # number of threads to use for tasks that don't need as much performance\n\nUSE_LOGIN = False\n\nDOWNLOAD_PATH = downloads/  # download output folder\n\nDEFAULT_PREFIXES = ['.', '+', ',']  # prefixes to use by default\n\nEXCLUDED_CASES = ['._.', '.-.', ':)', '-.-']  # list of cases to exclude from being recognized as commands\n\nAVAILABLE_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_loop', 'use_shuffle', 'use_info', 'use_lyrics', 'use_songs', 'use_steam', 'use_remove', 'use_goto', 'use_search', 'use_ping', 'use_avatar', 'use_level', 'use_chatgpt', 'use_seek', 'use_chords', 'use_genre', 'use_forward', 'use_options', 'use_fastplay', 'use_perms', 'use_add_prefix', 'use_del_prefix', 'use_pitch', 'use_rewind', 'use_restart_levels', 'use_add_perms', 'use_del_perms', 'use_available_perms', 'use_lang', 'use_vote_skip', 'use_volume', 'use_shazam', 'use_restrict', 'use_eq', 'use_autodj', 'use_download', 'use_reverse']  # all permissions available\n\nDEFAULT_USER_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_rewind', 'use_loop', 'use_info', 'use_goto', 'use_level', 'use_seek', 'use_genre', 'use_forward', 'use_fastplay', 'use_vote_skip', 'use_shazam', 'use_download']  # permissions each user gets by default\n\nADMIN_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_loop', 'use_shuffle', 'use_info', 'use_lyrics', 'use_songs', 'use_steam', 'use_remove', 'use_goto', 'use_search', 'use_ping', 'use_avatar', 'use_level', 'use_chatgpt', 'use_seek', 'use_chords', 'use_genre', 'use_forward', 'use_options', 'use_fastplay', 'use_perms', 'use_add_prefix', 'use_del_prefix', 'use_pitch', 'use_rewind', 'use_restart_levels', 'use_add_perms', 'use_del_perms', 'use_available_perms', 'use_lang', 'use_vote_skip', 'use_volume', 'use_shazam', 'use_restrict', 'use_eq', 'use_autodj', 'use_download', 'use_reverse']  # permissions admin users get by default\n\nUSE_BUTTONS = True  # to use buttons to select a song, if False uses reactions\n\nUSE_GRADIO = True  # use gradio for the user interface\n\nSKIP_TIMELIMIT = 15  # in seconds, timelimit for a skip vote\n\nMAX_SEARCH_SELECT = 15  # limit of youtube searching when choosing a song\n\nREFERENCE_MESSAGES = True  # whether for the bot to reference the user or not\n\nSKIP_PRIVATE_SEARCH = False  # whether or not to skip private/age restricted videos when searching\n\nAUTO_DJ_MAX_ADD = 3  # how many songs does the auto dj add each time\n\nQUEUE_VIDEOS_PER_PAGE = 30  # how many videos to show per page in the queue")


def read_param(complete=False):
    if not os.path.exists("PARAMETERS.txt"): write_param()
    with open("PARAMETERS.txt", 'r') as f:
        lines = f.readlines()

    parameters = {}
    for line in lines:
        if line == "\n": continue
        l = line[:line.find("#")].split("=")
        name, value = l[0].strip(), l[1].strip()
        if value.lower() in ["true", "false"]: value = value.capitalize()
        try: parameters[str(name)] = ast.literal_eval(value)
        except: parameters[str(name)] = ast.literal_eval(f'"{value}"')
    return parameters


def check_link_type(url, checked=False):
    if "&start_radio" in url: return "unknown", None
    yt_vid_match = re.search(r"(?:v=|\/videos\/|embed\/|\.be\/|\/v\/|\/e\/|watch\/|shorts\/|live\/|\/oembed\?url=https:\/\/www\.youtube\.com\/watch\?v=|watch%3Fv%3D|shorts\/|attribution_link\?a=.*&u=\/watch%3Fv%3D|attribution_link\?a=.*&u=https:\/\/www\.youtube\.com\/watch\?v%3D|attribution_link\?a=.*&u=https:\/\/www\.youtube\.com\/embed\/|attribution_link\?a=.*&u=\/embed\/|attribution_link\?a=.*&u=https:\/\/www\.youtube-nocookie\.com\/embed\/|attribution_link\?a=.*&u=\/e\/)([a-zA-Z0-9_-]{11})", url)
    yt_playlist_match = re.search(r"(?:https?:\/\/(?:www\.|m\.)?youtube\.com\/.*[?&]list=|https?:\/\/youtu\.be\/)([a-zA-Z0-9_-]*)", url)
    sp_track_match = re.search(r"open\.spotify\.com(?:\/intl-[a-z]{2})?\/(track|album|artist|playlist)\/([a-zA-Z0-9]+)", url)
    sp_code_match = re.search(r"spotify:(?:(user):[a-zA-Z0-9]+:)?(playlist|track|album):([a-zA-Z0-9]+)", url)
    raw_audio_match = re.search(r'(?:\.(mp3|wav|ogg|flac|m4a|aac|wma|aiff|ape|opus|mp4)$)|(?:audio%2F(mp3|wav|ogg|flac|m4a|aac|wma|aiff|ape|opus|mp4))', url, re.IGNORECASE)
    link_type, id = "unknown", None
    if yt_playlist_match:
        link_type, id = "playlist", yt_playlist_match.group(1)
    elif yt_vid_match:
        link_type, id = "video", yt_vid_match.group(1)
    elif sp_track_match:
        if sp_track_match.group(1) == 'artist': return link_type, id
        return f"sp_{sp_track_match.group(1)}", sp_track_match.group(2)
    elif sp_code_match:
        return "sp_"+sp_code_match.group(2), sp_code_match.group(3)
    elif raw_audio_match:
        return "raw_audio", None
    elif not checked:
        try:
            full_url = requests.get(url).url
            return check_link_type(full_url, checked=True)
        except requests.exceptions.RequestException as e:
            pass
    return link_type, id


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


def search_gif(query, api_key):
    query = re.sub(r'[^a-zA-Z0-9 ]', '', query)
    query = str(query).replace(' ', '+').replace('shorts', '')

    try:
        r = requests.get(f"https://tenor.googleapis.com/v2/search?q={query}&key={api_key}&limit=1")
        if r.status_code == 200:
            if not json.loads(r.content)['results']: return None
            return json.loads(r.content)['results'][0]['media_formats']['mediumgif']['url']
        else:
            return None

    except requests.RequestException as e:
        print(f"{api_request_error}: {e}")
        return None


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

