import spotipy, lyricsgenius
import asyncio, json, requests
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from spotipy.oauth2 import SpotifyClientCredentials
from openai import OpenAI
from pyppeteer import launch


GENIUS_API_BASE_URL = "https://api.genius.com"
GENIUS_ACCESS_TOKEN = ''
SPOTIFY_ID = ''
SPOTIFY_SECRET = ''
TENOR_API_KEY = ''
OPENAI_KEY = ''

client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_ID, client_secret=SPOTIFY_SECRET) if SPOTIFY_ID and SPOTIFY_SECRET else None

available_genres = [
    'acoustic', 'afrobeat', 'alt-rock', 'alternative', 'ambient', 'anime', 'black-metal', 'bluegrass', 'blues', 'bossanova',
    'brazil', 'breakbeat', 'british', 'cantopop', 'chicago-house', 'children', 'chill', 'classical', 'club', 'comedy',
    'country', 'dance', 'dancehall', 'death-metal', 'deep-house', 'detroit-techno', 'disco', 'disney', 'drum-and-bass',
    'dub', 'dubstep', 'edm', 'electro', 'electronic', 'emo', 'folk', 'forro', 'french', 'funk', 'garage', 'german', 'gospel',
    'goth', 'grindcore', 'groove', 'grunge', 'guitar', 'happy', 'hard-rock', 'hardcore', 'hardstyle', 'heavy-metal', 'hip-hop',
    'holidays', 'honky-tonk', 'house', 'idm', 'indian', 'indie', 'indie-pop', 'industrial', 'iranian', 'j-dance', 'j-idol',
    'j-pop', 'j-rock', 'jazz', 'k-pop', 'kids', 'latin', 'latino', 'malay', 'mandopop', 'metal', 'metal-misc', 'metalcore',
    'minimal-techno', 'movies', 'mpb', 'new-age', 'new-release', 'opera', 'pagode', 'party', 'philippines-opm', 'piano',
    'pop', 'pop-film', 'post-dubstep', 'power-pop', 'progressive-house', 'psych-rock', 'punk', 'punk-rock', 'r-n-b',
    'rainy-day', 'reggae', 'reggaeton', 'road-trip', 'rock', 'rock-n-roll', 'rockabilly', 'romance', 'sad', 'salsa', 'samba',
    'sertanejo', 'show-tunes', 'singer-songwriter', 'ska', 'sleep', 'songwriter', 'soul', 'soundtracks', 'spanish', 'study',
    'summer', 'swedish', 'synth-pop', 'tango', 'techno', 'trance', 'trip-hop', 'turkish', 'work-out', 'world-music'
]


def get_steam_avatar(profile_url):
    try:
        # Send an HTTP GET request to the Steam profile URL
        response = requests.get(profile_url)
        response.raise_for_status()

        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the parent div element with class "playerAvatarAutoSizeInner"
        avatar_div = soup.find('div', class_='playerAvatarAutoSizeInner')
        if not avatar_div: return None
        # Find all nested img elements within the avatar_div
        img_tags = avatar_div.find_all('img')

        # Check if there is a second img tag
        if len(img_tags) >= 2:
            # Extract the avatar image URL from the second img tag
            avatar_url = img_tags[1]['src']
            return avatar_url

        return None

    except requests.RequestException as e:
        print(f"Error: {e}")
        return None


def convert_seconds(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours == 0:
        return "{:0}:{:02d}".format(int(minutes), int(seconds))
    else:
        return "{:0}:{:02d}:{:02d}".format(int(hours), int(minutes), int(seconds))


def get_bar(total, progress, length=20):
    filled_length = int(length * progress // total)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[:arrow_forward:|:pause_button:|:stop_button:] {bar} [`{convert_seconds(progress)}`/`{convert_seconds(total)}`]"


def get_spotify_artist(query, is_song=False):
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    if is_song:
        # If the input is a song, search for the song and extract the artist's name
        results = sp.search(q=query, type='track')
        if results['tracks']['items']:
            return results['tracks']['items'][0]['artists'][0]['name']
    else:
        # If the input is an artist name, search for the artist and return the name
        results = sp.search(q=query, type='artist')
        if results['artists']['items']:
            return results['artists']['items'][0]['name']
    return None


def get_spotify_song(song_name):
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    # Search for the song
    results = sp.search(q=song_name, type='track')

    if results['tracks']['items']:
        return results['tracks']['items'][0]['name']
    return None


def get_artist_and_song(query, better=True):
    if not better:
        # Replace 'your_access_token' with your Genius.com API access token
        query = query.lower().replace('live', '').replace('remix', '').replace('mtv', '').replace('version', '') \
            .replace('official video', '').replace('official audio', '').replace('video', '').replace('audio', '') \
            .replace('squeaky clean', '').replace('clean', '').replace('[]', '').replace('()', '').strip()
        genius = lyricsgenius.Genius("your_access_token", excluded_terms=["(Remix)", "(Live)"])
        # Search for the given query
        search_result = genius.search_song(query)

        # Check if a result is found
        if search_result:
            artist = search_result.artist
            song = search_result.title
            return artist, song
        else:
            return None, None
    return get_spotify_artist(query, is_song=True), get_spotify_song(query)


def get_lyrics(song_title, tupla_a_s=(None, None)):
    try:
        if not all(tupla_a_s): artist, song = get_artist_and_song(song_title)
        else: artist, song = tupla_a_s
        genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, skip_non_songs=True, excluded_terms=["(Remix)", "(Live)"])
        song = genius.search_song(song, artist)
        lyrics = str(song.lyrics)
        index1 = lyrics.find("Lyrics")
        index2 = lyrics.find("Embed")
        for i in range(1, 100):
            if not lyrics[index2-i].isnumeric():
                break
        lyrics = lyrics[index1+6:index2-i+1].replace('You might also like', '').replace('\n\n','\n').replace('[', '\n**[').replace(']', ']**')
        return lyrics
    except Exception as e:
        return None, "Error al buscar la letra."


def get_top_songs(artist_name, n):
    # Authenticate with the Spotify API
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    # Search for the artist
    results = sp.search(q=artist_name, type='artist')

    # Check if the artist is found
    if len(results['artists']['items']) == 0:
        return None

    artist_id = results['artists']['items'][0]['id']

    # Get the top tracks of the artist
    top_tracks = sp.artist_top_tracks(artist_id)['tracks']

    # Extract the top N tracks
    top_n_tracks = top_tracks[:n]

    # Print the top N tracks
    tracks_list = list()
    for i, track in enumerate(top_n_tracks, start=1):
        tracks_list.append(f"{track['name']}")
    return tracks_list


def get_artist_image_url(artist_name):
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    # Search for the artist
    results = sp.search(q=artist_name, type='artist')

    # Check if the artist is found
    if len(results['artists']['items']) == 0:
        return f"Artist '{artist_name}' not found on Spotify."

    artist_id = results['artists']['items'][0]['id']

    # Get the artist's details
    artist_details = sp.artist(artist_id)

    # Get the URL of the artist's image
    image_url = artist_details['images'][0]['url'] if artist_details['images'] else None

    return image_url


def spotify_search(query, lim=5):
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    results = sp.search(q=query, limit=lim, type='track')
    top_results = []
    for track in results['tracks']['items']:
        track_info = {
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'url': track['external_urls']['spotify'],
            'image_url': track['album']['images'][0]['url']  # Extracting the first image URL from the album
        }
        top_results.append(track_info)

    return top_results


def genre_spotify_search(user_query, lim=15):
    if not user_query: user_query = "available"
    user_query = user_query.lower()
    mr1, mr2 = fuzz.ratio(user_query, 'available'), fuzz.ratio(user_query, 'disponible')
    if mr1 > 85 or mr2 > 85: return available_genres, True
    chosen_genre = max(available_genres, key=lambda genre: fuzz.ratio(user_query, genre.lower()))
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    results = sp.search(q=f"genre:{chosen_genre}", limit=lim, type='track')
    top_results = []
    for track in results['tracks']['items']:
        track_info = {
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'url': track['external_urls']['spotify'],
            'image_url': track['album']['images'][0]['url']  # Extracting the first image URL from the album
        }
        top_results.append(track_info)

    return top_results, False, chosen_genre


def chatgpt(msg, OPENAI_KEY):
    openai_client = OpenAI(api_key=OPENAI_KEY)
    context = {"role": "system",
               "content": "You are ChatGPT. You are a useful chatbot which responds to whatever the user says in either "
                          "english or spanish depending on the user's input. If possible, respond with short and concise answers."}
    response = openai_client.chat.completions.create(messages=[context,{"role": "user", "content": msg}], model="gpt-3.5-turbo" )
    return response.choices[0].message.content


async def search_cifraclub(query):
    browser = await launch()
    page = await browser.newPage()

    search_url = f"https://www.cifraclub.com/?q={query}"
    await page.goto(search_url, {'waitUntil': 'domcontentloaded'})

    # Wait for some time to allow dynamic content to load (adjust as needed)
    await asyncio.sleep(1)

    # Get the HTML content after dynamic loading
    content = await page.content()

    # Close the browser
    await browser.close()

    soup = BeautifulSoup(content, 'html.parser')
    result = soup.find('div', class_='gs-title')

    if result:
        song_url = result.find('a')['href']
        song_page = requests.get(song_url)

        if song_page.status_code == 200:
            song_soup = BeautifulSoup(song_page.text, 'html.parser')
            chords_and_lyrics = song_soup.find('pre')
            if chords_and_lyrics:
                chords_and_lyrics = str(chords_and_lyrics).replace('<pre>', '').replace('</pre>', '').replace('  ', ' \-').replace('<b>', '`').replace('</b>', '`')
                return chords_and_lyrics
            else:
                print("Lyrics not found.")
        else:
            print(f"Error accessing the song's page. Status code: {song_page.status_code}")
    else:
        print("Link to the song not found in the first result.")


def get_chords_and_lyrics(query):
    base_url = "https://www.ultimate-guitar.com"
    search_url = f"{base_url}/search.php"
    params = {
        'search_type': 'title',
        'order': 'date',
        'value': f"{query}"
    }
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        result = soup.find('div', class_='js-store')
        search_results = json.loads(result['data-content']).get('store', {})['page']['data']['results']
        song_url = None
        for res in search_results:
            if 'pro' not in res['tab_url']:
                song_url = res['tab_url']
                break
        if not song_url:
            return None
        song_page = requests.get(song_url)

        if song_page.status_code == 200:
            song_soup = BeautifulSoup(song_page.text, 'html.parser')
            lyrics_div = song_soup.find('div', class_='js-store')

            if lyrics_div:
                data_content = lyrics_div['data-content']
                content_json = json.loads(data_content)
                chords_and_lyrics = content_json.get('store', {}).get('page', {}).get('data', {}).get('tab_view', {}).get('wiki_tab', '').get('content', {})
                if "[Intro]" in chords_and_lyrics: chords_and_lyrics = chords_and_lyrics[chords_and_lyrics.find("[Intro]"):]
                chords_and_lyrics = chords_and_lyrics.replace('  ', ' \-').replace('[ch]', '`').replace('[/ch]', '`').replace('[tab]', '').replace('[/tab]', '')
                return chords_and_lyrics
            else:
                print("Lyrics not found.")
        else:
            print(f"Error accessing the song's page. Status code: {song_page.status_code}")
    else:
        print(f"Error searching for the song. Status code: {response.status_code}")

