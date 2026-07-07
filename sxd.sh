#!/usr/bin/env bash

mkdir -p "$HOME/.config"
CONFIG_FILE="$HOME/.config/.sxdrc"

if ! command -v curl >/dev/null 2>&1; then
    echo "Error: curl is required but not installed."
    exit 1
fi

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    
    if [ -z "${SXD_INSTANCE_URL:-}" ] || [ -z "${SXD_UPLOAD_TOKEN:-}" ]; then
        echo "Error: SXD_INSTANCE_URL or SXD_UPLOAD_TOKEN is not set in $CONFIG_FILE."
        exit 1
    fi

    if [ "$SXD_UPLOAD_TOKEN" = "1234" ] || [ "$SXD_INSTANCE_URL" = "https://yourdomain.com" ]; then
        echo "Error: Please update $CONFIG_FILE with your actual instance URL and upload token."
        exit 1
    fi

    # strip the trailing slash, if there is one
    SXD_INSTANCE_URL="${SXD_INSTANCE_URL%/}"
else
    echo "Created $CONFIG_FILE. Make sure to add your upload token and instance URL, then re-run this script."
    cat << 'EOF' > "$CONFIG_FILE"
SXD_UPLOAD_TOKEN=1234
SXD_INSTANCE_URL=https://yourdomain.com
EOF
    exit 0
fi

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 <file1> [file2...]"
    exit 1
fi

for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo -e "\033[0;31mError:\033[0m File '$file' not found." >&2
        continue
    fi

    echo -e "\033[0;34mUploading\033[0m '$file'..." >&2
    
    response=$(curl --user-agent "sxd.sh/1.1" -# -w "\n%{http_code}" -X POST -H "Authorization: $SXD_UPLOAD_TOKEN" -F "file=@$file" "$SXD_INSTANCE_URL/upload")
    curl_exit=$?
    
    if [ $curl_exit -ne 0 ]; then
        echo -e "\033[0;31mError:\033[0m curl failed to connect or upload (exit status $curl_exit)." >&2
        continue
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    url=$(echo "$body" | grep -o '"url": *"[^"]*"' | sed 's/"url": *"\(.*\)"/\1/' || true)
    delete_url=$(echo "$body" | grep -o '"delete_url": *"[^"]*"' | sed 's/"delete_url": *"\(.*\)"/\1/' || true)
    error_msg=$(echo "$body" | grep -o '"error": *"[^"]*"' | sed 's/"error": *"\(.*\)"/\1/' || true)

    if [ -n "$url" ]; then
        if [ -n "$delete_url" ]; then
            echo -e "\033[0;32mSuccess!\033[0m (Delete URL: $SXD_INSTANCE_URL$delete_url)" >&2
        else
            echo -e "\033[0;32mSuccess!\033[0m" >&2
        fi
        
        # output only the URL to stdout.
        # if piped, git rid of the trailing newline
        if [ -t 1 ]; then
            echo "$SXD_INSTANCE_URL$url"
        else
            printf "%s" "$SXD_INSTANCE_URL$url"
        fi
    elif [ -n "$error_msg" ]; then
        echo -e "\033[0;31mUpload failed\033[0m (HTTP $http_code): $error_msg" >&2
    else
        if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
            echo -e "\033[0;32mUpload successful\033[0m (HTTP $http_code). Response: $body" >&2
        else
            echo -e "\033[0;31mUpload failed\033[0m (HTTP $http_code). Response: $body" >&2
        fi
    fi
done
