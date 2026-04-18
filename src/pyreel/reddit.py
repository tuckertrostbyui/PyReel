from typing import Optional

from .config import PyReelConfig
from .exceptions import PyReelRedditError


def fetch_post(
    subreddit: str,
    post_id: Optional[str],
    config: PyReelConfig,
    exclude_ids: Optional[set] = None,
) -> dict:
    if not config.reddit_client_id or not config.reddit_client_secret:
        raise PyReelRedditError(
            "reddit_client_id and reddit_client_secret are required in PyReelConfig."
        )

    try:
        import praw
    except ImportError as e:
        raise PyReelRedditError("praw is not installed.") from e

    try:
        reddit = praw.Reddit(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent,
        )

        if post_id:
            submission = reddit.submission(id=post_id)
            _validate_submission(submission, config)
            return _submission_to_dict(submission)

        sub = reddit.subreddit(subreddit)
        for submission in sub.hot(limit=25):
            if submission.stickied:
                continue
            if config.nsfw_filter and submission.over_18:
                continue
            if not submission.is_self:
                continue
            if not submission.selftext or submission.selftext in ("[removed]", "[deleted]"):
                continue
            if exclude_ids and submission.id in exclude_ids:
                continue
            return _submission_to_dict(submission)

        raise PyReelRedditError(
            f"No suitable text posts found in r/{subreddit}."
        )

    except PyReelRedditError:
        raise
    except Exception as e:
        raise PyReelRedditError(f"Reddit API error: {e}") from e


def _validate_submission(submission, config: PyReelConfig) -> None:
    if config.nsfw_filter and submission.over_18:
        raise PyReelRedditError(
            f"Post {submission.id} is marked NSFW and nsfw_filter=True."
        )


def _submission_to_dict(submission) -> dict:
    return {
        "id": submission.id,
        "title": submission.title,
        "body": submission.selftext,
        "url": f"https://reddit.com{submission.permalink}",
        "author": str(submission.author) if submission.author else "unknown",
    }
