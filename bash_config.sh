#!/usr/bin/env bash

#=============================================================================
# Security Configuration
#=============================================================================

# Download credentials
export DOWNLOAD_USER="your_username"
export DOWNLOAD_PASS="your_password"

# Remote access credentials
export REMOTE_PASS="your_remote_password"

# GPG encryption key (use a secure method to store this)
export GPG_PASSPHRASE="your_gpg_passphrase"

#=============================================================================
# Path Configuration
#=============================================================================

# Application paths
export CARD_VIDS_PATH="/path/to/your/videos"
export NEWSBOAT_DB_BUP_DIR="/path/to/your/backups"

#=============================================================================
# Mobile Environment Detection
#=============================================================================

# Set this to true if you're on a mobile device
export IS_MOBILE=false

#=============================================================================
# Service Configuration
#=============================================================================

# Rclone configuration
export RCLONE_CONFIG="$HOME/rclone.conf"

# Temporary directory
export TMP="/tmp"

#=============================================================================
# Application Configuration
#=============================================================================

# Newsboat configuration
export NEWSBOAT_DB_FILE="$HOME/newsboat/newsboat_cache.db"
export NEWSBOAT_CONFIG_FILEPATH="$HOME/newsboat/newsboat_config"
export NEWSBOAT_URLS_FILE="$HOME/newsboat/newsboat_urls_file"

# YouTube-DL configuration
export YTDL_ARCHIVE="$HOME/yt-dlp/ytdl_success.txt"
export YTDL_FAILURE="$HOME/yt-dlp/ytdl_failure.txt" 