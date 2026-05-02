"""
Social Media Auto-Scheduler
Posts daily to Twitter/X and LinkedIn using AI-generated content.
Deploy on Railway or Render (free tier).
"""

import os
import json
import time
import random
import logging
import requests
import schedule
from datetime import datetime
from dotenv import load_dotenv
import anthropic
import tweepy
from requests_oauthlib import OAuth1

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────

TOPICS = [
    "Tech / AI breakthroughs and how they affect everyday work",
    "Business growth strategies and entrepreneurship mindset",
    "Marketing tips, content strategy, and audience building",
    "Productivity hacks for founders and creators",
    "Startup lessons, failures, and what to learn from them",
]

POST_TIMES = {
    "twitter": ["09:00", "17:00"],   # 9 AM and 5 PM daily
    "linkedin": ["08:30", "12:00"],  # 8:30 AM and noon daily
}

# ── AI Content Generation ────────────────────────────────────────────────────

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def generate_twitter_post(topic: str) -> str:
    """Generate a punchy Twitter/X post under 280 chars."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                f"Write a single high-engagement Twitter/X post about: {topic}.\n"
                "Rules:\n"
                "- Max 280 characters\n"
                "- Punchy, insightful, conversational\n"
                "- End with a question or call to action\n"
                "- Use 1-2 relevant emojis max\n"
                "- No hashtags (they reduce reach)\n"
                "Return ONLY the post text, nothing else."
            )
        }]
    )
    return message.content[0].text.strip()


def generate_linkedin_post(topic: str) -> str:
    """Generate a professional LinkedIn post (3-5 short paragraphs)."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": (
                f"Write a high-engagement LinkedIn post about: {topic}.\n"
                "Rules:\n"
                "- 150-300 words\n"
                "- Start with a bold hook (first line is the preview)\n"
                "- 3-5 short paragraphs with line breaks between them\n"
                "- Professional but human tone\n"
                "- End with a question to drive comments\n"
                "- 2-3 relevant hashtags at the end\n"
                "Return ONLY the post text, nothing else."
            )
        }]
    )
    return message.content[0].text.strip()


# ── Twitter/X Posting ────────────────────────────────────────────────────────

def post_to_twitter(text: str) -> bool:
    """Post a tweet using Twitter API v2 with OAuth 1.0a."""
    try:
        client_tw = tweepy.Client(
            consumer_key=os.environ["TWITTER_API_KEY"],
            consumer_secret=os.environ["TWITTER_API_SECRET"],
            access_token=os.environ["TWITTER_ACCESS_TOKEN"],
            access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
        )
        response = client_tw.create_tweet(text=text)
        tweet_id = response.data["id"]
        log.info(f"✅ Tweeted! ID: {tweet_id}")
        return True
    except Exception as e:
        log.error(f"❌ Twitter post failed: {e}")
        return False


# ── LinkedIn Posting ─────────────────────────────────────────────────────────

def get_linkedin_user_id(access_token: str) -> str:
    """Fetch the LinkedIn user URN needed for posting."""
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    r.raise_for_status()
    return r.json()["sub"]  # returns the person URN ID


def post_to_linkedin(text: str) -> bool:
    """Post to LinkedIn using the Share API v2."""
    try:
        access_token = os.environ["LINKEDIN_ACCESS_TOKEN"]
        author_id = get_linkedin_user_id(access_token)
        author_urn = f"urn:li:person:{author_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        r = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()
        post_id = r.headers.get("x-restli-id", "unknown")
        log.info(f"✅ LinkedIn posted! ID: {post_id}")
        return True
    except Exception as e:
        log.error(f"❌ LinkedIn post failed: {e}")
        return False


# ── Scheduled Jobs ───────────────────────────────────────────────────────────

def job_twitter():
    topic = random.choice(TOPICS)
    log.info(f"📝 Generating Twitter post | Topic: {topic}")
    text = generate_twitter_post(topic)
    log.info(f"Post preview: {text[:80]}...")
    post_to_twitter(text)


def job_linkedin():
    topic = random.choice(TOPICS)
    log.info(f"📝 Generating LinkedIn post | Topic: {topic}")
    text = generate_linkedin_post(topic)
    log.info(f"Post preview: {text[:80]}...")
    post_to_linkedin(text)


def setup_schedule():
    for t in POST_TIMES["twitter"]:
        schedule.every().day.at(t).do(job_twitter)
        log.info(f"🕐 Twitter scheduled at {t} daily")

    for t in POST_TIMES["linkedin"]:
        schedule.every().day.at(t).do(job_linkedin)
        log.info(f"🕐 LinkedIn scheduled at {t} daily")


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("🚀 Social Media Scheduler starting...")
    setup_schedule()

    # Optional: post immediately on startup to test
    if os.getenv("POST_ON_STARTUP", "false").lower() == "true":
        log.info("POST_ON_STARTUP=true — posting now to test...")
        job_twitter()
        time.sleep(3)
        job_linkedin()

    log.info("⏳ Scheduler running. Waiting for next post time...")
    while True:
        schedule.run_pending()
        time.sleep(30)
