# Coskquin: Cosk Music Bot
A music bot for discord made in python, self-hosted or using cloud services.

---

### Release: v1.0.0
Finally released!

Replit project updated.

## Features
- Use YouTube URLs or search, choosing from songs on multiple pages.
- Accepts playlists.
- Custom playlists for each server.
- Livestreams.
- Support for [a lot of pages](https://github.com/Coskon/coskmusicbot/blob/main/TESTED_SITES.md).
- Spotify to youtube conversion.
- Autoplay/Auto DJ.
- Play from file attachments.
- Raw audio URLs support.
- Support for shortened links.
- English and Spanish languages.
- Various fonts.
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
- Added spanish translation for the `help` message.
- Updated "current time" calculation to be more accurate, less consuming and more consistent across servers.
- Changed the `help` message, finally. Now it looks better and is divided into categories.
- Added `TESTED_SITED.md` to show which sites are tested and work. You can add to this list if you find any other site that works.
- Added the `use_parameter` permission, which by default nobody has. The only way to add it is by going into the json files of the server, this is to avoid people inviting the bot into a server they are admins and changing the parameters. You can find the server id using external tools and your user id inside discord, with that you can find yourself in the `user_perms_(guild id).json` file and add the `use_parameter` permission.
- Changed youtube search function to be faster, and search age restricted videos without compromising speed.

## Installation Guide
- Install [Python](https://www.python.org/downloads/).
- Clone or [download](https://github.com/Coskon/coskmusicbot/archive/refs/heads/main.zip) the repository.
- Create a [Discord Application](https://discord.com/developers/docs/quick-start/getting-started). It should have at least [these](https://imgur.com/a/FIytxLn) permissions (integer representation: 36711488), though this might change for future features.
- Put your Discord App Key (and any other of the optional api keys) on the `API_KEYS.txt` file.
- Run the `run.bat` script to initialize the bot.
- **(If `run.bat` didn't work)** Open a CMD on the project folder and input the following commands (Windows):
    ```console
    python.exe -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    pip install --upgrade yt-dlp
    bot.py
    ```
- **(Optional)** Run `gradio_ui.bat` to initialize the user interface to modify some options and parameters, or change them in `PARAMETERS.txt`.

### Guide for cloud services
If you don't want to have your computer running the bot or you want/need for it to be always active, you may want to use a cloud service.
I found "Replit" as a free alternative (you can go [here](https://replit.com/@mcgamescompany/Cosk-Music-Bot?v=1#main.py) and press "Use Template"), so i'll use that as the base, but following the general guide should work.
- Go to your chosen service and create a project. For Replit, select the "python discord bot" template.
- Upload the files; `bot.py` (you may rename it to `main.py` if necessary, as it is the case for Replit), `lang.py` in the folder `lang`, `extras.py`, `utilidades.py`, and optionally the other files.
- Set the secrets/enviroment variables (recommended for security reasons): `DISCORD_APP_KEY`, optionally; `TENOR_API_KEY`, `OPENAI_KEY`, `GENIUS_ACCESS_TOKEN`, `SPOTIFY_ID`, `SPOTIFY_SECRET`. Alternatively, you may set them in the `API_KEYS.txt` file, however this is not recommended, given that is a public site (specially in Replit, where the code is public for the free plan), using enviroment variables is better (and often easier) in this case.
- If you used enviroment variables, change `USE_PRIVATE_TOKENS` to `True` in both `bot.py` and `utilidades.py` (you can find it normally with Ctrl+F or with some search function your platform probably has).
- If the platform gives you an error saying "module extras doesn't exist" or similar, put `extras.py` into the `site-packages` folder.
- **Important:** Make sure your platform has FFMPEG and OPUS support. In Replit, you have to go to `replit.nix` (it's a hidden file), and add `pkgs.libopus` to  `deps = [ ... ]`. Also, it should have the `rubberband` filter, for some reason Replit doesn't have it and i couldn't find a way to install it, so in that case go to `bot.py`, find "rubberband" and remove it from the ffmpeg options string.
- If the program doesn't automatically install/import the required packages, you may add the `requirements.txt` file and run `pip install -r requirements.txt` in the shell.
- Done! For Replit, you can just press "Run" (make sure `bot.py` is renamed to `main.py`) to run your bot.

## Important
- This script was only tested on Windows, it might not work on other OS.
- If you were to delete all prefixes and don't want to mess with the .json files to add them back, simply use "DEF_PREFIX" as the prefix and call the `options default` or `add_prefix [prefix]` commands.

## Limitations
- Some commands will not work if the necessary API key is not provided or is incorrect.
- Bot language is global for all servers (cannot changed individually for each server). This will probably not be changed.
- User interface creates a separate venv occupying more space. Might change in the future.

## Known bugs
- If the bot is waiting for an input (like choosing a song), the `play` command (and related) will not work until something is chosen or timeout. This might be fixable, but it's not high priority since the bot is not meant to be used in a lot of servers.
- Current time isn't affected by the speed of the song. This will probably not be fixed soon as it is not that important.

## Command list
You can see aliases for each command using the bot `help` command. If you want to change the name or aliases of a command, search for the command in `bot.py` and replace `name=` and/or `aliases=` with the name/aliases you want.
- `help [command]`: Shows more information about the given command. If no command is provided, shows a list of all commands.
- `play [query]`: The query should be either a URL or what you want to search. If a URL is given, the song plays automatically (it can be a playlist), if not it will let you choose a video. You can also add audio attachments to be played.
- `fastplay [query]`: Works the same as `play`, but skips having to choose.
- `leave`: Disconnects the bot from the voice channel and clears the song queue.
- `skip`: Skips to the next song. For users without permission, initiates a skip vote.
- `rewind`: Goes back to the previous song.
- `join`: Connects to the voice channel.
- `pause`: Pauses the current song.
- `resume`: Resumes the current song.
- `queue`: Shows the current queue.
- `remove [number]`: Removes the song at position "number" from the queue.
- `goto [number]`: Goes to the song at position "number" in the queue.
- `loop [mode]`: Changes the loop mode (`all/queue` repeats the whole queue, `shuffle/random` randomizes the next song each time, `one` repeats the current song, `autodj` enables autoplay and `off` disables it). If no mode is given, it switches between `all` and `off`.
- `seek [time]`: Goes to the given time, time can be given either in seconds or in HH:MM:SS format.
- `forward [time]`: Fast forwards the specified time, time can be given either in seconds or in HH:MM:SS format.
- `backwards [time]`: Rewinds the specified time, time can be given either in seconds or in HH:MM:SS format.
- `volume [volume]`: Changes the volume of the current track, in percentage (from 0.01 to 300%) or dB (from -80 to 9.54dB)
- `shuffle`: Randomizes the order of the songs in the queue.
- `reverse`: Reverses the order of the queue.
- `playlist [mode] [playlist name] [query]`: Manage custom playlists, available modes: `create`, creates the playlist with the given `playlist name`. `names`, to see the playlists created. `add`, to add the query or current song to the playlist. `addqueue`, to add the current queue to the playlist. `remove`, to remove a song from the playlist by its number position (given as `query`). `clear`, to remove all songs from a playlist. `list` to see the songs on a playlist. `play` to add the playlist to the queue. `delete` to delete a playlist. `share` to get a code to share the playlist to other servers (requires bot to be hosted by the same person). `sharecomp`, same as `share` but it works even with different hosts of the bot (as long as they are up to date). `load` to load a code, which can be given in the command itself or by attaching a .txt file (when using `sharecomp` due to the large length of these codes).
- `autodj [query]`: Periodically gets similar songs from whats playing/the query (if given), and ads them to the queue.
- `shazam [duration]`: Tries to recognize the currently playing song and gives info about it. "duration" is the length of the clip to search, default is 15 (in seconds).
- `eq [type] [volume]`: Equalizes the track, types: "bass", "high". Volume in dB, from 0 to 12dB. This will be changed to be more in-depth.
- `bassboost`/`highboost`: Shortcuts for `eq` to boost the bass/high frequencies respectively.
- `mono`/`stereo`: Convert the audio to mono (single channel) or stereo (two channels). All audio by default is on stereo.
- `nowplaying`: Shows information about the current song (title, artist, duration). **Requires Spotify API**
- `lyrics [song]`: Shows the lyrics of the specified song. If no song is given, it shows the lyrics of the song currently playing. **Requires Spotify and Genius API**
- `chords [song]`: Shows the chords of the specified song. If no song is given, it shows the chords of the song currently playing. Traspose the chords adding `-t [semitones]` to the query. **Requires Spotify API**
- `songs [number] [artist]`: Shows the top "number" (10 by default) songs from the specified artist. If no artist is given, it will retrieve it from the song currently playing. **Requires Spotify API**
- `genre [genre]`: Shows songs of the given genre. If no genre is specified, shows the list of available genres to search. **Requires Spotify API**
- `search [platform] [query]`: Searches in youtube (by default) or spotify the given query and shows the results. **Requires Spotify API**
- `pitch [semitones] [speed]`: Changes the pitch of the song currently playing (positive for higher pitch, negative for lower pitch). You can also change the speed of the track, by default it will keep the same speed.
- `nightcore`/`daycore`: Shortcuts for `pitch` to pitch up and speed up/pitch down and slow down the song respectively.
- `download [number]`: Gives a link to download the song currently playing, or the one specified in `number`.
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
- `parameter [name] [value]`: Changes the value of the specified parameter to the one given, shows its value if no value is given or shows a list of the parameters otherwise.

## To be added
A list of things that might get added:
### High priority
Features that would be nice to have right now.
- [ ] Linux/MAC support. (will be difficult to test as i don't have neither).
- [ ] Stop bot from pausing when selecting a song.
- [ ] DJ Role or similar.

### Medium priority
Features that are not as important, but would be nice to have.
- [ ] Easier command customization.
- [ ] More audio effects.
- [ ] Interactive buttons to play, resume, etc.
- [ ] Certain things to be server-independant (reference messages, search limits for choosing a song, use buttons/reactions, etc).
- [ ] Audio volume normalizer between all tracks (so that they all play at the same perceived volume) and volume normalization for individual tracks (to remove excessive dynamic range).

### Low priority
Features that can wait.
- [ ] More info to the `steam` command.
- [ ] More in-depth equalization.
- [ ] Improved readme with more detail on each commands, all aliases, etc.







