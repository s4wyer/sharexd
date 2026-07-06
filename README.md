# sharexd

A minimalist, secure, self-hosted file sharing server built with Python and Flask.

Main Page                            | Image Viewer                                        |  Audio Player |
:-----------------------------------:|:---------------------------------------------------:|:---------------:|
![Main Page](assets/mainpage.png)    | ![Image Page](assets/imagepage.png)                 | ![Audio Player](assets/audiopage.png) |
[Preview](https://x.sawyer.systems)  | [Preview](https://x.sawyer.systems/view/i22xo.png)  | [Preview](https://x.sawyer.systems/view/8xvq7.m4a) |

## Features

- Simple interface, only a little bloat.
- S3 or local storage support.
- Automatic .sxcu generation (just fill in your access token).
- Token-based authentication.
- Heavily restricted CSP headers for viewing files, and attempts to serve potentially dangerous files as plain text to avoid any potential XSS attacks.

## Setup

1. Clone the repo
   ```bash
   git clone https://github.com/s4wyer/sharexd.git
   cd sharexd
   ```

2. Copy the example environment file and set your custom values (especially the upload token).
   ```bash
   cp .env.example .env
   ```

3. Install dependencies. I use uv for dependency management (but pip works fine).
   ```bash
   uv sync
   # or using pip:
   # pip install .
   ```

4. Run the server
   ```bash
   flask --app main run --host=0.0.0.0 --port=5000
   ```
5. (Optional) Set up S3 support in .env (example configuration for R2 [here](docs/r2_setup.md))

## Uploading Files

Just go to wherever you have the project running to find a ShareX config.

The project also includes a script called [sxd.sh](sxd.sh). Install jq, run the script to generate a config and upload files with:

```bash
./sxd.sh abc123.txt def456.txt
```

Uploads require the `Authorization` header to match your configured `UPLOAD_TOKEN`.

```bash
curl -X POST -H "Authorization: YOUR_SECRET_TOKEN_HERE" -F "file=@yourfile.png" http://localhost:5000/upload
```

The response will provide the URL to the uploaded file:
```json
{"url": "/abc123def456.txt"}
```

Images return a link to a viewer:
```json
{"url": "/view/abc123def456.txt"}
```
