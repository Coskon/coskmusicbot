import os, re, json, ast
import requests
from urllib.parse import urlsplit
from base64 import b85encode, b85decode

VAR_AVAILABLE_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_loop', 'use_shuffle', 'use_info', 'use_lyrics', 'use_songs', 'use_steam', 'use_remove', 'use_goto', 'use_search', 'use_ping', 'use_avatar', 'use_level', 'use_chatgpt', 'use_seek', 'use_chords', 'use_genre', 'use_forward', 'use_options', 'use_fastplay', 'use_perms', 'use_add_prefix', 'use_del_prefix', 'use_pitch', 'use_rewind', 'use_restart_levels', 'use_add_perms', 'use_del_perms', 'use_available_perms', 'use_lang', 'use_vote_skip', 'use_volume', 'use_shazam', 'use_restrict', 'use_eq', 'use_autodj', 'use_download', 'use_reverse', 'use_playlist', 'use_change_channels']
VAR_DEFAULT_PERMS = ['use_help', 'use_play', 'use_leave', 'use_skip', 'use_join', 'use_pause', 'use_resume', 'use_queue', 'use_rewind', 'use_loop', 'use_info', 'use_goto', 'use_level', 'use_seek', 'use_genre', 'use_forward', 'use_fastplay', 'use_vote_skip', 'use_shazam', 'use_download', 'use_playlist']
VAR_ADMIN_PERMS = VAR_AVAILABLE_PERMS.copy()
FONT_DICT = {
    "normal": {},
    "monospace": {' ': '  ', 'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶', 'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽', 'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄', 'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉', 'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐', 'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕', 'm': '𝚖', 'n': '𝚗', 'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞', 'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣', '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺', '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿'},
    "smallcaps": {'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'v', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ'},
    "bubble": {'A': 'Ⓐ', 'B': 'Ⓑ', 'C': 'Ⓒ', 'D': 'Ⓓ', 'E': 'Ⓔ', 'F': 'Ⓕ', 'G': 'Ⓖ', 'H': 'Ⓗ', 'I': 'Ⓘ', 'J': 'Ⓙ', 'K': 'Ⓚ', 'L': 'Ⓛ', 'M': 'Ⓜ', 'N': 'Ⓝ', 'O': 'Ⓞ', 'P': 'Ⓟ', 'Q': 'Ⓠ', 'R': 'Ⓡ', 'S': 'Ⓢ', 'T': 'Ⓣ', 'U': 'Ⓤ', 'V': 'Ⓥ', 'W': 'Ⓦ', 'X': 'Ⓧ', 'Y': 'Ⓨ', 'Z': 'Ⓩ', 'a': 'ⓐ', 'b': 'ⓑ', 'c': 'ⓒ', 'd': 'ⓓ', 'e': 'ⓔ', 'f': 'ⓕ', 'g': 'ⓖ', 'h': 'ⓗ', 'i': 'ⓘ', 'j': 'ⓙ', 'k': 'ⓚ', 'l': 'ⓛ', 'm': 'ⓜ', 'n': 'ⓝ', 'o': 'ⓞ', 'p': 'ⓟ', 'q': 'ⓠ', 'r': 'ⓡ', 's': 'ⓢ', 't': 'ⓣ', 'u': 'ⓤ', 'v': 'ⓥ', 'w': 'ⓦ', 'x': 'ⓧ', 'y': 'ⓨ', 'z': 'ⓩ', '0': '⓪', '1': '➀', '2': '➁', '3': '➂', '4': '➃', '5': '➄', '6': '➅', '7': '➆', '8': '➇', '9': '➈'},
    "fullwidth": {' ': '  ', 'A': 'Ａ', 'B': 'Ｂ', 'C': 'Ｃ', 'D': 'Ｄ', 'E': 'Ｅ', 'F': 'Ｆ', 'G': 'Ｇ', 'H': 'Ｈ', 'I': 'Ｉ', 'J': 'Ｊ', 'K': 'Ｋ', 'L': 'Ｌ', 'M': 'Ｍ', 'N': 'Ｎ', 'O': 'Ｏ', 'P': 'Ｐ', 'Q': 'Ｑ', 'R': 'Ｒ', 'S': 'Ｓ', 'T': 'Ｔ', 'U': 'Ｕ', 'V': 'Ｖ', 'W': 'Ｗ', 'X': 'Ｘ', 'Y': 'Ｙ', 'Z': 'Ｚ', 'a': 'ａ', 'b': 'ｂ', 'c': 'ｃ', 'd': 'ｄ', 'e': 'ｅ', 'f': 'ｆ', 'g': 'ｇ', 'h': 'ｈ', 'i': 'ｉ', 'j': 'ｊ', 'k': 'ｋ', 'l': 'ｌ', 'm': 'ｍ', 'n': 'ｎ', 'o': 'ｏ', 'p': 'ｐ', 'q': 'ｑ', 'r': 'ｒ', 's': 'ｓ', 't': 'ｔ', 'u': 'ｕ', 'v': 'ｖ', 'w': 'ｗ', 'x': 'ｘ', 'y': 'ｙ', 'z': 'ｚ', '0': '０', '1': '１', '2': '２', '3': '３', '4': '４', '5': '５', '6': '６', '7': '７', '8': '８', '9': '９'},
    "double_struck": {'A': '𝔸', 'B': '𝔹', 'C': 'ℂ', 'D': '𝔻', 'E': '𝔼', 'F': '𝔽', 'G': '𝔾', 'H': 'ℍ', 'I': '𝕀', 'J': '𝕁', 'K': '𝕂', 'L': '𝕃', 'M': '𝕄', 'N': 'ℕ', 'O': '𝕆', 'P': 'ℙ', 'Q': 'ℚ', 'R': 'ℝ', 'S': '𝕊', 'T': '𝕋', 'U': '𝕌', 'V': '𝕍', 'W': '𝕎', 'X': '𝕏', 'Y': '𝕐', 'Z': 'ℤ', 'a': '𝕒', 'b': '𝕓', 'c': '𝕔', 'd': '𝕕', 'e': '𝕖', 'f': '𝕗', 'g': '𝕘', 'h': '𝕙', 'i': '𝕚', 'j': '𝕛', 'k': '𝕜', 'l': '𝕝', 'm': '𝕞', 'n': '𝕟', 'o': '𝕠', 'p': '𝕡', 'q': '𝕢', 'r': '𝕣', 's': '𝕤', 't': '𝕥', 'u': '𝕦', 'v': '𝕧', 'w': '𝕨', 'x': '𝕩', 'y': '𝕪', 'z': '𝕫', '0': '𝟘', '1': '𝟙', '2': '𝟚', '3': '𝟛', '4': '𝟜', '5': '𝟝', '6': '𝟞', '7': '𝟟', '8': '𝟠', '9': '𝟡'},
    "bold": {'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈', 'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓', 'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙', 'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠', 'h': '𝐡', 'i': '𝐢', 'j': '𝐣', 'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧', 'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭', 'u': '𝐮', 'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳', '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'},
    "bold_italic": {'A': '𝑨', 'B': '𝑩', 'C': '𝑪', 'D': '𝑫', 'E': '𝑬', 'F': '𝑭', 'G': '𝑮', 'H': '𝑯', 'I': '𝑰', 'J': '𝑱', 'K': '𝑲', 'L': '𝑳', 'M': '𝑴', 'N': '𝑵', 'O': '𝑶', 'P': '𝑷', 'Q': '𝑸', 'R': '𝑹', 'S': '𝑺', 'T': '𝑻', 'U': '𝑼', 'V': '𝑽', 'W': '𝑾', 'X': '𝑿', 'Y': '𝒀', 'Z': '𝒁', 'a': '𝒂', 'b': '𝒃', 'c': '𝒄', 'd': '𝒅', 'e': '𝒆', 'f': '𝒇', 'g': '𝒈', 'h': '𝒉', 'i': '𝒊', 'j': '𝒋', 'k': '𝒌', 'l': '𝒍', 'm': '𝒎', 'n': '𝒏', 'o': '𝒐', 'p': '𝒑', 'q': '𝒒', 'r': '𝒓', 's': '𝒔', 't': '𝒕', 'u': '𝒖', 'v': '𝒗', 'w': '𝒘', 'x': '𝒙', 'y': '𝒚', 'z': '𝒛', '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'},
    "fraktur": {'A': '𝔄', 'B': '𝔅', 'C': 'ℭ', 'D': '𝔇', 'E': '𝔈', 'F': '𝔉', 'G': '𝔊', 'H': 'ℌ', 'I': 'ℑ', 'J': '𝔍', 'K': '𝔎', 'L': '𝔏', 'M': '𝔐', 'N': '𝔑', 'O': '𝔒', 'P': '𝔓', 'Q': '𝔔', 'R': 'ℜ', 'S': '𝔖', 'T': '𝔗', 'U': '𝔘', 'V': '𝔙', 'W': '𝔚', 'X': '𝔛', 'Y': '𝔜', 'Z': 'ℨ', 'a': '𝔞', 'b': '𝔟', 'c': '𝔠', 'd': '𝔡', 'e': '𝔢', 'f': '𝔣', 'g': '𝔤', 'h': '𝔥', 'i': '𝔦', 'j': '𝔧', 'k': '𝔨', 'l': '𝔩', 'm': '𝔪', 'n': '𝔫', 'o': '𝔬', 'p': '𝔭', 'q': '𝔮', 'r': '𝔯', 's': '𝔰', 't': '𝔱', 'u': '𝔲', 'v': '𝔳', 'w': '𝔴', 'x': '𝔵', 'y': '𝔶', 'z': '𝔷'},
    "script": {'A': '𝒜', 'B': '𝐵', 'C': '𝒞', 'D': '𝒟', 'E': '𝐸', 'F': '𝐹', 'G': '𝒢', 'H': '𝐻', 'I': '𝐼', 'J': '𝒥', 'K': '𝒦', 'L': '𝐿', 'M': '𝑀', 'N': '𝒩', 'O': '𝒪', 'P': '𝒫', 'Q': '𝒬', 'R': '𝑅', 'S': '𝒮', 'T': '𝒯', 'U': '𝒰', 'V': '𝒱', 'W': '𝒲', 'X': '𝒳', 'Y': '𝒴', 'Z': '𝒵', 'a': '𝒶', 'b': '𝒷', 'c': '𝒸', 'd': '𝒹', 'e': '𝑒', 'f': '𝒻', 'g': '𝑔', 'h': '𝒽', 'i': '𝒾', 'j': '𝒿', 'k': '𝓀', 'l': '𝓁', 'm': '𝓂', 'n': '𝓃', 'o': '𝑜', 'p': '𝓅', 'q': '𝓆', 'r': '𝓇', 's': '𝓈', 't': '𝓉', 'u': '𝓊', 'v': '𝓋', 'w': '𝓌', 'x': '𝓍', 'y': '𝓎', 'z': '𝓏'},
}

def write_param(param_dict=None):
    threads = os.cpu_count() // 2
    with open('PARAMETERS.txt', 'w') as f:
        if param_dict is None:
            f.write(f"BOT_NAME = Coskquin  # name of your bot\n\n"
                    f"FONT = Normal\n\n"
                    f"MAX_VIDEO_LENGTH = 216000  # in seconds\n\n"
                    f"PLAYLIST_MAX_LIMIT = 1000  # max videos on playlist\n\n"
                    f"SPOTIFY_LIMIT = 200  # max videos for a spotify playlist/album\n\n"
                    f"TIMELIMIT = 40  # (in seconds) timelimit for the popup of the search choice embed\n\n"
                    f"REQUEST_LIMIT = 1.25  # (in seconds) time should pass between command calls from each user\n\n"
                    f"EMBED_COLOR = 0xff0000  # color for the side of the embed\n\n"
                    f"ITAGS_LIST = [22, 151, 132, 17, 36, 92, 5, 139, 140, 141, 249, 250, 251, 18]  # list of itags allowed, dont touch if not sure\n\n"
                    f"DEFAULT_SEARCH_LIMIT = 5  # how many videos to show using the search command by default\n\n"
                    f"DEFAULT_RECOMMENDATION_LIMIT = 15  # how many videos to show in recommendations by default\n\n"
                    f"LVL_PLAY_ADD = 1  # how much to add per play command called\n\n"
                    f"LVL_NEXT_XP = 25  # how much required xp added per next level\n\n"
                    f"LVL_BASE_XP = 25  # base xp required for the first level\n\n"
                    f"NUM_THREADS_HIGH = {threads if threads > 0 else 1}  # number of threads to use for tasks that need high performance\n\n"
                    f"NUM_THREADS_LOW = {threads // 2 if threads // 2 > 0 else 1}  # number of threads to use for tasks that don't need as much performance\n\n"
                    f"USE_LOGIN = False\n\n"
                    f"DOWNLOAD_PATH = downloads/  # download output folder\n\n"
                    f"DEFAULT_PREFIXES = ['.', '+', ',']  # prefixes to use by default\n\n"
                    f"EXCLUDED_CASES = ['._.', '.-.', ':)', '-.-']  # list of cases to exclude from being recognized as commands\n\n"
                    f"AVAILABLE_PERMS = {VAR_AVAILABLE_PERMS}  # all permissions available\n\n"
                    f"DEFAULT_USER_PERMS = {VAR_DEFAULT_PERMS}  # permissions each user gets by default\n\n"
                    f"ADMIN_PERMS = {VAR_ADMIN_PERMS}  # permissions admin users get by default\n\n"
                    f"USE_BUTTONS = True  # to use buttons to select a song, if False uses reactions\n\n"
                    f"USE_GRADIO = True  # use gradio for the user interface\n\n"
                    f"SKIP_TIMELIMIT = 15  # in seconds, timelimit for a skip vote\n\n"
                    f"MAX_SEARCH_SELECT = 15  # limit of youtube searching when choosing a song\n\n"
                    f"REFERENCE_MESSAGES = True  # whether for the bot to reference the user or not\n\n"
                    f"SKIP_PRIVATE_SEARCH = True  # whether or not to skip private/age restricted videos when searching\n\n"
                    f"AUTO_DJ_MAX_ADD = 3  # how many songs does the auto dj add each time\n\n"
                    f"QUEUE_VIDEOS_PER_PAGE = 30  # how many videos to show per page in the queue\n\n"
                    f"DISCONNECT_AFTER_QUEUE_END = False  # if disabled, the bot will stay connected after all songs end")
        else:
            param_text = "\n\n".join(f"{key} = {value}" for key, value in param_dict.items()) + "\n\n"
            f.write(param_text)


def read_param(prev_path=""):
    if not os.path.exists(prev_path+"PARAMETERS.txt"): write_param()
    with open(prev_path+"PARAMETERS.txt", 'r') as f:
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


def is_raw_data_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '').lower()
        mime_types = {
            'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac', 'audio/ogg', 'audio/mp4', 'audio/m4a'
            'video/mp4', 'video/msvideo', 'video/quicktime', 'video/ms-wmv', 'video/flv', 'video/matroska', 'video/webm',
            'application/vnd.apple.mpegurl', 'application/mpegurl'
        }
        x_mime_types = set(s.replace("/", "/x-") for s in mime_types)
        return content_type in mime_types | x_mime_types
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return False


def check_link_type(url, checked=False):
    if "&start_radio" in url: return "unknown", None
    yt_vid_match = re.search(r"(?:v=|\/videos\/|embed\/|\.be\/|\/v\/|\/e\/|watch\/|shorts\/|live\/|\/oembed\?url=https:\/\/www\.youtube\.com\/watch\?v=|watch%3Fv%3D|shorts\/|attribution_link\?a=.*&u=\/watch%3Fv%3D|attribution_link\?a=.*&u=https:\/\/www\.youtube\.com\/watch\?v%3D|attribution_link\?a=.*&u=https:\/\/www\.youtube\.com\/embed\/|attribution_link\?a=.*&u=\/embed\/|attribution_link\?a=.*&u=https:\/\/www\.youtube-nocookie\.com\/embed\/|attribution_link\?a=.*&u=\/e\/)([a-zA-Z0-9_-]{11})", url)
    yt_playlist_match = re.search(r"(?:https?:\/\/(?:www\.|m\.)?youtube\.com\/.*[?&]list=|https?:\/\/youtu\.be\/)([a-zA-Z0-9_-]*)", url)
    sp_track_match = re.search(r"open\.spotify\.com(?:\/intl-[a-z]{2})?\/(track|album|artist|playlist)\/([a-zA-Z0-9]+)", url)
    sp_code_match = re.search(r"spotify:(?:(user):[a-zA-Z0-9]+:)?(playlist|track|album):([a-zA-Z0-9]+)", url)
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
    elif is_raw_data_url(url):
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


def format_views(views: str | int):
    views = str(views)
    if not views.isnumeric(): return views
    views = views[::-1]
    return " ".join([views[i:i + 3] for i in range(0, len(views), 3)])[::-1]


def cut_string(input_string, max_length):
    if len(input_string) <= max_length:
        return input_string

    newline_position = input_string.rfind('\n', 0, max_length)
    cut_position = newline_position if newline_position != -1 else max_length

    return input_string[:cut_position], input_string[cut_position:]


def get_share_code(urls=None, gid="", playlist_name="", shortened=True):
    if shortened:
        return playlist_name+"%PL%"+gid
    if all(check_link_type(url)[0] == "video" for url in urls):
        return playlist_name+"%PL%"+"".join([url.replace("www.", "").replace(r"https://youtube.com/watch?v=", "") for url in urls])
    return playlist_name+"%PL%"+b85encode(bytes(";".join([url for url in urls]).encode())).decode()


def find_font(text):
    ret_text = ""
    FONT = read_param(prev_path='../')['FONT'].lower()
    font = FONT_DICT[FONT]
    perc = False
    for c in text:
        if c == '%': perc = True
        if c in {' ', '!', ')', '(', ']', '[', '¡', '?', '¿', '.', ',', ':', ';', '`'}: perc = False
        if c in font and not perc:
            ret_text += font[c]
        else:
            ret_text += c
    return ret_text

