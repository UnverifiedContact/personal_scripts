ytfb() {
    local selections=""
    selections+="bestvideo[height<=480][height>=480][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="bestvideo[height<=720][height>=720][vcodec!*=av01]+bestaudio[abr>=64]/best"
    selections+="worstvideo[height>=480][vcodec!*=av01]+(worstaudio[abr>=64]/bestaudio)"
    selections+='/worst[height>=480][ext=mp4]'
    selections+='/worst[height>=480]'
    selections+='/best'

    # Get metadata first
    local metadata=$(python3 "$HOME/personal_scripts/fb_video_metadata.py" --format json "$1")
    if [ $? -ne 0 ]; then
        echo "Failed to get metadata for $1"
        return 1
    fi

    # Extract filenames from JSON
    local progress_template=$(echo "$metadata" | jq -r '.ytdlp_filename')
    local output_filename=$(echo "$metadata" | jq -r '.ytdlp_filename_mp4')

    local archive_flag="--download-archive $HOME/yt-dlp/ytdl_success.txt"
    local force_overwrite=""  # No force overwrite by default

    [[ "$1" == "--force" ]] && { archive_flag=""; force_overwrite="--force-overwrites"; shift; }
    [[ "$1" == "--max" ]] && { selections="bestvideo+bestaudio/best"; shift; }

    echo "$1"
    $HOME/yt-dlp/yt-dlp.sh \
        -f "$selections" \
        --progress-template "[Downloading] $progress_template | %(progress._percent_str)s ETA: %(progress._eta_str)s Speed: %(progress._speed_str)s Size: %(progress._total_bytes_str)s" \
        --add-metadata \
        --embed-chapters \
        --sub-langs=en \
        --match-filter '!is_live' \
        --match-filter 'duration<36000' \
        --embed-subs \
        --write-auto-subs \
        --progress \
        --newline \
        -o "$output_filename" \
        $archive_flag \
        $force_overwrite \
        --exec 'touch {} && echo {} && sync' "$1" || echo "$1" >> ytdl_failure.txt
}