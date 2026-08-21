from __future__ import annotations

from pathlib import Path

import tweepy

from fpl_x.config import Settings


class TwitterError(RuntimeError):
    pass


def post_image(settings: Settings, text: str, image_path: Path) -> str:
    api_key, api_secret, access_token, access_token_secret = settings.require_x()
    image_path = Path(image_path)
    if not image_path.is_file():
        raise TwitterError(f"Graphic not found: {image_path}")

    auth = tweepy.OAuth1UserHandler(
        api_key,
        api_secret,
        access_token,
        access_token_secret,
    )
    api = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    try:
        media = api.media_upload(filename=str(image_path))
        response = client.create_tweet(text=text, media_ids=[media.media_id])
    except tweepy.TweepyException as exc:
        raise TwitterError(f"X API request failed: {exc}") from exc

    tweet_id = None
    if response and getattr(response, "data", None):
        tweet_id = response.data.get("id")
    return str(tweet_id) if tweet_id else ""
