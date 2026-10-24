import re
import urllib.parse

from yt_dlp.extractor.reddit import RedditIE
from yt_dlp.jsinterp import JSInterpreter
from yt_dlp.utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    truncate_string,
    unescapeHTML,
    url_or_none,
)


class _RedditPluginIE(RedditIE, plugin_name='shreddit'):
    """
    yt-dlp extractor plugin for Reddit.
    Adds support for Reddit's modern Shreddit frontend, solves Reddit's
    client JavaScript challenge, and extracts signed HLS/MP4 streams
    without requiring authentication cookies.
    """

    def _download_reddit_webpage(self, url, video_id, note='Downloading webpage'):
        webpage = self._download_webpage(url, video_id, note=note, fatal=False)
        if not webpage:
            return None

        if 'name="js_challenge"' in webpage:
            action = self._search_regex(
                r'<form[^>]+action=["\']([^"\']+)["\']', webpage, 'form action', default=None)
            target_url = urllib.parse.urljoin(url, action) if action else url

            jsc_token = self._search_regex(
                r'name=["\']jsc_token["\']\s+value=["\']([^"\']+)["\']',
                webpage, 'jsc_token', default=None)
            expr, seed = self._search_regex(
                r'\(async\s+e\s*=>\s*([^)]+)\)\s*\(\s*["\']([^"\']+)["\']\s*\)',
                webpage, 'challenge', default=(None, None), group=(1, 2))
            if jsc_token and seed:
                solution = None
                if expr:
                    try:
                        jsi = JSInterpreter(f'function solve(e) {{ return {expr}; }}')
                        solution = jsi.extract_function('solve')([seed])
                    except Exception:
                        pass
                if not solution:
                    solution = seed + seed
                query = {
                    'solution': solution,
                    'js_challenge': '1',
                    'jsc_token': jsc_token,
                    'jsc_orig_r': '',
                }
                webpage = self._download_webpage(
                    target_url, video_id, note='Solving Reddit JS challenge', query=query, fatal=False)

        return webpage

    def _extract_from_webpage(self, url, slug, display_id):
        webpage = self._download_reddit_webpage(url, display_id)
        if not webpage:
            return None

        player = self._search_regex(
            r'(<shreddit-player\b[^>]+>)', webpage, 'shreddit player', default=None)
        post = self._search_regex(
            r'(<shreddit-post\b[^>]+>)', webpage, 'shreddit post', default=None)

        if not player and not post:
            return None

        title = unescapeHTML(self._search_regex(
            r'\bpost-title="([^"]+)"', player or post or '', 'title', default=None))
        uploader = unescapeHTML(self._search_regex(
            r'\bauthor="([^"]+)"', post or '', 'author', default=None))
        subreddit = self._search_regex(
            r'\bsubreddit-name="([^"]+)"', player or post or '', 'subreddit', default=None)
        score = int_or_none(self._search_regex(
            r'\b(?:post-)?score="([^"]+)"', player or post or '', 'score', default=None))
        timestamp = parse_iso8601(self._search_regex(
            r'\b(?:post-)?created-(?:at|timestamp)="([^"]+)"', player or post or '', 'timestamp', default=None))
        comment_count = int_or_none(self._search_regex(
            r'\bcomment-count="([^"]+)"', post or '', 'comment_count', default=None))

        # Check for external links if no video player
        if not player and post:
            content_href = unescapeHTML(self._search_regex(
                r'\bcontent-href="([^"]+)"', post, 'content_href', default=''))
            domain = self._search_regex(r'\bdomain="([^"]+)"', post, 'domain', default=None)
            if content_href and domain and 'v.redd.it' not in domain and 'reddit.com' not in domain:
                return {
                    '_type': 'url_transparent',
                    'url': content_href,
                    'id': display_id,
                    'display_id': display_id,
                    'title': truncate_string(title, 72) if title else None,
                    'alt_title': title,
                    'uploader': uploader,
                    'channel_id': subreddit,
                    'like_count': score,
                    'comment_count': comment_count,
                    'timestamp': timestamp,
                }

        if not player:
            return None

        src = unescapeHTML(self._search_regex(r'\bsrc="([^"]+)"', player, 'hls src', default=None))
        if not src:
            src = unescapeHTML(self._search_regex(
                r'<source[^>]+src="([^"]+)"[^>]+type="application/vnd\.apple\.mpegURL"',
                webpage, 'hls source', default=None))

        video_id = self._search_regex(
            r'https?://v\.redd\.it/(?P<id>[^/?#&]+)', src or '', 'video_id', default=display_id)

        formats = []
        subtitles = {}

        # 1. HLS formats & subtitles
        if src:
            hls_fmts, hls_subs = self._extract_m3u8_formats_and_subtitles(
                src, display_id, 'mp4', m3u8_id='hls', fatal=False)
            formats.extend(hls_fmts)
            self._merge_subtitles(hls_subs, target=subtitles)

        # 2. Subtitles from caption-url
        caption_url = unescapeHTML(self._search_regex(
            r'\bcaption-url="([^"]+)"', player, 'caption_url', default=None))
        if caption_url:
            self._merge_subtitles({'en': [{'url': caption_url}]}, target=subtitles)
        else:
            self._merge_subtitles(self.extract_subtitles(video_id), target=subtitles)

        # 3. Direct formats from packaged-media-json
        pkg_json = self._search_regex(
            r'\bpackaged-media-json="([^"]+)"', player, 'packaged-media-json', default=None)
        duration = None
        if pkg_json:
            pkg_data = self._parse_json(unescapeHTML(pkg_json), display_id, fatal=False) or {}
            duration = int_or_none(traverse_obj(pkg_data, ('playbackMp4s', 'duration')))
            for perm in traverse_obj(pkg_data, ('playbackMp4s', 'permutations', ...), expected_type=dict):
                source = perm.get('source') or {}
                mp4_url = url_or_none(source.get('url'))
                if not mp4_url:
                    continue
                formats.append({
                    'url': mp4_url,
                    'format_id': f'mp4-{traverse_obj(source, ("dimensions", "height")) or "direct"}',
                    'width': int_or_none(traverse_obj(source, ('dimensions', 'width'))),
                    'height': int_or_none(traverse_obj(source, ('dimensions', 'height'))),
                    'tbr': float_or_none(source.get('bitrateBps'), scale=1000),
                    'vcodec': source.get('videoCodec'),
                    'ext': 'mp4',
                })

        # 4. Preview / fallback
        preview = unescapeHTML(self._search_regex(
            r'\bpreview="([^"]+)"', player, 'preview', default=None))
        if preview and preview.endswith('.mp4'):
            formats.append({
                'url': preview,
                'format_id': 'preview-96p',
                'height': 96,
                'ext': 'mp4',
                'vcodec': 'h264',
                'acodec': 'none',
                'preference': -10,
            })

        # 5. Thumbnails
        thumbnails = []
        poster = unescapeHTML(self._search_regex(
            r'\bposter="([^"]+)"', player, 'poster', default=None))
        if poster:
            thumbnails.append({'url': poster})
        if preview and preview.endswith(('.jpg', '.png', '.webp')):
            thumbnails.append({'url': preview})

        for img_url in re.findall(r'<img[^>]+slot="poster"[^>]+src="([^"]+)"', webpage):
            thumbnails.append({'url': unescapeHTML(img_url)})

        over_18 = bool(self._search_regex(
            r'\b(?:over-18|nsfw)\b', player or post or '', 'over_18', default=None))

        description = clean_html(self._search_regex(
            r'<div[^>]+slot="text-body"[^>]*>(.*?)</div>', webpage, 'description', default=None))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': truncate_string(title, 72) if title else None,
            'alt_title': title,
            'description': description,
            'uploader': uploader,
            'channel_id': subreddit,
            'like_count': score,
            'comment_count': comment_count,
            'timestamp': timestamp,
            'duration': duration,
            'thumbnails': thumbnails,
            'age_limit': 18 if over_18 else 0,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        try:
            return super()._real_extract(url)
        except ExtractorError:
            slug, video_id = self._match_valid_url(url).group('slug', 'id')
            info = self._extract_from_webpage(url, slug, video_id)
            if info:
                return info
            raise

