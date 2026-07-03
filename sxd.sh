#!/usr/bin/env bash

INSTANCE_URL="http://localhost:5000"
UPLOAD_TOKEN="YOUR_TOKEN"

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 <file1> [file2...]"
    exit 1
fi

for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "Error: File '$file' not found."
        continue
    fi

    response=$(curl -s -X POST -H "Authorization: $UPLOAD_TOKEN" -F "file=@$file" "$INSTANCE_URL/upload")
    
    if command -v jq >/dev/null 2>&1; then
        url=$(echo "$response" | jq -r '.url')
        if [ "$url" != "null" ] && [ -n "$url" ]; then
            echo "$INSTANCE_URL$url"
        else
            echo "Response: $response"
        fi
    else
        echo "Response: $response"
    fi
done
