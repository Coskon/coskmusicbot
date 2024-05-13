# Coskquin: Cosk Music Bot
A *(probably not well made)* music bot for discord, made in python. You can modify it for your own purposes, but it wasn't originally meant to be published so there are variable names in spanish, it's not commented (might add later) and in general it's better to add things that don't rely on the stuff that is already there (for example, you may add a command that retrieves information from a webpage, but don't try adding spotify support).
## Features
- User permissions for each command (by default, admins get all permissions and everyone else have a default set of permissions which you can change in the code).
- Can be used in multiple servers at the same time, with each one having its own.
- Can have and modify multiple prefixes, even non single-characters prefixes.
- Very simple level system.
- Commands to show your pfp, a steam profile, use chatgpt, etc...
- Use YouTube URLs or choose from 5 results.
- Time limitation between command calls.
- Lots of easily adjustable parameters.
- And more...

## Limitations
- There is no executable or .bat (for now), you have to use an IDE or any other way to run the program and modify/run the code from there.
- Only supports YouTube.
- Some commands will not work if the necessary API key is not provided or is incorrect (though those aren't really important).
- When searching for results on YouTube, you have to wait for all the reactions to appear to be able to choose.
- It has to download each video mp3, so it's limited by the host internet speed and disk space.

## Installation Guide
1) Clone or [download]() the repository.
2) Create a [Discord Application](https://discord.com/developers/docs/quick-start/getting-started).
3) Edit the file `bot.py`
    - Install all the necessary packages.
    - Change the `DISCORD_APP_KEY` to your discord app api key.
4) Edit the file `utilidades.py`
    - Install all the necessary packages.
    - **(Optional)** Add the API keys you have (spotify, openai, ...), needed to use some commands.
5) **(Optional)** Change the default prefixes, bot messages, excluded cases, or any other parameter you want.
6) Run `bot.py`
### Important
- The first time playing a song, you might be prompted to login with a youtube account, just follow the instructions in the console of your IDE. If you don't want to do that (which might block age restricted videos from being played), change the parameter `USE_LOGIN` to `False`.
- Because of a problem with the library `pytube`, even if you login you will not be able to play age restricted videos. To fix this, go to `venv/Lib/site-packages/pytube` and edit `innertube.py` and in line 223, change `client='ANDROID_MUSIC'` into `client='ANDROID_CREATOR'`.
- This script was only tested on WINDOWS, it might not work on other OS.
## Command list
You can see aliases for each command using the bot. If you want to change the name or aliases of a command, search for the command in `bot.py` and replace `name=` and/or `aliases=` with the name/aliases you want.
- `help [command]`: Shows more information about the given command. If no command is provided, shows a list of all commands.
- `play [query]`: The query should be either a URL or what you want to search. If a URL is given, the song plays automatically (it can be a playlist), if not it will let you choose a video.
- `fastplay [query]`: Works the same as `play`, but skips having to choose.
- `leave`: Disconnects the bot from the voice channel and clears the song queue.
- `skip`: Skips to the next song, leaves if its the last song (unless loop is enabled).
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
- `shuffle`: Randomizes the order of the songs in the queue.
- `nowplaying`: Shows information about the current song (title, artist, duration). **Requires Spotify API**
- `lyrics [song]`: Shows the lyrics of the specified song. If no song is given, it shows the lyrics of the song currently playing. **Requires Spotify and Genius API**
- `chords [song]`: Shows the chords of the specified song. If no song is given, it shows the chords of the song currently playing. **Requires Spotify API**
- `songs [number] [artist]`: Shows the top "number" (10 by default) songs from the specified artist. If no artist is given, it will retrieve it from the song currently playing. **Requires Spotify API**
- `genre [genre]`: Shows songs of the given genre. If no genre is specified, shows the list of available genres to search. **Requires Spotify API**
- `search [platform] [query]`: Searches in youtube (by default) or spotify the given query and shows the results. **Requires Spotify API**
- `pitch [semitones]`: Changes the pitch of the song currently playing (positive for higher pitch, negative for lower pitch).
- `steam [user]`: Shows the steam profile of the specified user.
- `ping`: Shows the bot latency.
- `pfp`: Shows your profile picture.
- `level`: Shows your level and xp.
- `chatgpt [message]`: Answers the message using ChatGPT. **Requires OpenAI API**
- `perms`: Shows what permissions does the bot have in the server.
- `options [option] [value]`: Changes the option "option" to have the specified value. If no option is given, it shows the available options and its current values.
- `add_prefix [prefix]`: Add the specified prefix.
- `del_prefix [prefix]`: Removes the specified prefix.
- `available_perms`: Shows the list of all available permissions a user can have, and a list of the permissions a user has by default.
- `add_perm [name] [permission]`: Adds "permission" to the specified user (use ALL to affect everyone).
- `del_perm [name] [permission]`: Removes "permission" from the specified user (use ALL to affect everyone).

## To be added
A list of things that might get added:
- Majority vote to skip/rewind for users without permission.
- More info to the `steam` command.
- Buttons instead of reactions to choose a song (since they are faster).
- Spotify support to play songs and playlists.
