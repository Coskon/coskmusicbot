import json, os
from extras import find_font, read_param

if os.path.exists("../"+"PARAMETERS.txt"):
    FONT = read_param(prev_path='../')['FONT'].lower()
else:
    FONT = read_param()['FONT'].lower()


### ENGLISH ###
if True: # only to minimize
    already_connected_texts = ["I'm already connected.", "I'm already here."]
    entering_texts = ["Entering ", "Going into "]
    nothing_on_texts = ["Nothing is playing."]
    song_not_chosen_texts = [f"Selection timed out."]
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
    not_connected_texts = ["I'm not connected to a voice channel."]
    different_channel_texts = ["We are not in the same channel."]
    api_key_not_found = "not found. Go into 'API_KEYS.txt' to set it."
    api_request_error = "Error making API request"
    invalid_time_format = "Invalid time format. Please use either HH:MM:SS or MM:SS."
    generic_error = "Error"
    processing_error = "Error processing"
    couldnt_find_audiofile = "Error: Couldn't find audio file."
    logged_in = "Logged in as"
    command_from = "Command from"
    wait_seconds = "%name, wait `%time` seconds."
    help_title = "ℹ️ — Help"
    help_desc = "Command list -> command [use] (aliases) | Prefixes: %prefix:"
    bot_perms = "⚙️ — %botname permissions in %server"
    couldnt_find_user = "Couldn't find user `%name`."
    invalid_perm = "Permission `%perm` is not a valid permission, use `available_perms`."
    perm_added_everyone = "Permission `%perm` added to *everyone*."
    perm_added = "Permission `%perm` added to `%name`."
    perm_already_added = "`%name` already has `%perm` permission."
    all_perms_added = "Every permission added to `%name`."
    all_perms_everyone = "Every permission added to everyone."
    perm_del_everyone = "Permission `%perm` removed from everyone."
    perm_not_added = "`%name` doesn't have `%perm` permission."
    perm_removed = "Permission `%perm` removed from `%name`."
    available_perms_title = "⚙️ — **Available perms**"
    default_perms_title = "⚙️ — **Default perms**"
    song_info_title = "ℹ️ — **Information of the song**"
    song_info_desc = "➤ **Title**: %title\n➤ **Artist**: %artist\n➤ **Channel**: %channel\n➤ **Duration**: `%duration`\n\n %bar"
    config_title = "⚙️ — Configuration"
    config_desc = "➤ Options: `search_limit=%search_limit`, `recomm_limit=%recomm_limit`, `custom_prefixes=%custom_prefixes`, `restricted_to=%restricted_to`."
    config_changed = "➤ `%option` changed from `%original` to `%newvalue`"
    config_default = "➤ `search_limit` changed from `%sl` to `%def_sl`\n" \
                        "➤ `recomm_limit` changed from `%rl` to `%def_rl`\n" \
                        "➤ `custom_prefixes` changed from `%cust_p` to `%def_cust_p`\n"
    youtube_search_title = "🔎 — YouTube search results"
    spotify_search_title = "🔎 — Spotify search results"
    spotify_search_desc = "➤ **Title**: [%name](%url) | **Artist**: %artist\n"
    available_genres = "🎸 — Available genres"
    genre_search_title = "🔎 — Spotify search results by genre: %genre"
    choose_song_title = "🔍 — Choose a song (Page %page)"
    playlist_added_title = "📜 — Playlist added"
    playlist_added_desc = "**%name** put **%title** in *%ch_name*!\nA total of `%pl_length` songs have been added."
    playlist_max_reached = "The playlist has `%pl_length` videos, `%over` more than the maximum. The last `%discarded` videos were discarded."
    playlist_link = "Playlist link"
    playlist_link_desc = '%url\n\n➤ **Title**: *%title*'
    playlist_link_desc_time = "\n➤ **Total duration**: `%duration`"
    playlist_videos_unavailable = "The playlist has `%total` videos, from which `%unavailable` are unavailable."
    video_max_duration = "Video is too long (`%video_limit` limit)."
    song_selected = "Chosen: %title"
    song_chosen_title = "Song chosen"
    raw_audio_desc = "¡**%name** put an audio in *%ch_name*!"
    all_selected = "All songs from page %page chosen."
    song_chosen_desc = "**%name** put **[%title](%url)** in *%ch_name*!"
    added_queue_title = "Added to queue"
    added_queue_desc = "**%name** added **[%title](%url)** to the queue."
    word_title = "Title"
    word_duration = "Duration"
    word_views = "Views"
    level_title = "📶 — Level menu"
    level_desc = "➤ **Name**: %name\n➤ **LVL**: `%level`\n➤ **XP**: `%xp/%next_xp`"
    removed_from_queue = "Deleted from queue: *%title*"
    fast_forwarding = "%emoji — Fast forward"
    rewinding = "%emoji — Rewinding"
    forward_title = "**%modetype %sec to %time**"
    seek_title = "⏱️ — Playback Position Updated"
    not_loop_mode = f"`%mode` is not a loop mode, use `queue/all`, `shuffle/random`, `one` or `off`."
    loop_disable = "Loop disabled."
    loop_mode_changed = "Loop mode: `%loop`."
    queue_title = "🎶 — Song Queue"
    queue_pages = "Page"
    queue_videos = "Songs"
    queue_duration = "Duration"
    queue_current = "` ⮜ **Current song**"
    profile_title = "👤 — Profile picture of %name"
    steam_title = "👤 — Steam profile of %name"
    chatgpt_title = "🤖 — ChatGPT Response"
    lyrics_title = "ℹ️ — Information"
    lyrics_desc = f"➤ **Title**: %title\n➤ **Artist**: %artist"
    top_songs_title = "🔝 — Top %number songs of %artist"
    chords_title = "🎼 — Chords of %song, %artist"
    tuning_embed_title = "ℹ️ — Tuning information"
    tuning_embed_desc = "➤ **Tonality**: %tonality\n➤ **Capo**: %capo%th\n➤ **Tuning**: %tuning_value (%tuning_name)\n➤ **Trasposed**: %traspose"
    no_capo_chords = "No capo"
    pitch_title = "🎤 - Pitch changed"
    pitch_desc = "➤ **Pitch**: %sign%tone\n➤ **Speed**: x%speed"
    volume_title = "🎚️ — Volume changed"
    volume_desc = "➤ **Volume**: %vol"
    eq_title = "🎛️ — Equalization"
    eq_desc = "➤ **Frequency**: %freq\n➤ **Width**: %width\n➤ **Volume**: %vol"
    prefix_add_title = "⚙️ — Prefix added"
    prefix_add_desc = "➤ Prefix `%prefix` has been added. Prefixes: `%prfixes`"
    prefix_del_title = "⚙️ — Prefix removed"
    prefix_del_desc = "➤ Prefix `%prefix` has been removed. Prefixes: `%prfixes`"
    lang_changed = "Hello!"
    vote_skip_text = "Song skip vote: %num needed."
    song_skipped = "Song skipped."
    queue_reversed = "Queue order reversed."
    searching_text = "Searching..."
    recognizing_song = "Listening..."
    shazam_title = "✅ — Song found"
    shazam_desc = f"➤ **Title**: %title\n➤ **Artist**: %artist\n➤ **Album**: %album\n➤ **Genre%plural**: %genres\n\n%url"
    shazam_no_song = f"Couldn't recognize song. Try using a longer time; `shazam [duration]`."
    no_album_info_found = "No information."
    autodj_added_songs = "Added `%num` related songs to queue."
    autodj_no_song = "Couldn't retrieve information."
    cannot_change_time_live = "Cannot use `%command` on a live video."
    couldnt_load_song = "Couldn't load song (private/age restricted): %title."
    already_on_another_vc = "I'm already on another channel."
    channel_doesnt_exist = "`%name` doesn't exist."
    restricted_to_channel = "Now i will only send messages in `%name`."
    cant_access_channel = "`%name` is private and i don't have access to it."
    not_restricted = "Now i can send messages to all channels."
    download_url = "Click [here](%url) to download.\nOriginal link [here](%original_url)."
    cannot_download_live = "Downloading LIVE videos is not supported."
    cannot_download_m3u8 = "Can't download this song."
    no_playlists_created = "No playlists created in `%server_name`. Use `playlist create [name]`."
    playlist_list_title = "🎹 — Playlists"
    playlist_list_desc = "%playlists"
    playlist_created = "Playlist `%pl_name` created. Add songs using `playlist add %pl_name [song]`."
    playlist_already_exists = "Playlist `%pl_name` already exists."
    playlist_not_found = "Playlist `%pl_name` not found. Use `playlist names` to see the playlists available in this server."
    playlist_no_songs = "Playlist `%pl_name` has no songs in it. Use `playlist add %pl_name [song]`."
    added_to_playlist_url = "[%title](%url) added to `%pl_name`."
    playlist_played = "Playlist `%pl_name` added to queue."
    playlist_cleared = "Playlist `%pl_name` cleared."
    playlist_deleted = "Playlist `%pl_name` deleted."
    removed_from_playlist = "[Song %number](%url) removed from `%pl_name`."
    queue_added_to_playlist = "Current queue added to `%pl_name`, `%num_songs` songs added."
    shared_playlist_code = "Playlist code: `%code`. Use `playlist load [code]` to load it."
    playlist_loaded = "Playlist `%pl_name` loaded with `%len` videos."
    playlist_created_by = "Created by %name"
    playlist_title = "📜 — Playlist: "
    playlist_info = "songs, by *%name*"
    change_channels_mode = "Changed audio to `%mode`."
    missing_parameters = "ATTENTION: Missing parameter, file will be rewritten and parameters will be changed to default.\nPress 'Enter' to proceed."
    invalid_parameter = "Invalid parameter, use `parameters` to see the list of available parameters."
    parameters_to_default = "Parameters reverted to default."
    parameter_changed_value = "Parameter `%pname` changed to `%value`."
    song_queue_ended = "Song queue ended."
    command_desc_help = f"➤ Use: `help [nothing/command]`\n➤ Aliases: `h`\n" \
                          f"➤ Description: Shows all commands, if a command is given it shows more info about it."
    command_desc_play = f"➤ Use: `play [query or url] [nothing/-opt option]`\n➤ Aliases: `p`\n" \
                          f"➤ Description: Plays the given song. If -opt gif is added at the end, a gif is added (try it!)."
    command_desc_leave = f"➤ Use: `leave`\n➤ Aliases: `l`, `dis`, `disconnect`, `d`\n" \
                           f"➤ Description: Disconnects the bot from the voice channel and clears the queue."
    command_desc_skip = f"➤ Use: `skip`\n➤ Aliases: `s`, `next`\n" \
                          f"➤ Description: Skips to the next song."
    command_desc_join = f"➤ Use: `join`\n➤ Aliases: `connect`\n" \
                          f"➤ Description: Connects to the voice channel."
    command_desc_pause = f"➤ Use: `pause`\n➤ Aliases: `stop`\n" \
                           f"➤ Description: Pauses the song."
    command_desc_resume = f"➤ Use: `resume`\n" \
                            f"➤ Description: Resumes the song."
    command_desc_queue = f"➤ Use: `queue`\n➤ Aliases: `q`\n" \
                           f"➤ Description: Shows the song queue."
    command_desc_loop = f"➤ Use: `loop [all/queue/shuffle/random/off]`\n➤ Aliases: `lp`\n" \
                          f"➤ Description: Changes the loop mode; `all/queue` repeats the whole queue, " \
                          f"`shuffle/random` randomize the next song when the current one is finished, " \
                          f"`one` repeats the current song, `off` disables the loop."
    command_desc_shuffle = f"➤ Use: `shuffle`\n➤ Aliases: `sf`, `random`\n" \
                             f"➤ Description: Randomizes the queue, then goes to the first song."
    command_desc_info = f"➤ Use: `np`\n➤ Aliases: `info`, `nowplaying`, `playing`\n" \
                          f"➤ Description: Shows information of the current song."
    command_desc_lyrics = f"➤ Use: `lyrics [nothing/song name]`\n➤ Aliases: `lyric`\n" \
                            f"➤ Description: Shows the lyrics of the current playing song, if given a name of a song " \
                            f"it shows the lyrics to that song."
    command_desc_songs = f"➤ Use: `songs [nothing/NUM] [artist]`\n➤ Aliases: `song`\n" \
                           f"➤ Description: Shows the top NUM songs of the given artist (10 if no NUM provided)." \
                           f" If no artist is provided, it retrieves it from the current playing song."
    command_desc_steam = f"➤ Use: `steam [user]`\n➤ Description: Shows the steam profile of the given user."
    command_desc_remove = f"➤ Use: `remove [song number]`\n➤ Aliases: `rm`" \
                            f"➤ Description: Removes the given song from the queue (use `queue` to see the songs and their numbers)."
    command_desc_goto = f"➤ Use: `goto [song number]`\n➤ Description: Goes to the chosen song."
    command_desc_ping = f"➤ Use: `ping`\n➤ Description: Shows the bot latency."
    command_desc_avatar = f"➤ Use: `avatar`\n➤ Aliases: `pfp`, `profile`\n" \
                            f"➤ Description: Shows your profile picture (HD)."
    command_desc_level = f"➤ Use: `level`\n➤ Aliases: `lvl`\n" \
                           f"➤ Description: Shows your level."
    command_desc_chatgpt = f"➤ Use: `chatgpt [message]`\n➤ Aliases: `chat`, `gpt`\n" \
                             f"➤ Description: Answers with ChatGPT your message."
    command_desc_seek = f"➤ Use: `seek [time]`\n➤ Aliases: `sk`\n" \
                          f"➤ Description: Goes to the given time. Time should be given in seconds or in format HH:MM:SS."
    command_desc_chords = f"➤ Use: `chords [nothing/song]`\n" \
                            f"➤ Description: Shows the chords of the current song, if given a song it shows the chords to that song."
    command_desc_genre = f"➤ Use: `genre [nothing/genre]`\n➤ Aliases: `genres`, `recomm`, `recommendation`, `recommendations`\n" \
                           f"➤ Description: Shows songs of the given genre, if nothing (or available) is put, shows the list of genres."
    command_desc_search = f"➤ Use: `search [nothing/youtube/spotify] [query]`\n➤ Aliases: `find`\n" \
                            f"➤ Description: Searches in youtube (default) or spotify the given query and shows the results."
    command_desc_rewind = f"➤ Use: `rewind`\n➤ Aliases: `rw`, `r`, `back`\n" \
                            f"➤ Description: Goes back to the previous song."
    command_desc_forward = f"➤ Use: `forward [time]`\n➤ Aliases: `fw`, `forwards`, `bw`, `backward`, `backwards`\n" \
                             f"➤ Description: Fast forwards or rewinds the song (depending if the time is positive/negative). " \
                             f"Time should be given in seconds or in format HH:MM:SS."
    command_desc_options = f"➤ Use: `config [nothing/option] [value]`\n➤ Aliases: `options`, `opt`, `cfg`\n" \
                             f"➤ Description: Changes the value of the given option to the given value, if no option is given, " \
                             f"shows the list of options."
    command_desc_fastplay = f"➤ Use: `fastplay [song name or url]`\n➤ Aliases: `fp`\n" \
                              f"➤ Description: Plays a song without having to choose."
    command_desc_perms = f"➤ Use: `perms`\n➤ Aliases: `prm`\n" \
                           f"➤ Description: Shows %bot_name (the bot) current permissions in the server."
    command_desc_add_prefix = f"➤ Use: `add_prefix [prefix]`\n➤ Aliases: `prefix`, `set_prefix`\n" \
                                f"➤ Description: Adds the given prefix to use it for commands."
    command_desc_del_prefix = f"➤ Use: `del_prefix [prefix]`\n➤ Aliases: `remove_prefix`, `rem_prefix`\n" \
                                f"➤ Description: Removes the given prefix."
    command_desc_add_perm = f"➤ Use: `add_perm [name/ALL] [permission]`\n" \
                              f"➤ Description: Adds the given permission to the specified user (or all users)."
    command_desc_del_perm = f"➤ Use: `del_perm [name/ALL] [permission]`\n" \
                              f"➤ Description: Removes the given permission from the specified user (or all users)."
    command_desc_available_perms = f"➤ Use: `available_perms`\n" \
                                     f"➤ Description: Shows the available permissions and the ones that are given by default to" \
                                     f" all users (admins get all permissions)."
    command_desc_pitch = f"➤ Use: `pitch [semitones]`\n➤ Aliases: `tone`\n" \
                           f"➤ Description: Changes the pitch of the current song in the given semitones. " \
                           f"(positive: higher pitch, negative: lower pitch)."
    command_desc_lang =  f"➤ Use: `lang [language]`\n➤ Aliases: `language`, `change_lang`, `change_language`\n" \
                           f"➤ Description: Changes the language of the bot (english: en, spanish: es)."
    command_commands = "➤ `help [nothing/command] (h)`\n➤ `play [query or url] [nothing/-opt option] (p)`\n" \
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

en_data = dict()
a = vars().copy()
for name, value in zip(a.keys(), a.values()):
    if isinstance(value, list) or isinstance(value, str) and not name.startswith("__"):
        en_data[name] = find_font(value, FONT) if isinstance(value, str) else [find_font(v, FONT) for v in value]

try:
    with open("lang/en.json", "w") as f:
        json.dump(en_data, f)
except:
    with open("en.json", "w") as f:
        json.dump(en_data, f)


### SPANISH ###
if True: # only to minimize
    already_connected_texts = ["Ya estoy conectado.", "Ya entré."]
    entering_texts = ["Uniéndome a ", "Entrando a "]
    nothing_on_texts = ["No está sonando nada."]
    song_not_chosen_texts = [f"La selección ha expirado."]
    not_existing_command_texts = ["Comando inválido."]
    nobody_left_texts = ["No queda nadie, desconectando..."]
    invalid_use_texts = ["Uso inválido (usar `help` para más información)."]
    prefix_use_texts = ["Para añadir o borrar un prefijo, usar `add_prefix [prefijo]` o `del_prefix [prefijo]`."]
    couldnt_complete_search_texts = ["No se pudo completar la búsqueda."]
    not_in_vc_texts = ["No estás en un canal de voz."]
    private_channel_texts = ["No puedo entrar a ese canal."]
    cancel_selection_texts = ["Selección cancelada."]
    invalid_link_texts = ["Link no válido."]
    restricted_video_texts = ["Video no válido (restringido por edad o privado)."]
    rip_audio_texts = ["Error de audio."]
    no_queue_texts = ["No hay canciones en la cola."]
    avatar_error_texts = ["No se pudo obtener la foto de perfil."]
    no_api_credits_texts = ["No se tienen créditos de API para usar esto."]
    lyrics_too_long_texts = ["La letra es muy larga."]
    no_api_key_texts = ["Esta funcionalidad está desactivada."]
    insuff_perms_texts = ["No tienes permisos para usar esto."]
    not_connected_texts = ["No estoy conectado a un canal de voz."]
    different_channel_texts = ["No estamos en el mismo canal."]
    api_key_not_found = "no encontrado. Ir a 'API_KEYS.txt' para configurarlo."
    api_request_error = "Error en la solicitud de API"
    invalid_time_format = "Formato del tiempo inválido. Usar HH:MM:SS o MM:SS."
    generic_error = "Error"
    processing_error = "Error procesando"
    couldnt_find_audiofile = "Error: No se pudo encontrar el archivo de audio."
    logged_in = "Conectado como"
    command_from = "Comando de"
    wait_seconds = "%name, espere `%time` segundos."
    help_title = "ℹ️ — Ayuda"
    help_desc = "Lista de comandos -> comando [uso] (aliases) | Prefijos: %prefix:"
    bot_perms = "⚙️ — Permisos de %botname en %server"
    couldnt_find_user = "No se pudo encontrar al usuario `%name`."
    invalid_perm = "El permiso `%perm` no es válido, usar `available_perms`."
    perm_added_everyone = "Permiso `%perm` añadido a *todos*."
    perm_added = "Permiso `%perm` añadido a `%name`."
    perm_already_added = "`%name` ya tiene el permiso `%perm`."
    all_perms_added = "Todos los permisos añadidos a `%name`."
    all_perms_everyone = "Todos los permisos añadidos a todos."
    perm_del_everyone = "Permiso `%perm` removido de todos."
    perm_not_added = "`%name` no tiene el permiso `%perm`."
    perm_removed = "Permiso `%perm` removido de `%name`."
    available_perms_title = "⚙️ — **Permisos disponibles**"
    default_perms_title = "⚙️ — **Permisos por defecto**"
    song_info_title = "ℹ️ — **Información de la canción**"
    song_info_desc = "➤ **Título**: %title\n➤ **Artista**: %artist\n➤ **Canal**: %channel\n➤ **Duración**: `%duration`\n\n %bar"
    config_title = "⚙️ — Configuración"
    config_desc = "➤ Opciones: `search_limit=%search_limit`, `recomm_limit=%recomm_limit`, `custom_prefixes=%custom_prefixes`, `restricted_to=%restricted_to`."
    config_changed = "➤ `%option` cambiado de `%original` a `%newvalue`"
    config_default = "➤ `search_limit` cambiado de `%sl` a `%def_sl`\n" \
                        "➤ `recomm_limit` cambiado de `%rl` a `%def_rl`\n" \
                        "➤ `custom_prefixes` cambiado de `%cust_p` a `%def_cust_p`\n"
    youtube_search_title = "🔎 — Resultados de búsqueda de YouTube"
    spotify_search_title = "🔎 — Resultados de búsqueda de Spotify"
    spotify_search_desc = "➤ **Título**: [%name](%url) | **Artista**: %artist\n"
    available_genres = "🎸 — Géneros disponibles"
    genre_search_title = "🔎 — Resultados de búsqueda de Spotify por género: %genre"
    choose_song_title = "🔍 — Elige una canción (Página %page)"
    playlist_added_title = "📜 — Lista de reproducción añadida"
    playlist_added_desc = "¡**%name** puso **%title** en *%ch_name*!\nUn total de `%pl_length` canciones fueron añadidas."
    playlist_max_reached = "La lista de reproducción tiene `%pl_length` videos, `%over` más que el máximo. Los últimos `%discarded` videos fueron descartados."
    playlist_link = "Link de la lista de reproducción"
    playlist_link_desc = '%url\n\n➤ **Título**: *%title*'
    playlist_link_desc_time = "\n➤ **Duración total**: `%duration`"
    playlist_videos_unavailable = "La lista de reproducción tiene `%total` videos, de los cuales `%unavailable` no están disponibles."
    video_max_duration = "El video es muy largo (límite de `%video_limit`)."
    song_selected = "Elegido: %title"
    song_chosen_title = "Canción elegida"
    raw_audio_desc = "¡**%name** puso un audio en *%ch_name*!"
    all_selected = "Todas las canciones de la página %page elegidas."
    song_chosen_desc = "¡**%name** puso **[%title](%url)** en *%ch_name*!"
    added_queue_title = "Añadido a la cola"
    added_queue_desc = "**%name** añadió **[%title](%url)** a la cola."
    word_title = "Título"
    word_duration = "Duración"
    word_views = "Visitas"
    level_title = "📶 — Menú de niveles"
    level_desc = "➤ **Nombre**: %name\n➤ **NVL**: `%level`\n➤ **EXP**: `%xp/%next_xp`"
    removed_from_queue = "Removido de la cola: *%title*"
    fast_forwarding = "%emoji — Adelantando"
    rewinding = "%emoji — Rebobinando"
    forward_title = "**%modetype %sec a %time**"
    seek_title = "⏱️ — Posición Actualizada"
    not_loop_mode = f"`%mode` no es un modo de loop, usar `queue/all`, `shuffle/random`, `one` o `off`."
    loop_disable = "Loop desactivado."
    loop_mode_changed = "Modo de loop: `%loop`."
    queue_title = "🎶 — Cola de canciones"
    queue_pages = "Página"
    queue_videos = "Canciones"
    queue_duration = "Duración"
    queue_current = "` ⮜ **Canción actual**"
    profile_title = "👤 — Foto de perfil de %name"
    steam_title = "👤 — Perfil de Steam de %name"
    chatgpt_title = "🤖 — Respuesta de ChatGPT"
    lyrics_title = "ℹ️ — Información"
    lyrics_desc = f"➤ **Título**: %title\n➤ **Artista**: %artist"
    top_songs_title = "🔝 — Top %number canciones de %artist"
    chords_title = "🎼 — Acordes de %song, %artist"
    tuning_embed_title = "ℹ️ — Información de afinación"
    tuning_embed_desc = "➤ **Tonalidad**: %tonality\n➤ **Capo**: %capo\n➤ **Afinación**: %tuning_value (%tuning_name)\n➤ **Traspuesta**: %traspose"
    no_capo_chords = "Sin capotraste"
    pitch_title = "🎤 - Tono cambiado"
    pitch_desc = "➤ **Tono**: %sign%tone\n➤ **Velocidad**: x%speed"
    volume_title = "🎚️ — Volúmen cambiado"
    volume_desc = "➤ **Volúmen**: %vol"
    eq_title = "🎛️ — Ecualización"
    eq_desc = "➤ **Frecuencia**: %freq\n➤ **Ancho**: %width\n➤ **Volúmen**: %vol"
    prefix_add_title = "⚙️ — Prefijo añadido"
    prefix_add_desc = "➤ El prefijo `%prefix` fue añadido. Prefijos: `%prfixes`"
    prefix_del_title = "⚙️ — Prefijo removido"
    prefix_del_desc = "➤ El prefijo `%prefix` fue removido. Prefijos: `%prfixes`"
    lang_changed = "¡Hola!"
    vote_skip_text = "Votación para saltar la canción: %num necesarios."
    song_skipped = "Canción saltada."
    queue_reversed = "Orden de las canciones invertido."
    searching_text = "Buscando..."
    recognizing_song = "Escuchando..."
    shazam_title = "✅ — Canción encontrada"
    shazam_desc = f"➤ **Título**: %title\n➤ **Artista**: %artist\n➤ **Álbum**: %album\n➤ **Género%plural**: %genres\n\n%url"
    shazam_no_song = f"No se pudo reconocer la canción. Prueba a usar un tiempo más largo; `shazam [duración]`."
    no_album_info_found = "Sin información."
    autodj_added_songs = "Se añadieron `%num` canciones relacionadas a la cola."
    autodj_no_song = "No se pudo obtener información."
    cannot_change_time_live = "No se puede usar `%command` en un video en vivo."
    couldnt_load_song = "No se pudo cargar la canción (privado/restricción por edad): %title."
    already_on_another_vc = "Ya estoy en otro canal."
    channel_doesnt_exist = "`%name` no existe."
    restricted_to_channel = "Ahora solo mandaré mensajes en `%name`."
    cant_access_channel = "`%name` es privado y no tengo acceso."
    not_restricted = "Ahora puedo mandar mensajes a todos los canales."
    download_url = "Click [aquí](%url) para descargar.\nLink original [aquí](%original_url)."
    cannot_download_live = "No se puede descargar videos EN VIVO."
    cannot_download_m3u8 = "No se pudo descargar esta canción."
    no_playlists_created = "No hay listas en `%server_name`. Usar `playlist create [nombre]`."
    playlist_list_title = "🎹 — Listas"
    playlist_list_desc = "%playlists"
    playlist_created = "Lista `%pl_name` creada. Añade canciones usando `playlist add %pl_name [canción]`."
    playlist_already_exists = "La lista `%pl_name` ya existe."
    playlist_not_found = "Lista `%pl_name` no encontrada. Usar `playlist names` para ver las listas disponibles en este server."
    playlist_no_songs = "La lista `%pl_name` no tiene canciones. Usar `playlist add %pl_name [canción]`."
    added_to_playlist_url = "[%title](%url) añadido a `%pl_name`."
    playlist_played = "Lista `%pl_name` añadida a la cola."
    playlist_cleared = "Lista `%pl_name` limpiada."
    playlist_deleted = "Lista `%pl_name` borrada."
    removed_from_playlist = "[Canción %number](%url) borrada de `%pl_name`."
    queue_added_to_playlist = "Cola actual añadida a `%pl_name`, `%num_songs` canciones añadidas."
    shared_playlist_code = "Código de la lista: `%code`. Usar `playlist load [código]` para cargarla."
    playlist_loaded = "Lista `%pl_name` cargada con `%len` videos."
    playlist_created_by = "Creada por %name"
    playlist_title = "📜 — Lista: "
    playlist_info = "canciones, por *%name*"
    change_channels_mode = "Cambiado el audio a `%mode`."
    missing_parameters = "ATENCIÓN: Parámetro faltante, se reescribirá el archivo y los parámetros serán cambiados a sus valores por defecto.\nPresiona 'Enter' para proceder."
    invalid_parameter = "Parámetro inválido, usar `parameters` para ver la lista de parámetros disponibles."
    parameters_to_default = "Parámetros revertidos a su valor por defecto."
    parameter_changed_value = "Parámetro `%pname` cambiado a `%value`."
    song_queue_ended = "La cola de canciones terminó."
    command_desc_help = f"➤ Uso: `help [nada/comando]`\n➤ Aliases: `h`\n" \
                          f"➤ Descripción: Muestra todos los comandos, si se especifica un comando muestra más información acerca de este."
    command_desc_play = f"➤ Uso: `play [canción o link] [nada/-opt opción]`\n➤ Aliases: `p`\n" \
                          f"➤ Descripción: Toca la canción dada. Si se agrega -opt gif al final, se añade un gif (¡prúebalo!)."
    command_desc_leave = f"➤ Uso: `leave`\n➤ Aliases: `l`, `dis`, `disconnect`, `d`\n" \
                           f"➤ Descripción: Desconecta al bot del canal de voz."
    command_desc_skip = f"➤ Uso: `skip`\n➤ Aliases: `s`, `next`\n" \
                          f"➤ Descripción: Salta a la siguiente canción."
    command_desc_join = f"➤ Uso: `join`\n➤ Aliases: `connect`\n" \
                          f"➤ Descripción: Conecta al bot al canal de voz."
    command_desc_pause = f"➤ Uso: `pause`\n➤ Aliases: `stop`\n" \
                           f"➤ Descripción: Pausa la canción."
    command_desc_resume = f"➤ Uso: `resume`\n" \
                            f"➤ Descripción: Reaunuda la canción."
    command_desc_queue = f"➤ Uso: `queue`\n➤ Aliases: `q`\n" \
                           f"➤ Descripción: Muestra la cola de canciones."
    command_desc_loop = f"➤ Uso: `loop [all/queue/shuffle/random/off]`\n➤ Aliases: `lp`\n" \
                          f"➤ Descripción: Cambia el modo de loop; `all/queue` repite toda la cola, " \
                          f"`shuffle/random` elige una canción aleatoria cuando la actual termine, " \
                          f"`one` repite la canción actual, `off` desactiva el loop."
    command_desc_shuffle = f"➤ Uso: `shuffle`\n➤ Aliases: `sf`, `random`\n" \
                             f"➤ Descripción: Aleatoriza la cola, luego va a la primera canción."
    command_desc_info = f"➤ Uso: `np`\n➤ Aliases: `info`, `nowplaying`, `playing`\n" \
                          f"➤ Descripción: Muestra información de la canción actual."
    command_desc_lyrics = f"➤ Uso: `lyrics [nada/canción]`\n➤ Aliases: `lyric`\n" \
                            f"➤ Descripción: Muestra la letra de la canción actual si no se especifica nada, si no muestra la letra " \
                            f"de la canción dada."
    command_desc_songs = f"➤ Uso: `songs [nada/NUM] [artista]`\n➤ Aliases: `song`\n" \
                           f"➤ Descripción: Muestra el top NUM de canciones del artista dado (10 si no especifica NUM)." \
                           f" Si no se especifica el artista, lo toma de la canción actual."
    command_desc_steam = f"➤ Uso: `steam [usuario]`\n➤ Descripción: Muestra el perfil de steam del usuario dado."
    command_desc_remove = f"➤ Uso: `remove [número de canción]`\n➤ Aliases: `rm`" \
                            f"➤ Descripción: Borra la canción dada de la cola (usar `queue` para ver las canciones y sus números)."
    command_desc_goto = f"➤ Uso: `goto [número de canción]`\n➤ Descripción: Va a la canción elegida."
    command_desc_ping = f"➤ Uso: `ping`\n➤ Descripción: Muestra la latencia del bot."
    command_desc_avatar = f"➤ Uso: `avatar`\n➤ Aliases: `pfp`, `profile`\n" \
                            f"➤ Descripción: Muestra tu foto de perfil (HD)."
    command_desc_level = f"➤ Uso: `level`\n➤ Aliases: `lvl`\n" \
                           f"➤ Descripción: Muestra tu nivel."
    command_desc_chatgpt = f"➤ Uso: `chatgpt [mensaje]`\n➤ Aliases: `chat`, `gpt`\n" \
                             f"➤ Descripción: Responde a tu mensaje con ChatGPT."
    command_desc_seek = f"➤ Uso: `seek [tiempo]`\n➤ Aliases: `sk`\n" \
                          f"➤ Descripción: Va al tiempo elegido. El tiempo deberia darse en segundos o en formato HH:MM:SS."
    command_desc_chords = f"➤ Uso: `chords [nada/canción]`\n" \
                            f"➤ Descripción: Muestra los acordes de la canción actual si no se especifica una canción," \
                            f" si no muestra los acordes de dicha canción."
    command_desc_genre = f"➤ Uso: `genre [nada/género]`\n➤ Aliases: `genres`, `recomm`, `recommendation`, `recommendations`\n" \
                           f"➤ Descripción: Muestra canciones del género dado, muestra una lista de los géneros disponibles " \
                           f"si no se especifica nada (o se pone available)."
    command_desc_search = f"➤ Uso: `search [nada/youtube/spotify] [búsqueda]`\n➤ Aliases: `find`\n" \
                            f"➤ Descripción: Busca en youtube (por defecto) o spotify y muestra los resultados."
    command_desc_rewind = f"➤ Uso: `rewind`\n➤ Aliases: `rw`, `r`, `back`\n" \
                            f"➤ Descripción: Vuelve a la canción anterior."
    command_desc_forward = f"➤ Uso: `forward [tiempo]`\n➤ Aliases: `fw`, `forwards`, `bw`, `backward`, `backwards`\n" \
                             f"➤ Descripción: Adelanta o rebobina la canción (dependiendo de si el tiempo es positivo/negativo). " \
                             f"El tiempo deberia darse en segundos o en formato HH:MM:SS."
    command_desc_options = f"➤ Uso: `config [nada/opción] [valor]`\n➤ Aliases: `options`, `opt`, `cfg`\n" \
                             f"➤ Descripción: Cambia el valor de la opción dada al valor especificado. Si no se da una opción," \
                             f" muestra una lista de las opciones disponibles."
    command_desc_fastplay = f"➤ Uso: `fastplay [canción o link]`\n➤ Aliases: `fp`\n" \
                              f"➤ Descripción: Toca una canción sin tener que elegir."
    command_desc_perms = f"➤ Uso: `perms`\n➤ Aliases: `prm`\n" \
                           f"➤ Descripción: Muestra los permisos de %bot_name (el bot) en el server."
    command_desc_add_prefix = f"➤ Uso: `add_prefix [prefijo]`\n➤ Aliases: `prefix`, `set_prefix`\n" \
                                f"➤ Descripción: Añade el prefijo dado."
    command_desc_del_prefix = f"➤ Uso: `del_prefix [prefijo]`\n➤ Aliases: `remove_prefix`, `rem_prefix`\n" \
                                f"➤ Descripción: Borra el prefijo dado."
    command_desc_add_perm = f"➤ Uso: `add_perm [nombre/ALL] [permiso]`\n" \
                              f"➤ Descripción: Añade el permiso especificado al usuario dado (o a todos)."
    command_desc_del_perm = f"➤ Uso: `del_perm [nombre/ALL] [permiso]`\n" \
                              f"➤ Descripción: Borra el permiso especificado del usuario dado (o de todos)."
    command_desc_available_perms = f"➤ Uso: `available_perms`\n" \
                                     f"➤ Descripción: Muestra los permisos disponibles y los que son dados por defecto " \
                                     f"a todos los usuarios (los administradores obtienen todos los permisos)."
    command_desc_pitch = f"➤ Uso: `pitch [semitonos]`\n➤ Aliases: `tone`\n" \
                           f"➤ Descripción: Cambia el tono de la canción los semitonos dados " \
                           f"(positivo: más agudo, negativo: más grave)."
    command_desc_lang = f"➤ Uso: `lang [lenguaje]`\n➤ Aliases: `language`, `change_lang`, `change_language`\n" \
                          f"➤ Descripción: Cambia el lenguaje del bot (inglés: en, español: es)."
    command_commands = "➤ `help [nada/comando] (h)`\n➤ `play [canción o link] [nada/-opt] (p)`\n" \
                         "➤ `leave (l, dis, disconnect, d)`\n➤ `skip (s, next)`\n➤ `join (connect)`\n➤ `pause (stop)`\n" \
                         "➤ `resume`\n➤ `queue (q)`\n➤ `loop [all/queue/shuffle/random/one/off] (lp)`\n➤ `shuffle (sf, random)`\n" \
                         "➤ `np (info, nowplaying, playing)`\n➤ `lyrics [nada/canción] (lyric)`\n" \
                         "➤ `songs [nada/NUM] [artista] (song)`\n➤ `steam [usuario]`\n➤ `remove [número de canción] (rm)`" \
                         "\n➤ `goto [número de canción]`\n➤ `search [nada/youtube/spotify] [búsqueda] (find)`\n➤ `ping`\n➤ `avatar (pfp, profile)`\n" \
                         "➤ `level (lvl)`\n➤ `chatgpt [mensaje] (chat, gpt)`\n➤ `seek [tiempo] (sk)`\n➤ `chords [nada/canción]`\n" \
                         "➤ `genre [nada/género] (genres, recomm, recommendation, recommendations)`\n" \
                         "➤ `forward [tiempo] (fw, forwards, bw, backward, backwards)`\n➤ `config [nada/opción] [valor] " \
                         "(cfg, options, opt)`\n➤ `fastplay [canción o link] (fp)`\n➤ `perms (prm)`\n" \
                         "➤ `add_prefix [prefijo] (prefix, set_prefix)`\n➤ `del_prefix [prefijo] (rem_prefix, remove_prefix)`\n" \
                         "➤ `add_perm [nombre/ALL] [permiso]`\n➤ `del_perm [nombre/ALL] [permiso]`\n➤ `available_perms`\n" \
                         "➤ `pitch [semitonos] (tone)`"

es_data = dict()
a = vars().copy()
for name, value in zip(a.keys(), a.values()):
    if isinstance(value, list) or isinstance(value, str) and not name.startswith("__"):
        es_data[name] = find_font(value, FONT) if isinstance(value, str) else [find_font(v, FONT) for v in value]

try:
    with open("lang/es.json", "w") as f:
        json.dump(es_data, f)
except:
    with open("es.json", "w") as f:
        json.dump(es_data, f)