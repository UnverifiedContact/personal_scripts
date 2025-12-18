if [ -f "$HOME/IS_MOBILE" ]; then
	RCLONE_CONFIG=$HOME/rclone.conf
	export RCLONE_CONFIG
	export TMP=$HOME/tmp
	[[ -z "${CARD_VIDS_PATH}" ]] && echo 'WARNING: CARD_VIDS_PATH is not set.';
	alias ol="time rsync -av --progress --size-only . $CARD_VIDS_PATH"
  alias nol="time rsync -av --progress --size-only . $CARD_NIGHT_PATH"
	alias clean_landing='time rm --verbose *.mp4 && rm --verbose *.mkv && rm --verbose *.webm'
  alias clean_landing='extensions="mp4 mkv webm vtt part ytdl jpg webp srt mp3 avi"; time for ext in $extensions; do rm --verbose *."$ext"; done'
	. `which env_parallel.bash`
	#sshd && sv-enable sshd
  #apachectl restart && sv-enable httpd
  source $PREFIX/etc/profile.d/start-services.sh
  sv-enable sshd
  sv-enable httpd

else
	alias python=python3
	xset b off # no beep
	export TMP='/tmp'
	export PATH="$HOME/.local/bin:$PATH" # for pipx binaries
	alias whack_gnome='pkill -f "gnome-terminal"'
	alias wn='whack_gnome'
fi

[[ -z "${NEWSBOAT_DB_BUP_DIR}" ]] && echo 'WARNING: NEWSBOAT_DB_BUP_DIR is not set.';

start_nbserver() {
    local logdir="$HOME/personal_scripts/nbserver/logs"
    local logfile="$logdir/api_server.log"
    mkdir -p "$logdir"
    
    set +m
    python3 "$HOME/personal_scripts/nbserver/api_server.py" \
        --db="$NEWSBOAT_DB_FILE" \
        >>"$logfile" 2>&1 &
    set -m
    disown $! 2>/dev/null
}

review_news() {
    local port=5001
    start_nbserver
    if [ -f "$HOME/IS_MOBILE" ] && command -v am >/dev/null 2>&1; then
        ( sleep 2 && am start -a android.intent.action.VIEW -d "http://localhost:$port" org.mozilla.firefox ) &
    fi
}
alias nr='review_news'

## news related functions
export NEWSBOAT_DB_FILE="$HOME/newsboat/newsboat_cache.db"
export NEWSBOAT_CONFIG_FILEPATH="$HOME/newsboat/newsboat_config"
export NEWSBOAT_URLS_FILE="$HOME/newsboat/newsboat_urls_file"
alias sub="python3 $HOME/personal_scripts/subscribe.py"
alias iys="python3 $HOME/personal_scripts/inject_yt_subs.py"
alias dld="time python3 $HOME/personal_scripts/dldir.py"
alias get='php $HOME/personal_scripts/custom_get.php'

alias py='python3'
alias cls='clear'
alias ta='tmux attach || tmux new'
alias source_bash='source ~/.bashrc'
alias dt='top -b -n 1 > ~/top.txt' # dump top
alias ports='lsof -i -P -n'
alias rs='pkill sshd; sshd;'
alias wgr='wget -cr -np -R "index.html*" '
alias sb='source_bash'
alias x='exit'
alias vol="pactl list sinks | grep -P -m1 'Volume:.*?([0-9]+)%' | awk -F' ' '{print \$5}'"
alias vup='pactl -- set-sink-volume 0 +10% && vol'
alias v200='pactl -- set-sink-volume 0 200% && vol'

alias enc='gpg --batch --symmetric --passphrase "dog" '
alias dec='gpg --decrypt --batch --passphrase "dog" '
alias gip="source_bash ; export GATEWAY_IP=$(ip route | grep def | cut -d ' ' -f 3) && echo $GATEWAY_IP"
alias temp="sensors | grep \"Core 0\" | awk '{print $3}'"

export VISUAL=vim
export EDITOR="$VISUAL"
export APPIMAGES_DIR='$HOME/appimages'
alias youtube-dl='$HOME/yt-dlp/yt-dlp.sh'
alias yt-dlp='youtube-dl'
alias ytdlp='youtube-dl'
alias yt='youtube-dl'
alias pc='protonvpn-cli c'
alias pd='protonvpn-cli d'

cbup() {
	#echo $@
	TIMESTAMP=$(date +%s);
	FILEPATH="$@";
	FILENAME=$(basename $FILEPATH);
	echo $FILENAME;
	echo $FILEPATH;
	#rclone copy $FILEPATH box1:test --backup-dir="box1:old/$FILENAME/$TIMESTAMP" -P;
	rclone copy $FILEPATH box2:cbup --backup-dir="box2:old/$FILENAME/$TIMESTAMP" -P;
	rclone copy $FILEPATH mega2:cbup --backup-dir="mega2:old/$FILENAME/$TIMESTAMP" -P;
	#rclone copy $FILEPATH mega1:test --backup-dir="mega1:old/$FILENAME/$TIMESTAMP" -P;
}

cpull() {
	rclone copy "box2:cbup/$1" .
}

emsub() { 
    #ffmpeg -i "$1" -c copy -sn "$TMP/$1" && mv "$TMP/$1" "$1";
    #ffmpeg -i "$1" -i "$2" -c copy -c:s mov_text -metadata:s:s:0 language=eng "$TMP/$1" && mv "$TMP/$1" "$1"; 
    ffmpeg -i "$1" -i "$2" -c copy -c:s mov_text -metadata:s:s:0 language=eng "$TMP/$1" && rsync --progress "$TMP/$1" "$1" && rm "$TMP/$1";
};

# for mp4
emsub_bup() { 
    ffmpeg -i "$1" -c copy -sn "$TMP/$1" && mv "$TMP/$1" "$1";
    ffmpeg -i "$1" -i "$2" -c copy -c:s mov_text -metadata:s:s:0 language=eng "$TMP/$1" && mv "$TMP/$1" "$1"; 
};

rmsub_all() {
  ffmpeg -i "$1" -map 0:v -map 0:a? -c copy "$TMP/$1" && rsync --progress "$TMP/$1" "$1" && rm "$TMP/$1"
}

# for mkv
emsub2() { 
    ffmpeg -i "$1" -c copy -sn "$TMP/$1" && mv "$TMP/$1" "$1";
    ffmpeg -i "$1" -i "$2" -c:a aac -c copy -c:s srt -metadata:s:s:0 language=eng "$TMP/$1" && mv "$TMP/$1" "$1"; 
};

scream() {
	termux-volume notification 15;
	while true; do
		termux-notification --button1 "AAA";
		termux-media-player play $HOME/beep.mp3; 
	done
};

ytz_bup() {
    local selections=""
    selections+="hls-221/hls-222/hls-223/hls-224/hls-225/hls-226/hls-227/hls-228/hls-229/hls-22?/hls-21?/" # rumble mp4 640x360
    # selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)/"
    # selections+="worst[height>=480][ext=mp4]/"
    # selections+="worst[height>=480]/"
    # selections+="best"
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="worstvideo[height>=480][vcodec!*=av01]+((worstaudio[abr>=64][language^=en]/bestaudio[language^=en])/(worstaudio[abr>=64]/bestaudio))/"
    selections+="worst[height>=480][ext=mp4]/" # this line is necessary else we get fragmented formats which are gay
    selections+="worst[height>=480]/"
    selections+="best"

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default

    [[ " $* " == *" --720 "* ]] && selections="bestvideo[height<=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --1080 "* ]] && selections="bestvideo[height<=1080][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --force "* ]] && { archive_flag=""; force_overwrite="--force-overwrites"; }
    [[ " $* " == *" --max "* ]] && { selections="bestvideo+bestaudio/best"; }

    echo "${!#}"
    $HOME/yt-dlp/yt-dlp.sh \
        -f "$selections" \
        --progress-template "[Downloading] %(info.uploader,info.channel,info.uploader_id)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-chapters \
        --sub-langs=en,en-orig,en-US,en-x-autogen,en-auto,English \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --progress \
        --newline \
        --merge-output-format mkv \
        --sponsorblock-chapter all \
	      --use-postprocessor 'DeArrow:when=pre_process' \
        -o '%(uploader,channel,uploader_id|40.40s)s - %(title)s [%(id)s].%(ext)s' \
        $archive_flag \
        $force_overwrite \
        --exec 'touch {} && echo {} && sync' "${!#}" || echo "${!#}" >> ytdl_failure.txt
}

ytz_megabup() {
    local selections=""

    selections+="best[protocol=m3u8][height<=480][height>=480]/"  # try 480p first
    selections+="best[protocol=m3u8][height<=360][height>=360]/"  # fallback to 360p
    selections+="best[protocol=m3u8][height<=720][height>=720]/"  # fallback to 720p
    selections+="best[protocol=m3u8]/"                             # fallback to any HLS
    
    #selections+="hls-221/hls-222/hls-223/hls-224/hls-225/hls-226/hls-227/hls-228/hls-229/hls-22?/hls-21?/" # rumble mp4 640x360
    # selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)/"
    # selections+="worst[height>=480][ext=mp4]/"
    # selections+="worst[height>=480]/"
    # selections+="best"
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="worstvideo[height>=480][vcodec!*=av01]+((worstaudio[abr>=64][language^=en]/bestaudio[language^=en])/(worstaudio[abr>=64]/bestaudio))/"
    selections+="worst[height>=480][ext=mp4]/" # this line is necessary else we get fragmented formats which are gay
    selections+="worst[height>=480]/"
    selections+="best"

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default
    local skip_subs=""

    [[ " $* " == *" --720 "* ]] && selections="bestvideo[height<=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --1080 "* ]] && selections="bestvideo[height<=1080][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --force "* ]] && { archive_flag=""; force_overwrite="--force-overwrites"; }
    [[ " $* " == *" --max "* ]] && { selections="bestvideo+bestaudio/best"; }
    [[ " $* " == *" --skip-subs "* ]] && skip_subs="true"

    echo "${!#}"
    
    # Build command arguments
    local cmd_args=(
        -f "$selections"
        --progress-template "[Downloading] %(info.uploader,info.channel,info.uploader_id)s - %(info.title)s | $progress_format"
        --add-metadata
        --embed-chapters
        #--sub-langs=en,en-orig,en-US,en-x-autogen,English
        --match-filter '!is_live'
        --match-filter 'duration<36000'
        #--embed-subs
        --progress
        --newline
        --merge-output-format mkv
        --sponsorblock-chapter all
        --use-postprocessor 'DeArrow:when=pre_process'
        #--extractor-args "youtube:player_client=default,web_safari;player_js_version=actual" # temp workaround
        -o '%(uploader,channel,uploader_id|40.40s)s - %(title)s [%(id)s].%(ext)s'
        $archive_flag
        $force_overwrite
        --exec 'touch {} && echo {} && sync'
    )
    
    # Add subtitle injection exec if not skipping
    if [ "$skip_subs" != "true" ]; then
        cmd_args+=(--exec "python3 $HOME/personal_scripts/inject_yt_subs.py {}")
    fi
    
    # Add the URL
    cmd_args+=("${!#}")
    
    # Execute the command
    "$HOME/yt-dlp/yt-dlp.sh" "${cmd_args[@]}" || echo "${!#}" >> ytdl_failure.txt
}

ytz() {
    local url="${!#}"
    local selections=""

    selections+="best[protocol=m3u8][height<=480][height>=480]/"  # try 480p first
    selections+="best[protocol=m3u8][height<=360][height>=360]/"  # fallback to 360p
    selections+="best[protocol=m3u8][height<=720][height>=720]/"  # fallback to 720p
    selections+="best[protocol=m3u8]/"                             # fallback to any HLS
    
    #selections+="hls-221/hls-222/hls-223/hls-224/hls-225/hls-226/hls-227/hls-228/hls-229/hls-22?/hls-21?/" # rumble mp4 640x360
    # selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)/"
    # selections+="worst[height>=480][ext=mp4]/"
    # selections+="worst[height>=480]/"
    # selections+="best"
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="worstvideo[height>=480][vcodec!*=av01]+((worstaudio[abr>=64][language^=en]/bestaudio[language^=en])/(worstaudio[abr>=64]/bestaudio))/"
    selections+="worst[height>=480][ext=mp4]/" # this line is necessary else we get fragmented formats which are gay
    selections+="worst[height>=480]/"
    selections+="best"

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""
    local use_cookies=""
    
    [[ " $* " == *" --720 "* ]] && selections="bestvideo[height<=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --1080 "* ]] && selections="bestvideo[height<=1080][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --force "* ]] && { archive_flag=""; force_overwrite="--force-overwrites"; }
    [[ " $* " == *" --max "* ]] && selections="bestvideo+bestaudio/best"
    [[ " $* " == *" --cookies "* ]] && use_cookies="true"
    
    # YouTube: default skip_subs (unless --get-subs); Non-YouTube: always get subs
    local is_youtube="" skip_subs=""
    [[ "$url" =~ (youtube\.com|youtu\.be) ]] && is_youtube="true"
    [[ "$is_youtube" = "true" && " $* " != *" --get-subs "* ]] && skip_subs="true"
    [[ " $* " == *" --skip-subs "* ]] && skip_subs="true"

    echo "$url"
    
    local cmd_args=(
        -f "$selections"
        --progress-template "[Downloading] %(info.uploader,info.channel,info.uploader_id)s - %(info.title)s | $progress_format"
        --add-metadata
        --embed-chapters
        --match-filter '!is_live'
        --match-filter 'duration<36000'
        --progress
        --newline
        --merge-output-format mkv
        --remote-components ejs:github
        --sponsorblock-chapter all
        --use-postprocessor 'DeArrow:when=pre_process'
        -o '%(uploader,channel,uploader_id|40.40s)s - %(title)s [%(id)s].%(ext)s'
        $archive_flag
        $force_overwrite
        --exec 'touch {} && echo {} && sync'
    )
    
    [ "$skip_subs" != "true" ] && cmd_args+=(--sub-langs=en,en-orig,en-US,en-x-autogen,en-auto,English --write-subs --write-auto-subs --embed-subs)
    [ "$is_youtube" = "true" ] && cmd_args+=(--exec "python3 $HOME/personal_scripts/inject_yt_subs.py {}")
    [ "$use_cookies" = "true" ] && cmd_args+=(--cookies $HOME/yt-dlp/youtube.com_cookies.txt)
    
    "$HOME/yt-dlp/yt-dlp.sh" "${cmd_args[@]}" "$url" || echo "$url" >> ytdl_failure.txt
}

ytzs() {
    local selections=""
    selections+="hls-221/hls-222/hls-223/hls-224/hls-225/hls-226/hls-227/hls-228/hls-229/hls-22?/hls-21?/" # rumble mp4 640x360
    # selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)/"
    # selections+="worst[height>=480][ext=mp4]/"
    # selections+="worst[height>=480]/"
    # selections+="best"
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="worstvideo[height>=480][vcodec!*=av01]+((worstaudio[abr>=64][language^=en]/bestaudio[language^=en])/(worstaudio[abr>=64]/bestaudio))/"
    selections+="worst[height>=480][ext=mp4]/" # this line is necessary else we get fragmented formats which are gay
    selections+="worst[height>=480]/"
    selections+="best"

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default

    [[ " $* " == *" --720 "* ]] && selections="bestvideo[height<=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --1080 "* ]] && selections="bestvideo[height<=1080][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --force "* ]] && { archive_flag=""; force_overwrite="--force-overwrites"; }
    [[ " $* " == *" --max "* ]] && { selections="bestvideo+bestaudio/best"; }

    echo "${!#}"
    $HOME/yt-dlp/yt-dlp.sh \
        -f "$selections" \
        --progress-template "[Downloading] %(info.uploader,info.channel,info.uploader_id)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-chapters \
        --sub-langs=en,en-orig,en-US,en-x-autogen \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        --merge-output-format mkv \
        --sponsorblock-chapter all \
	      --use-postprocessor 'DeArrow:when=pre_process' \
        -o '%(uploader,channel,uploader_id|40.40s)s - %(title)s [%(id)s].%(ext)s' \
        $archive_flag \
        $force_overwrite \
        --exec 'touch {} && echo {} && sync' "${!#}" || echo "${!#}" >> ytdl_failure.txt
}

ytpl() {
    local selections=""
    selections+="hls-221/hls-222/hls-223/hls-224/hls-225/hls-226/hls-227/hls-228/hls-229/hls-22?/hls-21?/" # rumble mp4 640x360
    # selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/"
    # selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)/"
    # selections+="worst[height>=480][ext=mp4]/"
    # selections+="worst[height>=480]/"
    # selections+="best"
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/"
    selections+="worstvideo[height>=480][vcodec!*=av01]+((worstaudio[abr>=64][language^=en]/bestaudio[language^=en])/(worstaudio[abr>=64]/bestaudio))/"
    selections+="worst[height>=480][ext=mp4]/" # this line is necessary else we get fragmented formats which are gay
    selections+="worst[height>=480]/"
    selections+="best"

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default

    [[ " $* " == *" --720 "* ]] && selections="bestvideo[height<=720][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --1080 "* ]] && selections="bestvideo[height<=1080][vcodec!*=av01]+(bestaudio[abr>=64][language^=en]/bestaudio[abr>=64])/$selections"
    [[ " $* " == *" --force "* ]] && { archive_flag=""; force_overwrite="--force-overwrites"; }
    [[ " $* " == *" --max "* ]] && { selections="bestvideo+bestaudio/best"; }

    echo "${!#}"
    $HOME/yt-dlp/yt-dlp.sh \
        -f "$selections" \
        --progress-template "[Downloading] %(info.uploader,info.channel)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-chapters \
        --sub-langs=en \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        --merge-output-format mkv \
        --sponsorblock-chapter all \
	      --use-postprocessor 'DeArrow:when=pre_process' \
        -o '%(playlist_index)s %(title)s .%(ext)s' \
        $archive_flag \
        $force_overwrite \
        --exec 'touch {} && echo {} && sync' "${!#}" || echo "${!#}" >> ytdl_failure.txt
}

# 
source $HOME/personal_scripts/ytfb.sh

ytmax() {
    ytz --max $1
}

ytzc() {
  ytz --cookies $1
}

alias docker-compose="docker compose"
alias ytdl_id="youtube-dl --get-filename -o '%(channel_id)s'"
ytdl_rss() { VID_ID=$(ytdl_id $1) && echo "https://www.youtube.com/feeds/videos.xml?channel_id=$VID_ID"; }
yfl() { export -f ytz && parallel -u --jobs 6 -a $1 ytz; }

ytinfo() { yt-dlp --dump-json --skip-download $1 | jq --color-output . | less --RAW-CONTROL-CHARS; };
alias yti='ytinfo'
alias ytlist='yfl'
# alias ytsubs="yt-dlp --skip-download --write-sub --sub-lang en"
alias ytsubs="yt-dlp --skip-download --write-sub --write-auto-sub --sub-lang en,en-orig"

ytdl_flat_playlist() { youtube-dl -j --flat-playlist "$1" | jq -r '.id' | sed 's_^_https://youtube.com/v/_'; }
alias yfp='ytdl_flat_playlist'
ytdl_flat_channel() { youtube-dl -j "$1" | jq -r '.id' | sed 's_^_https://youtube.com/v/_'; }
ytdl_soft_flat_channel() { youtube-dl -j "$1" | jq -r '.id'; }

#alias sy='export -f ytz && parallel -u --jobs 4 ytz ::: $(curl http://209.209.9.16:476/lite.php);'
alias sy='export -f ytz && parallel -u --jobs 4 ytz ::: $(list_news);'
alias syp='export -f ytz && export -f ytdl_flat_playlist && parallel -u --jobs 4 ytz ::: $(ytdl_flat_playlist $1);'
# alias ytp='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-fcZOlKWCZn6uP6SJ4btn7G'
# alias ytp7='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-fKGIfEc4IC9pY1ZC22Sa6Q'
# alias ytp8='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-ef0zZtbBhvLLYpGbS_8XsC'
# alias ytp9='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-cou3Jzg__BirgJMv75zgHx'
#alias ytpn='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-em3dpNukt7dVGQ0EHz5SAC'

alias ytw='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-dLfcvHQ5Us0ThR5yM0H2Fd' #water
alias ytpn='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-evYPqaB_Sdk57cYWDofrMz' # sleepy

#alias sqlite='sqlite3'
alias begin_install='apt-get install tmux git curl wget apache2 aria2 php ncdu htop python jq ffmpeg w3m lynx vim sqlite newsboat parallel axel progress rclone which iproute2 mediainfo rsync man man-pages'

alias browse='w3m -M'
alias browser='w3m -M'
alias bro='w3m -M'

backup_newsboat_cache() {  
    DIR=$(dirname $NEWSBOAT_DB_FILE);
    ZIP=$DIR/newsboat_db.zip;
    echo 'Backing up...';
    zip -9 $ZIP $NEWSBOAT_DB_FILE $NEWSBOAT_URLS_FILE $NEWSBOAT_CONFIG_FILEPATH && cp --backup=t $ZIP $NEWSBOAT_DB_BUP_DIR && sync
    #mbup $ZIP
}

backup_newsboat_cache() {
    DIR=$(dirname "$NEWSBOAT_DB_FILE")
    ARCHIVE="$DIR/newsboat_db.tar"
    BACKUP="$DIR/newsboat_db.tar.xz"

    echo "Archiving..."
    tar -cf "$ARCHIVE" \
        "$NEWSBOAT_DB_FILE" \
        "$NEWSBOAT_URLS_FILE" \
        "$NEWSBOAT_CONFIG_FILEPATH" \ 
        "$HOME/my_bash.sh"

    echo "Compressing..."
    xz -9e -f "$ARCHIVE"

    echo "Backing up..."
    cp --backup=t "$BACKUP" "$NEWSBOAT_DB_BUP_DIR"
    sync
    #mbup "$BACKUP"
}

backup_newsboat_cache() {
    DIR=$(dirname "$NEWSBOAT_DB_FILE")
    ARCHIVE="$DIR/newsboat_db.tar"
    BACKUP="$DIR/newsboat_db.tar.xz"

    echo "Archiving..."
    tar -cf "$ARCHIVE" \
        "$NEWSBOAT_DB_FILE" \
        "$NEWSBOAT_URLS_FILE" \
        "$NEWSBOAT_CONFIG_FILEPATH" \
        "$HOME/my_bash.sh" \
    && echo "Compressing..." \
    && xz -9e -f "$ARCHIVE" \
    && echo "Backing up..." \
    && cp --backup=t "$BACKUP" "$NEWSBOAT_DB_BUP_DIR" \
    && sync \
    && echo "Backup complete: $BACKUP"
}

backup_newsboat_cache() {
    DIR=$(dirname "$NEWSBOAT_DB_FILE")
    ARCHIVE="$DIR/newsboat_db.tar"
    BACKUP="$DIR/newsboat_db.tar.xz"

    echo "Vacuuming..."
    sqlite3 "$NEWSBOAT_DB_FILE" "VACUUM;"
    echo "Archiving files..." \
    && tar -chf "$ARCHIVE" \
        "$NEWSBOAT_DB_FILE" \
        "$NEWSBOAT_URLS_FILE" \
        "$NEWSBOAT_CONFIG_FILEPATH" \
        "$HOME/my_bash.sh" \
    && echo "Compressing..." \
    && xz -v -9e -f "$ARCHIVE" \
    && echo "Backing up..." \
    && cp --backup=t "$BACKUP" "$NEWSBOAT_DB_BUP_DIR" \
    && sync \
    #mbup "$BACKUP"
}

alias nbcb='backup_newsboat_cache && cbup $HOME/newsboat/newsboat_db.tar.xz'

# the db file is called the "cache" file for some reason in docs and man so
#alias backup_newsboat_cache="cp --backup=t $NEWSBOAT_DB_FILEPATH $NEWSBOAT_DB_BACKUPS_DIR && sync"
#alias backup_newsboat_cache="zip -9 $NEWSBOAT_DB_BUP_DIR/newsboat_db.zip $NEWSBOAT_DB_FILE && cp --backup=t $NEWSBOAT_DB_BUP_DIR/newsboat_db.zip $NEWSBOAT_DB_BUP_DIR && sync"
#alias backup_newsboat_cache="zip -9 $TMP/newsboat_db.zip $NEWSBOAT_DB_FILE && cp --backup=t $TMP/newsboat_db.zip $NEWSBOAT_DB_BUP_DIR && sync"
#alias newsboat="backup_newsboat_cache && newsboat -c $NEWSBOAT_DB_FILE -C $NEWSBOAT_CONFIG_FILEPATH -u $NEWSBOAT_URLS_FILE"
alias newsboat="newsboat -c $NEWSBOAT_DB_FILE -C $NEWSBOAT_CONFIG_FILEPATH -u $NEWSBOAT_URLS_FILE"
#alias newsboat="newsboat u $NEWSBOAT_URLS_FILE"
alias nb='newsboat'
alias nbdb="backup_newsboat_cache && sqlite3 $NEWSBOAT_DB_FILE"
alias cnt="sqlite3 $NEWSBOAT_DB_FILE 'select count(*) from rss_item where deleted =0;'"
alias nclear="sqlite3 $NEWSBOAT_DB_FILE 'UPDATE rss_item SET deleted=1;'"
alias nc='nclear'
alias list_news="sqlite3 $NEWSBOAT_DB_FILE 'SELECT url FROM rss_item WHERE deleted = 0 ORDER BY pubDate DESC;'"

wget_authed() {
  USER=phoenix;
  PASS=phoenix;
  wget -cr -np -R "index.html*" "$2" "$("echo $1 | sed 's/ http\?:\/\/[^:]*:/\$USER:\$PASS@/'")";
}

download_dir() {
    local username="phoenix"
    local password="phoenix"
    local url="$1"
    local new_url=$(echo "$url" | sed -e "s~^~http://$username:$password\@~")
    echo $new_url
    wget -r --no-parent $new_url
}

hot() {
    GATEWAY_IP=$(ip route | grep def | cut -d ' ' -f 3);
    #sshpass -p "geronimo" ssh -P 8022 -o StrictHostKeyChecking=no moth@$IP
    sshpass -p 'geronimo' ssh -o StrictHostKeyChecking=no -p 8022 moth@$GATEWAY_IP
}

# laravel
laravel_create() { curl -s "https://laravel.build/$1" | bash; } 
alias pa='php artisan'
alias sa='sail artisan'
alias sail='[ -f sail ] && sh sail || sh vendor/bin/sail'
alias tinker='composer dump-autoload && sa tinker'
alias dbf='sa migrate:fresh --seed'
alias sup='sail up -d'
alias lcc='php artisan cache:clear'

alias gs='git status'
alias gp='git push'
alias gb='git branch'

alias dc='docker compose'
alias l2='ollama run llama2-uncensored-succinct'
alias gemma='ollama run gemma2-succinct'
alias gma='gemma'

# review_news() {  
#     ( echo > /dev/tcp/127.0.0.1/5001 ) >/dev/null 2>&1 && echo "Port already in use." && return 1 || echo "Port available...";
#     # termux-open http://localhost:5001
#     am start -a android.intent.action.VIEW -d "http://localhost:5001" org.mozilla.firefox
#     python $HOME/personal_scripts/nbserver/api_server.py --db=$NEWSBOAT_DB_FILE
# }

is_port_in_use() { (echo > /dev/tcp/127.0.0.1/$1) >/dev/null 2>&1; }

# review_news() {
#     local port=5001
#     is_port_in_use "$port" && { echo "Server already running on port $port."; } \
#         || { python "$HOME/personal_scripts/nbserver/api_server.py" --db="$NEWSBOAT_DB_FILE" & sleep 1; }
#     am start -a android.intent.action.VIEW -d "http://localhost:$port" org.mozilla.firefox
# }

# review_news() {
#     local port=5001
#     python "$HOME/personal_scripts/nbserver/api_server.py" --db="$NEWSBOAT_DB_FILE";
#     sleep 1;
#     am start -a android.intent.action.VIEW -d "http://localhost:$port" org.mozilla.firefox
# }

nbserver_db_prepare() {
    curl -s -X GET http://localhost:5001/api/maintenance/prepare | jq -r '.message'
}

nbr() {
    backup_newsboat_cache
    echo "Scanning..."
    newsboat -c "$NEWSBOAT_DB_FILE" -C "$NEWSBOAT_CONFIG_FILEPATH" -u "$NEWSBOAT_URLS_FILE" -x reload print-unread
    nbserver_db_prepare
    termux-vibrate
    termux-notification \
      --title "Open Localhost" \
      --content "NBServer Sync Complete" \
      --action "am start -a android.intent.action.VIEW -d 'http://localhost:5001' org.mozilla.firefox"
}

export OPENSUBTITLES_USERNAME='unverifiedcontact'
export OPENSUBTITLES_PASSWORD='geronimo'
alias sdl='time subliminal download -l en -p opensubtitles .'
alias all_subs='yt-dlp --skip-download --write-subs --write-auto-subs'
alias mi='mediainfo'

# EXPERIMENTAL 
alias mp4towebm='f(){ s=9961472; d=$(ffprobe -v 0 -of csv=p=0 -show_entries format=duration "$1"); vbr=$((s*8/(${d%.*}+1)-48000)); ffmpeg -y -i "$1" -c:v libvpx-vp9 -b:v ${vbr} -pass 1 -an -f null /dev/null && ffmpeg -i "$1" -c:v libvpx-vp9 -b:v ${vbr} -pass 2 -c:a libopus -b:a 48k "${1%.*}.webm"; rm -f ffmpeg2pass-0.log*; }; f'
alias pull_music='rsync -avz -e "ssh -p 8022" moth@192.168.11.59:"/storage/C31A-2B7B/My Music/" .'

# TEMP
alias pgo='docker-compose run --rm laracastdl php ./start.php -s "30-days-to-learn-laravel-11"'
alias pg2='docker-compose run --rm laracastdl php start.php -s "inertia-2-unleashed" -e "12,15" -s "the-definition-series"'
alias pqt='docker stop laracasts-downloader-laracastdl-run-7b6e0c6bbfe6'
alias pqt='docker ps --filter "name=laracasts-downloader" -q | xargs -r docker stop'

# alias fixvtt='
# fixvtt() {
#   local file="$1"
#   if [[ ! -f "$file" ]]; then
#     echo "File not found: $file"
#     return 1
#   fi
#   tmp="$(mktemp)"
#   {
#     echo "WEBVTT"
#     echo ""
#     sed "/^WEBVTT$/d; /^X-TIMESTAMP-MAP=/d; /^[[:space:]]*$/d; s/[[:space:]]\\{1,\\}/ /g" "$file"
#   } > "$tmp" && mv "$tmp" "$file"
# }'

desub() { ffmpeg -i "$1" -map 0 -map -0:s -c copy "$TMP/$1" && rsync --progress "$TMP/$1" "$1" && rm "$TMP/$1"; }

emsub_mkv() {
    local input="$1"
    local subs="$2"
    local tmpdir="${TMPDIR:-/tmp}"
    local base="${input##*/}"
    local name="${base%.*}"
    local output="$tmpdir/${name}.mkv"
    local srt="$tmpdir/${name}.srt"
    local dest="./${name}.mkv"

    local lang=$(basename "$subs" | grep -oE '\.[a-z]{2}(\.srt|\.vtt|\.ass|\.sub)?$' | cut -d. -f2)
    [[ -z "$lang" ]] && lang="eng"

    ffmpeg -y -i "$subs" "$srt"
    mkvmerge -o "$output" "$input" --language 0:$lang "$srt"
    rsync --progress "$output" "$dest"
    rm -f "$output" "$srt"
}

fix_vtt() {
  # Usage: fix_vtt input.vtt [output.vtt]
  local input="$1"
  local output="$2"

  if [[ -z "$input" ]]; then
    echo "Usage: fix_vtt input.vtt [output.vtt]"
    return 1
  fi

  if [[ ! -f "$input" ]]; then
    echo "Input file does not exist!"
    return 1
  fi

  local tmpfile
  tmpfile="$(mktemp)"

  {
    echo "WEBVTT"
    echo ""

    sed '/^WEBVTT$/d' "$input" | \
    sed '/^X-TIMESTAMP-MAP=/d' | \
    sed -E 's/[[:space:]]+$//g'
  } > "$tmpfile"

  if [[ -z "$output" ]]; then
    # Clobber the input file
    mv "$tmpfile" "$input"
  else
    # Write to the specified output
    mv "$tmpfile" "$output"
  fi
}

# temp function
fixaudio() {
  if [ $# -ne 1 ]; then
    echo "Usage: fixaudio <video_file>"
    return 1
  fi

  input="$1"
  filename=$(basename "$input")
  ext="${filename##*.}"
  tmpfile="$HOME/tmp/${filename%.*}_fixed.${ext}"

  ffmpeg -y -i "$input" -c:v copy -c:a aac -b:a 64k "$tmpfile" && mv "$tmpfile" "$input"
}

start_nginx_termux() {
    # Start PHP-FPM if installed and not running
    if command -v php-fpm >/dev/null && ! pgrep php-fpm >/dev/null; then
        php-fpm >/dev/null 2>&1 &
    fi
    # Start Nginx if installed and not running
    if command -v nginx >/dev/null && ! pgrep nginx >/dev/null; then
        nginx >/dev/null 2>&1 &
    fi

    # echo "App at http://$(ip -o -4 addr show wlan0 | awk '{print $4}' | cut -d/ -f1):2473"
}

tokens_count() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "File not found: $file"
    return 1
  fi

  python3 - <<EOF
import tiktoken

# Read file contents
with open("$file", "r", encoding="utf-8") as f:
    text = f.read()

# Choose encoding (replace 'gpt-3.5-turbo' with your model if needed)
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
tokens = enc.encode(text)
print(len(tokens))
EOF
}

# this is just temporary for dev/testing... better later
bait() {
    cd $HOME/personal_scripts/bait_yt_analyse
    source venv/bin/activate
    set -a && source .env && set +a
    python ytprep_cli.py "$@"
    deactivate
}

bait() {
    source "$HOME/personal_scripts/bait_yt_analyse/.env"
    "$HOME/personal_scripts/bait_yt_analyse/venv/bin/python" \
        "$HOME/personal_scripts/bait_yt_analyse/ytprep_cli.py" "$@"
}

yt_ai_summary() {
    [ -z "$1" ] && echo "usage: yt_ai_summary <url>" && return 1
    json="$(ytdlp --dump-json "$1" 2>/dev/null)" || { echo "error"; return 1; }
    summary="$(printf '%s' "$json" | jq -r '.["ai_summary"] // empty')"
    [ -n "$summary" ] && printf '%s\n' "$summary" || echo "nothing found"
}
alias ais=yt_ai_summary

serve_here() {
    port="${1:-6215}"
    tmp=$(mktemp)
    printf 'server.document-root="%s"\nserver.port=%s\ndir-listing.activate="enable"\n' "$PWD" "$port" > "$tmp"
    lighttpd -D -f "$tmp"
    rm -f "$tmp"
}

source $HOME/personal_scripts/rebait/rebait.sh
alias venv='source venv/bin/activate'

START_SERVICES() {
    $HOME/personal_scripts/transcript_service/start_gunicorn.sh
    start_nbserver
    if [ -f "$HOME/IS_MOBILE" ] && command -v am >/dev/null 2>&1; then
      start_nginx_termux
    fi
}
START_SERVICES;