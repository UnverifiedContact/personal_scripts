if [ -f "$HOME/IS_MOBILE" ]; then
	RCLONE_CONFIG=$HOME/rclone.conf
	export RCLONE_CONFIG
	export TMP=$HOME/tmp
	[[ -z "${CARD_VIDS_PATH}" ]] && echo 'WARNING: CARD_VIDS_PATH is not set.';
	alias ol="time rsync -av --progress --size-only . $CARD_VIDS_PATH"
	alias clean_landing='time rm --verbose *.mp4 && rm --verbose *.mkv && rm --verbose *.webm'
    alias clean_landing='extensions="mp4 mkv webm vtt part ytdl jpg webp srt mp3 avi"; time for ext in $extensions; do rm --verbose *."$ext"; done'
	. `which env_parallel.bash`
	#sshd && sv-enable sshd
    #apachectl restart && sv-enable httpd
    source $PREFIX/etc/profile.d/start-services.sh
    sv-enable sshd
    sv-enable httpd
else
	xset b off # no beep
	export TMP='/tmp'
	export PATH="$HOME/.local/bin:$PATH" # for pipx binaries
fi

[[ -z "${NEWSBOAT_DB_BUP_DIR}" ]] && echo 'WARNING: NEWSBOAT_DB_BUP_DIR is not set.';

## news related functions
export NEWSBOAT_DB_FILE="$HOME/newsboat/newsboat_cache.db"
export NEWSBOAT_CONFIG_FILEPATH="$HOME/newsboat/newsboat_config"
export NEWSBOAT_URLS_FILE="$HOME/newsboat/newsboat_urls_file"
alias sub="python3 $HOME/personal_scripts/subscribe.py"
alias dld="python3 $HOME/personal_scripts/dldir.py"
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

ytz() {
    local selections=""
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)"
    selections+='/worst[height>=480][ext=mp4]'
    selections+='/worst[height>=480]'
    selections+='/best'

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default

    [[ "$1" == "--force" ]] && { archive_flag=""; force_overwrite="--force-overwrites"; shift; }
    [[ "$1" == "--max" ]] && { selections="bestvideo+bestaudio/best"; shift; }

    echo "$1"
    $HOME/yt-dlp/yt-dlp.sh \
        -f "$selections" \
        --progress-template "[Downloading] %(info.uploader,info.channel)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-thumbnail \
        --embed-chapters \
        --sub-langs=en \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        -o '%(uploader|30.30s)s - [%(id)s].%(ext)s' \
        $archive_flag \
        $force_overwrite \
        --exec 'touch {} && echo {} && sync' "$1" || echo "$1" >> ytdl_failure.txt
}

ytzs() {
    local selections=""
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)"
    selections+='/worst[height>=480][ext=mp4]'
    selections+='/worst[height>=480]'
    selections+='/best'

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default

    [[ "$1" == "--force" ]] && { archive_flag=""; force_overwrite="--force-overwrites"; shift; }
    [[ "$1" == "--max" ]] && { selections="bestvideo+bestaudio/best"; shift; }

    echo "$1"
    $HOME/yt-dlp/yt-dlp.sh \
        -f "$selections" \
        --progress-template "[Downloading] %(info.uploader,info.channel)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-thumbnail \
        --embed-chapters \
        --sub-langs=en,de \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        -o '%(uploader|30.30s)s - [%(id)s].%(ext)s' \
        $archive_flag \
        $force_overwrite \
        --exec 'touch {} && echo {} && sync' "$1" || echo "$1" >> ytdl_failure.txt
}

ytzxxxx() {
    local selections=""
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)"
    selections+='/worst[height>=480][ext=mp4]'
    selections+='/worst[height>=480]'
    selections+='/best'

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default

    [[ "$1" == "--force" ]] && { archive_flag=""; force_overwrite="--force-overwrites"; shift; }
    [[ "$1" == "--max" ]] && { selections=""; shift; }

    echo "$1"
    $HOME/yt-dlp/yt-dlp.sh \
        -f "$selections" \
        --progress-template "[Downloading] %(info.uploader,info.channel)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-thumbnail \
        --embed-chapters \
        --sub-langs=en \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        -o '%(uploader|30s)s - %(description|40s)s [%(id)s].%(ext)s' --match-filter 'extractor=facebook' \
        -o '%(uploader,channel|40.40s)s - %(title|50.50s)s [%(id)s].%(ext)s' \
        $archive_flag \
        $force_overwrite \
        --exec 'touch {} && echo {} && sync' "$1" || echo "$1" >> ytdl_failure.txt
}

ytz2222() {

    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local selections="";
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/best";
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/best";
    selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)";
    selections+='/worst[height>=480][ext=mp4]';
    selections+='/worst[height>=480]';
    selections+='/best';
    
    [[ "$1" == "--force" ]] && archive_flag="" && shift
    [[ "$1" == "--max" ]] && selections="" && shift
    echo "$1"
    
    $HOME/yt-dlp/yt-dlp.sh ${selections:+-f "$selections"} \
        --progress-template "[Downloading] %(info.uploader,channel)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-thumbnail \
        --embed-chapters \
        --sub-langs=en \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        -o '%(uploader|40.40s)s - %(description|50.50s)s [%(id)s].%(ext)s' --match-filter 'extractor=facebook' \
        -o '%(uploader|40.40s)s - %(title|50.50s)s [%(id)s].%(ext)s'\
        $archive_flag \
        --exec 'touch {} && echo {} && sync' "$1" || echo "$1" >> ytdl_failure.txt
}

# --download-archive $HOME/yt-dlp/ytdl_success.txt \

ytz22() {
    echo $1
    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s";
    local selections="";
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/best";
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/best";
    selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)";
    selections+='/worst[height>=480][ext=mp4]';
    selections+='/worst[height>=480]';
    selections+='/best';
    
    if [[ $1 == *"facebook.com"* ]]; then
        outformat='fb_%(uploader|10.10s)s_%(id)s.%(ext)s'
        outformat='%(uploader|40.40s)s - %(description|20.20s)s [%(id)s].%(ext)s'
        thumbformat='fb_%(id)s.%(ext)s'
    else
        outformat='%(uploader|40.40s)s - %(title|50.50s)s [%(id)s].%(ext)s'
        thumbformat='%(id)s.%(ext)s'
    fi
    
    $HOME/yt-dlp/yt-dlp.sh -f $selections \
    --progress-template "[Downloading] %(info.uploader,channel)s - %(info.title)s | $progress_format" \
    --add-metadata \
    --convert-thumbnails jpg \
    --output-na-placeholder "" \
    --paths "thumbnail:$thumbformat" \
    --embed-thumbnail \
    --embed-chapters \
    --sub-langs=en \
    --match-filter '!is_live' \
    --match-filter 'duration<36000' \
    --embed-subs \
    --write-auto-subs \
    --progress \
    --newline \
    -o "$outformat" \
    --exec 'touch {} && echo {} && sync' $1 || echo $1 >> ytdl_failure.txt
}

ytz_old() {
    echo $1
	local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s";
	local selections="";
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/best";
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/best";
	selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)";
	selections+='/worst[height>=480][ext=mp4]';
	selections+='/worst[height>=480]';
	selections+='/best';
	
		$HOME/yt-dlp/yt-dlp.sh -f $selections \
	--progress-template "[Downloading] %(info.uploader,channel)s - %(info.title)s | $progress_format" \
	--add-metadata \
	--embed-thumbnail \
	--embed-chapters \
	--sub-langs=en \
	--match-filter '!is_live' \
	--match-filter 'duration<36000' \
	--embed-subs \
	--write-auto-subs \
	--progress \
	--newline \
	--download-archive $HOME/yt-dlp/ytdl_success.txt \
    -o '%(uploader|40.40s)s - %(title|50.50s)s [%(id)s].%(ext)s' \
    --exec 'touch {} && echo {} && sync' $1 || echo $1 >> ytdl_failure.txt
}

ytmax() {
    echo $1
	local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s";
	
		$HOME/yt-dlp/yt-dlp.sh \
	--progress-template "[Downloading] %(info.uploader)s - %(info.title)s | $progress_format" \
	--add-metadata \
	--embed-thumbnail \
	--embed-chapters \
	--sub-langs=en \
	--match-filter '!is_live' \
	--match-filter 'duration<36000' \
	--embed-subs \
	--write-auto-subs \
	--progress \
	--newline \
    -o '%(uploader,channel)s - %(title).200s [%(id)s].%(ext)s' \
    --exec 'touch {} && echo {} && sync' $1 || echo $1 >> ytdl_failure.txt
}

ytz2() {
    echo $1
    local progress_format="%(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s"
    local selections=""
    selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)"
    selections+='/worst[height>=360][ext=mp4]'
    selections+='/worst[height>=360]'
    selections+='/best'
    local download_archive_flag=()

    if [[ $2 != "--force" ]]; then
        download_archive_flag=(--download-archive "$HOME/yt-dlp/ytdl_success.txt")
    fi

    $HOME/yt-dlp/yt-dlp.sh -4 -f $selections \
        --progress-template "[Downloading] %(info.uploader,channel)s - %(info.title)s | $progress_format" \
        --add-metadata \
        --embed-thumbnail \
        --embed-chapters \
        --sub-langs=en \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        "${download_archive_flag[@]}" \
        -o '%(uploader,channel)s - %(title)s [%(id)s].%(ext)s' \
        --exec 'touch {} && echo {} && sync' $1 || echo $1 >> ytdl_failure.txt
}

alias docker-compose="docker compose"
alias ytdl_id="youtube-dl --get-filename -o '%(channel_id)s'"
ytdl_rss() { VID_ID=$(ytdl_id $1) && echo "https://www.youtube.com/feeds/videos.xml?channel_id=$VID_ID"; }
yfl() { export -f ytz && parallel -u --jobs 6 -a $1 ytz; }

ytinfo() { yt-dlp --dump-json --skip-download $1 | jq --color-output . | less --RAW-CONTROL-CHARS; };
alias yti='ytinfo'
alias ytlist='yfl'
# alias ytsubs="yt-dlp --skip-download --write-sub --sub-lang en"
alias ytsubs="yt-dlp --skip-download --write-sub --write-auto-sub --sub-lang en"

ytdl_flat_playlist() { youtube-dl -j --flat-playlist "$1" | jq -r '.id' | sed 's_^_https://youtube.com/v/_'; }
alias yfp='ytdl_flat_playlist'
ytdl_flat_channel() { youtube-dl -j "$1" | jq -r '.id' | sed 's_^_https://youtube.com/v/_'; }
ytdl_soft_flat_channel() { youtube-dl -j "$1" | jq -r '.id'; }

#alias sy='export -f ytz && parallel -u --jobs 4 ytz ::: $(curl http://209.209.9.16:476/lite.php);'
alias sy='export -f ytz && parallel -u --jobs 4 ytz ::: $(list_news);'
alias syp='export -f ytz && export -f ytdl_flat_playlist && parallel -u --jobs 4 ytz ::: $(ytdl_flat_playlist $1);'
alias ytp='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-fcZOlKWCZn6uP6SJ4btn7G'
alias ytp7='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-fKGIfEc4IC9pY1ZC22Sa6Q'
alias ytp8='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-ef0zZtbBhvLLYpGbS_8XsC'
alias ytp9='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-cou3Jzg__BirgJMv75zgHx'
alias ytpn='ytz https://www.youtube.com/playlist?list=PLannLfUUpj-fT4AfNO0JPP4WVk2HZdNA6'

alias sqlite='sqlite3'
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

alias nbcb='backup_newsboat_cache && cbup $HOME/newsboat/newsboat_db.zip'

# the db file is called the "cache" file for some reason in docs and man so
#alias backup_newsboat_cache="cp --backup=t $NEWSBOAT_DB_FILEPATH $NEWSBOAT_DB_BACKUPS_DIR && sync"
#alias backup_newsboat_cache="zip -9 $NEWSBOAT_DB_BUP_DIR/newsboat_db.zip $NEWSBOAT_DB_FILE && cp --backup=t $NEWSBOAT_DB_BUP_DIR/newsboat_db.zip $NEWSBOAT_DB_BUP_DIR && sync"
#alias backup_newsboat_cache="zip -9 $TMP/newsboat_db.zip $NEWSBOAT_DB_FILE && cp --backup=t $TMP/newsboat_db.zip $NEWSBOAT_DB_BUP_DIR && sync"
#alias newsboat="backup_newsboat_cache && newsboat -c $NEWSBOAT_DB_FILE -C $NEWSBOAT_CONFIG_FILEPATH -u $NEWSBOAT_URLS_FILE"
alias newsboat="newsboat -c $NEWSBOAT_DB_FILE -C $NEWSBOAT_CONFIG_FILEPATH -u $NEWSBOAT_URLS_FILE"
#alias newsboat="newsboat u $NEWSBOAT_URLS_FILE"
alias nb='backup_newsboat_cache && newsboat'
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

alias pull_music='rsync -avz -e "ssh -p 8022" moth@192.168.11.59:"/storage/C31A-2B7B/My Music/" .'
alias dc='docker compose'
#alias l2='ollama run llama2-uncensored'
alias l2='ollama run llama2-uncensored-succinct'

alias gemma='ollama run gemma2-succinct'
alias gma='gemma'

alias pgo='docker-compose run --rm laracastdl php ./start.php -s "30-days-to-learn-laravel-11"'
alias pg2='docker-compose run --rm laracastdl php start.php -s "inertia-2-unleashed" -e "12,15" -s "the-definition-series"'
alias pqt='docker stop laracasts-downloader-laracastdl-run-7b6e0c6bbfe6'
alias pqt='docker ps --filter "name=laracasts-downloader" -q | xargs -r docker stop'
