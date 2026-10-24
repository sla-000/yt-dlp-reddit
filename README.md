# yt-dlp-reddit

[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](http://unlicense.org/)
[![Topic: yt-dlp-plugins](https://img.shields.io/badge/topic-yt--dlp--plugins-orange.svg)](https://github.com/topics/yt-dlp-plugins)

A plugin for [yt-dlp](https://github.com/yt-dlp/yt-dlp) that adds headless support for downloading Reddit videos without requiring authentication or cookies.

---

## The Problem

Reddit has blocked unauthenticated access to its legacy `.json` metadata endpoints (returning `HTTP Error 403: Blocked`). When using standard `yt-dlp` without cookies on public Reddit links, `yt-dlp` fails with:

```
ERROR: [Reddit] <id>: Account authentication is required. Use --cookies-from-browser or --cookies for the authentication.
```

However, public Reddit videos can be viewed in standard web browsers without logging in, via Reddit's modern **Shreddit** frontend. When queried, Reddit issues a lightweight JavaScript Challenge (`js_challenge=1`), generates session tokens, and renders the video inside `<shreddit-player>` with signed HLS manifests.

## What This Plugin Does

This plugin acts as a **transparent fallback wrapper** around `yt-dlp`'s built-in `RedditIE`:
1. It first lets `yt-dlp` attempt standard extraction (preserving 100% of existing functionality for logged-in sessions, crossposts, galleries, and embeds).
2. If the built-in extractor fails due to Reddit's unauthenticated block, this plugin intercepts the error:
   - Automatically solves Reddit's client JavaScript challenge on the fly.
   - Obtains anonymous session tokens (`token_v2`, `loid`, etc.).
   - Parses the Shreddit HTML (`<shreddit-player>` and `<shreddit-post>`).
   - Extracts signed `HLSPlaylist.m3u8` streams, direct MP4 permutations, subtitles (`.vtt`), thumbnails, and post metadata.

---

## Installation

### Method 1: Drop-in Zip (Recommended for Standalone Binaries)

1. Download `yt-dlp-reddit.zip` from the latest [Release](https://github.com/sla0x00/yt-dlp-reddit/releases).
2. Place the `.zip` file into your `yt-dlp` plugins directory:
   - **macOS / Linux**: `~/.yt-dlp/plugins/` (or `~/.config/yt-dlp/plugins/`)
   - **Windows**: `%APPDATA%/yt-dlp/plugins/`

*No unzipping required — `yt-dlp` loads zip plugins automatically.*

### Method 2: Via pip

If you installed `yt-dlp` in Python:

```bash
pip install git+https://github.com/sla0x00/yt-dlp-reddit.git
```

### Method 3: Portable / Local Directory

Place the `yt_dlp_plugins` directory inside `yt-dlp-plugins/` next to your `yt-dlp` executable:

```text
yt-dlp
yt-dlp-plugins/
    yt-dlp-reddit/
        yt_dlp_plugins/
            extractor/
                reddit.py
```

---

## Verification

Run `yt-dlp` with the `-v` flag:

```bash
yt-dlp -v 'https://www.reddit.com/r/Pikabu/comments/1xa1dkp/%D0%BC%D1%8F%D1%83%D0%BA%D1%80%D0%B0%D1%84%D1%82/'
```

You should see:
```text
[debug] Extractor Plugins: shreddit (RedditIE)
[Reddit+shreddit] Extracting URL: ...
[Reddit+shreddit] Downloading webpage
[Reddit+shreddit] Downloading m3u8 information
[info] Downloading 1 format(s): hls-594+hls-4-audio_0
```

---

## License

This project is released into the public domain under the [The Unlicense](LICENSE).
