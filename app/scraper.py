import itertools
import logging
from pathlib import Path

import instaloader
from instaloader.exceptions import (
    InstaloaderException, LoginRequiredException,
    PrivateProfileNotFollowedException, ProfileNotExistsException,
    TooManyRequestsException,
)

from .config import settings

log = logging.getLogger(__name__)
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".mp4", ".webp"}


class ScrapeError(Exception):
    def __init__(self, msg: str, code: int = 502):
        super().__init__(msg)
        self.code = code


def _loader(dest: Path) -> instaloader.Instaloader:
    L = instaloader.Instaloader(
        dirname_pattern=str(dest),
        filename_pattern="{date_utc:%Y%m%d_%H%M%S}_{shortcode}",
        download_comments=False, save_metadata=False,
        download_video_thumbnails=False, compress_json=False,
        quiet=True, max_connection_attempts=2,
    )
    if settings.ig_username and settings.ig_session_file:
        L.load_session_from_file(settings.ig_username, str(settings.ig_session_file))
    return L


def _collect(dest: Path) -> list[str]:
    return sorted(str(p.relative_to(settings.download_dir))
                  for p in dest.rglob("*") if p.suffix.lower() in MEDIA_EXT)


def download_post(job_id: str, shortcode: str) -> list[str]:
    dest = settings.download_dir / job_id
    L = _loader(dest)
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        if post.owner_profile.is_private:
            raise ScrapeError("post belongs to a private account", 403)
        L.download_post(post, target=dest.name)
    except TooManyRequestsException:
        raise ScrapeError("rate limited by Instagram, retry later", 429)
    except LoginRequiredException:
        raise ScrapeError("Instagram requires login; configure a session", 401)
    except InstaloaderException as e:
        raise ScrapeError(f"could not fetch post: {e}", 404)
    return _collect(dest)


def download_profile(job_id: str, username: str, limit: int) -> list[str]:
    limit = min(limit, settings.max_posts_per_profile)
    dest = settings.download_dir / job_id
    L = _loader(dest)
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        if profile.is_private:
            raise ScrapeError("profile is private", 403)
        for post in itertools.islice(profile.get_posts(), limit):
            L.download_post(post, target=dest.name)
    except ProfileNotExistsException:
        raise ScrapeError("profile not found", 404)
    except PrivateProfileNotFollowedException:
        raise ScrapeError("profile is private", 403)
    except TooManyRequestsException:
        raise ScrapeError("rate limited by Instagram, retry later", 429)
    except LoginRequiredException:
        raise ScrapeError("Instagram requires login; configure a session", 401)
    except InstaloaderException as e:
        raise ScrapeError(f"could not fetch profile: {e}", 502)
    return _collect(dest)
