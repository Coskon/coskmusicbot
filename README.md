# Coskquin: Cosk Music Bot
A *(probably not well made)* music bot for discord, made in python. You can modify it for your own purposes, but it wasn't originally meant to be published so it's messy, if you want something to be added you may open an issue with a feature request.

---

### NOW IN BETA (SOON TO RELEASE 1.0.0)
#### Important feature
Added support for a lot of different pages (for info on the possible pages with support, go [here](https://github.com/yt-dlp/yt-dlp/tree/master/yt_dlp/extractor), each .py file is a different website extractor). If you use a supposedly compatible url but it doesn't work, try running `format_extractor.py` with your URL and send me the output/open an issue. I'll add as much formats as possible. You might need to add a 'cookies.txt' file extracted from your browser to access some of these sites to the bot folder.

---
Changed from downloading the videos to streaming them, allowing for faster responses, no space issues, practically any video length, and it can now access livestreamings! However, this is still in beta (see the beta disclaimer below).  

Spotify support (convert from spotify to youtube). Most spotify links + codes should work of tracks, albums and playlists. Kinda slow (~10-15 seconds for a 100 track playlist), since it has to actually search, going any faster would require another library. 

Added support to play directly raw audio urls (such as the ones obtained from the yt downloader).  

Switched back to pytube from yt-dlp, though kept it for age restricted videos and livestreams. Everything now is much faster, and you don't have to login with pytube, or change its code or anything like that. However, the audio might cut though it rarely happens.

## Features
- Use YouTube URLs or search, choosing from songs on multiple pages.
- Accepts playlists.
- Livestreams (*only in beta*)
- Support for a lot of pages, including Twitch, SoundCloud, even twitter for some reason. (*only in beta*)
- Spotify to youtube conversion (*only in beta*)
- Auto DJ (*only in beta*)
- Play from file attachments (*only in beta*)
- Raw audio URLs support.
- Support for shortened links.
- English and Spanish languages.
- User permissions for each command.
- Can be used in multiple servers at the same time, meant for a few servers at most.
- Can have and modify multiple prefixes, even non single-characters prefixes.
- Time limitation between command calls.
- Lots of easily adjustable parameters.
- Majority skip for users without permission.
- Very simple level system.
- Miscellaneous commands to show your pfp, a steam profile, use chatgpt, etc...
- Gradio UI.
- And more...

## Recently added
- Queue changed, now with buttons to go to different pages, shuffle and reverse the queue.
- New command: `reverse`, reverses the queue.
- New command: `download [number]`, gives the link to download the current playing song (or the song specified with "number").
- Modified the command `chords`, now adding `-t [semitones]` to the query will traspose the chords.
- Play from file attachment(s): When using the `play` or `fastplay` commands, appart from the url/query, you can now attach audio files to the message (if it doesn't play then it's probably a incompatibility issue, though it seems to accept a lot). They will be added to queue in order of attachment, and they will be added first, before the url/query is processed.
- `shazam` and `autodj` are now faster for longer videos.
- New command: `autodj [query]`, alongside new parameter `AUTO_DJ_MAX_ADD`, gets related songs from the one it's currently playing/the user provided via query, and adds them to the queue each time the queue is about to end. By default it adds 3 each time. This automatically overrides the current loop mode, but changing the loop mode will override the autodj, so if you want to stop it you can `leave` or `loop [any loop mode]`.
- Slightly modified `nowplaying` command to be more accurate when retrieving the artist using the spotify API.
- New command: `eq [mode] [volume]`, alongside two quicker options, `bassboost` and `highboost`. "mode" is either bass/high, and "volume" is how much that band is turning up the volume.
- New command: `shazam [duration]`, takes a little segment of the currently playing song, gets it (like shazam) and gives info about it. "duration" is by default 15 seconds. Useful if you're listening to some sort of mix, livestream, etc. It's a little slower on livestreams, but in general 15 seconds tends to work great.
- New command/option: `restrict [channel]`, given the name of a text channel, it will restrict practically all bot messages to that channel (this disables referencing). Useful to set a "commands" channel. Reset it by putting no channel or "ALL_CHANNELS". See current channel it's restricted to in `options`.
- New parameters: `SKIP_PRIVATE_SEARCH` (ignore private/restricted videos when searching, makes searching faster), `SPOTIFY_LIMIT` (limit of tracks in a spotify playlist/album).

## Installation Guide
- Clone or [download](https://github.com/Coskon/coskmusicbot/archive/refs/heads/main.zip) the repository.
- Create a [Discord Application](https://discord.com/developers/docs/quick-start/getting-started).
- Put your discord api key (and any other of the optional api keys) on the `API_KEYS.txt` file.
- Run the `run.bat` script to initialize the bot (or `run_beta.bat` to run the beta).
- **(If `run.bat` didn't work)** Open a CMD on the project folder and input the following commands (windows):
    ```console
    python.exe -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    lang/lang.py
    bot.py
    ```
- **(Optional)** Run `gradio_ui.bat` to initialize the user interface to modify some options and parameters, or change them in `PARAMETERS.txt`.

### Guide for cloud services
If you don't want to have your computer running the bot or you want/need for it to be always active, you may need to use a cloud service.
I found "Replit" as a free alternative (you can go [here](https://replit.com/@mcgamescompany/Cosk-Music-Bot?v=1#main.py) and press "Use Template"), so i'll use that as the base, but following the general guide should work.
- Go to your chosen service and create a project. For Replit, select the "python discord bot" template.
- Upload the files; `bot.py` (you may rename it to `main.py` if necessary, as it is the case for Replit), `lang.py` in the folder `lang`, `extras.py`, `utilidades.py` and optionally other files.
- Set the secrets/enviroment variables (recommended for security reasons): `DISCORD_APP_KEY`, optionally; `TENOR_API_KEY`, `OPENAI_KEY`, `GENIUS_ACCESS_TOKEN`, `SPOTIFY_ID`, `SPOTIFY_SECRET`. Alternatively, you may set them in the `API_KEYS.txt` file, however this is not recommended, given that is a public site (specially in Replit, where the code is public for the free plan), using enviroment variables is better (and often easier) in this case.
- If you used enviroment variables, change `USE_PRIVATE_TOKENS` to `True` in both `bot.py` and `utilidades.py` (you can find it normally with Ctrl+F or with some search function your platform probably has).
- Before running the main file, find a way to run `lang.py`. In Replit, you can go to the "Shell" section, and run `python lang/lang.py`. This is only needed once for each time `lang.py` is changed.
- **Important:** Make sure your platform has FFMPEG and OPUS support. In Replit, you have to go to `replit.nix` (it's a hidden file), and add `pkgs.libopus` to  `deps = [ ... ]`.
- If the program doesn't automatically install/import the required packages, you may add the `requirements.txt` file and run `pip install -r requirements.txt` in the shell.
- Done! For Replit, you can just press "Run" (make sure `bot.py` is renamed to `main.py`) to run your bot.

## Important
- This script was only tested on WINDOWS, it might not work on other OS.
- If you were to delete all prefixes and don't want to mess with the .json files to add them back, simply use "DEF_PREFIX" as the prefix and call the `options default` or `add_prefix [prefix]` commands.
- ~~The first time playing a song, you might be prompted to login with a youtube account, just follow the instructions in the console. If you don't want to do that (which might block age restricted videos from being played), open the code and change the parameter `USE_LOGIN` to `False`.~~ No longer necessary.
- ~~Because of a problem with the library `pytube`, even if you login you will not be able to play age restricted videos. To fix this, go to `venv/Lib/site-packages/pytube`, open to edit `innertube.py` and in line 223, change `client='ANDROID_MUSIC'` into `client='ANDROID_CREATOR'`. (if you're using a cloud service, the path to the package might be a little different, try searching for a way to access "site-packages")~~ No longer necessary.
- ~~If you're using the beta, there is a problem with the library `youtube-dl`. To fix this go to `site-packages/youtube_dl/extractor/youtube.py`, at line 1794 (where it says 'uploader_id': ...) add a # at the beginning (aka comment out the line). If you're not convinced, instead change it to `'uploader_id': self._search_regex(r'/(?:channel|user)/([^/?&#]+)', owner_profile_url, 'uploader id', fatal=False) if owner_profile_url else None,`.~~ No longer necessary.

## Beta disclaimer
As the name indicates, it's in beta. It will not work as expected, at least not 100% of the time, have that in mind.  
Current beta feature: *Streaming audio instead of downloading it*.  
Why is in beta: *Will be released when i make new embeds/messages to make it look better. Bot cutting audio should be fixed.*

## Limitations
- ~~Only supports YouTube.~~ Not in the beta.
- Some commands will not work if the necessary API key is not provided or is incorrect (though those aren't really important).
- ~~When searching for results on YouTube, you have to wait for all the reactions to appear to be able to choose.~~ Added buttons! (you can still use reactions).
- ~~It has to download each video mp3, so it's limited by the host internet speed and disk space.~~ Not in the beta (still limited by internet speed).
- Bot language is global for all servers (cannot changed individually for each server). This will probably not be changed.
- User interface creates a separate venv occupying more space. Might change in the future. (couldn't initialize both threads at the same time and make them work correctly so i went with this)

## Known bugs
- If the bot is waiting for an input (like choosing a song), the bot will stop responding in every server until something is chosen or timeout. (might try to implement a better wait_for to fix this, however the bot isn't meant to be used in a big quantity of servers so it shouldn't be a huge problem)
- ~~Other users can interact with the buttons when choosing a song, because of this reactions are set by default instead.~~ Not anymore!
- ~~Anyone (including people outside the voice channel) can vote skip. This will probably not be fixed.~~ I lied, it is fixed.

## Command list
You can see aliases for each command using the bot. If you want to change the name or aliases of a command, search for the command in `bot.py` and replace `name=` and/or `aliases=` with the name/aliases you want.
- `help [command]`: Shows more information about the given command. If no command is provided, shows a list of all commands.
- `play [query]`: The query should be either a URL or what you want to search. If a URL is given, the song plays automatically (it can be a playlist), if not it will let you choose a video. You can also add audio attachments to be played (*only in beta*).
- `fastplay [query]`: Works the same as `play`, but skips having to choose.
- `leave`: Disconnects the bot from the voice channel and clears the song queue.
- `skip`: Skips to the next song, leaves if its the last song (unless loop is enabled). For users without permission, initiates a skip vote.
- `rewind`: Goes back to the previous song.
- `join`: Connects to the voice channel.
- `pause`: Pauses the current song.
- `resume`: Resumes the current song.
- `queue`: Shows the current queue.
- `remove [number]`: Removes the song at position "number" from the queue.
- `goto [number]`: Goes to the song at position "number" in the queue.
- `loop [mode]`: Changes the loop mode (`all/queue` repeats the whole queue, `shuffle/random` randomizes the next song each time, `one` repeats the current song and `off` disables it). If no mode is given, it switches between `all` and `off`.
- `seek [time]`: Goes to the given time, time can be given either in seconds or in HH:MM:SS format.
- `forward [time]`: Fast forwards or rewinds the specified time (depends if the time is positive or negative), time can be given either in seconds or in HH:MM:SS format.
- `volume [volume]`: Changes the volume of the current track, in percentage (from 0.01 to 300%) or dB (from -80 to 9.54dB)
- `shuffle`: Randomizes the order of the songs in the queue.
- `reverse`: Reverses the order of the queue.
- `autodj [query]`: Periodically gets similar songs from whats playing/the query (if given), and ads them to the queue.
- `shazam [duration]`: Tries to recognize the currently playing song and gives info about it. "duration" is the length of the clip to search, default is 15 (in seconds).
- `eq [type] [volume]`: Equalizes the track, types: "bass", "high". Volume in dB, from 0 to 12dB. This will be changed to be more in-depth.
- `bassboost`/`highboost`: Shortcuts for `eq` to boost the bass/high frequencies respectively.
- `nowplaying`: Shows information about the current song (title, artist, duration). **Requires Spotify API**
- `lyrics [song]`: Shows the lyrics of the specified song. If no song is given, it shows the lyrics of the song currently playing. **Requires Spotify and Genius API**
- `chords [song]`: Shows the chords of the specified song. If no song is given, it shows the chords of the song currently playing. Traspose the chords adding `-t [semitones]` to the query (*only in beta*). **Requires Spotify API**
- `songs [number] [artist]`: Shows the top "number" (10 by default) songs from the specified artist. If no artist is given, it will retrieve it from the song currently playing. **Requires Spotify API**
- `genre [genre]`: Shows songs of the given genre. If no genre is specified, shows the list of available genres to search. **Requires Spotify API**
- `search [platform] [query]`: Searches in youtube (by default) or spotify the given query and shows the results. **Requires Spotify API**
- `pitch [semitones] [speed]`: Changes the pitch of the song currently playing (positive for higher pitch, negative for lower pitch). You can also change the speed of the track, by default it will keep the same speed (*only in beta*).
- `nightcore`/`daycore`: Shortcuts for `pitch` to pitch up and speed up/pitch down and slow down the song respectively.
- `steam [user]`: Shows the steam profile of the specified user.
- `ping`: Shows the bot latency.
- `pfp`: Shows your profile picture.
- `level`: Shows your level and xp.
- `chatgpt [message]`: Answers the message using ChatGPT. **Requires OpenAI API**
- `perms`: Shows what permissions does the bot have in the server.
- `options [option] [value]`: Changes the option "option" to have the specified value. If no option is given, it shows the available options and its current values.
- `restrict [channel]`: Restricts practically all bot messages to the given channel. Use `restrict` or `restrict ALL_CHANNELS` to go back to default.
- `add_prefix [prefix]`: Add the specified prefix.
- `del_prefix [prefix]`: Removes the specified prefix.
- `available_perms`: Shows the list of all available permissions a user can have, and a list of the permissions a user has by default.
- `add_perm [name] [permission]`: Adds "permission" to the specified user (use ALL or * to affect everyone, use ALL or * to give every permission).
- `del_perm [name] [permission]`: Removes "permission" from the specified user (use ALL or * to affect everyone).
- `lang [language]`: Changes the language of the bot (english: en, spanish: es).

## To be added
A list of things that might get added:
### High priority
Features that would be nice to have right now.
- [ ] Linux/MAC support. (will be difficult to test as i don't have neither).
- [ ] Better looking embeds (alongside more information).
- [ ] Favorites (basically "custom playlists" for each server, so that they can easily be called with a single command and not have to add each video or make a yt playlist).
- [ ] Stop bot from pausing when selecting a song.

### Medium priority
Features that are not as important, but would be nice to have.
- [ ] Easier command customization.
- [ ] More audio effects.
- [ ] Interactive buttons to play, resume, etc.
- [ ] Certain things to be server-independant (reference messages, search limits for choosing a song, use buttons/reactions, etc).

### Low priority
Features that can wait.
- [ ] Improve the user interface to modify parameters.
- [ ] More info to the `steam` command.
- [ ] More in-depth equalization.







