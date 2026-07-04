#!/usr/bin/env bash

mkdir -p "$HOME/.config"
CONFIG_FILE="$HOME/.config/.sxdrc"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    # strip the trailing slash, if there is one
    SXD_INSTANCE_URL="${SXD_INSTANCE_URL%/}"
else
    echo "Created $HOME/.config/.sxdrc. Make sure to add your upload token and instance URL, then re-run this script."
    echo -e "SXD_UPLOAD_TOKEN=1234\nSXD_INSTANCE_URL=https://yourdomain.com" > "$CONFIG_FILE"
    exit
fi

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 <file1> [file2...]"
    exit 1
fi

for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "Error: File '$file' not found."
        continue
    fi

    response=$(curl -s -X POST -H "Authorization: $SXD_UPLOAD_TOKEN" -F "file=@$file" "$SXD_INSTANCE_URL/upload")
    
    if command -v jq >/dev/null 2>&1; then
        url=$(echo "$response" | jq -r '.url' 2>/dev/null)
        if [ "$url" != "null" ] && [ -n "$url" ]; then
            echo "$SXD_INSTANCE_URL$url"
        else
            echo "Response: $response"
        fi
    else
        echo "Response: $response"
    fi
done
