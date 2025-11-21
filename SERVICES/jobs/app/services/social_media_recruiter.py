"""
Social Media Recruiter - AI-Powered Autonomous Recruitment
Connects to Twitter, LinkedIn, Reddit APIs to autonomously recruit candidates
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from anthropic import Anthropic
import httpx

logger = logging.getLogger(__name__)


class SocialMediaRecruiter:
    """AI-powered social media recruitment automation"""

    def __init__(self):
        # API credentials
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.linkedin_access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')

        # AI for content generation
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set - AI content generation disabled")

    async def generate_social_post(
        self,
        job: Dict,
        platform: str,
        style: str = "engaging"
    ) -> Dict:
        """
        Generate AI-optimized social media post for job

        Args:
            job: Job details
            platform: twitter, linkedin, reddit
            style: engaging, professional, technical, viral

        Returns:
            Post content optimized for platform
        """
        if not self.client:
            return self._get_default_post(job, platform)

        try:
            platform_specs = {
                'twitter': {
                    'max_length': 280,
                    'style': 'concise, punchy, with emojis',
                    'call_to_action': 'Apply now 👇',
                    'hashtags': 3
                },
                'linkedin': {
                    'max_length': 3000,
                    'style': 'professional but engaging',
                    'call_to_action': 'See full details and apply',
                    'hashtags': 5
                },
                'reddit': {
                    'max_length': 40000,
                    'style': 'authentic, detailed, community-focused',
                    'call_to_action': 'Apply or AMA in comments',
                    'hashtags': 0
                }
            }

            spec = platform_specs.get(platform, platform_specs['twitter'])

            prompt = f"""Generate a {style} social media post for {platform}.

JOB:
Title: {job['title']}
Description: {job['description'][:500]}...
Budget: ${job['budget']}
Duration: {job['duration']}
Skills: {', '.join(job['skills'])}
URL: http://198.54.123.234:8008/jobs/{job['id']}

PLATFORM SPECS:
- Max length: {spec['max_length']} chars
- Style: {spec['style']}
- Hashtags: {spec['hashtags']}
- Call to action: {spec['call_to_action']}

MAKE IT:
1. Attention-grabbing (hook in first line)
2. Highlight what's UNIQUE (AI interviews, crypto payment, autonomous systems)
3. Clear value prop for the candidate
4. Include link
5. Optimize for engagement (questions, controversy, curiosity)

For Twitter: Thread format if needed (multiple tweets)
For LinkedIn: Professional but not corporate-speak
For Reddit: Authentic, not salesy, community-value first

Generate in JSON:
{{
  "platform": "{platform}",
  "content": "Main post text",
  "thread": ["Tweet 1", "Tweet 2", ...] // only for Twitter if needed
  "hashtags": ["hashtag1", "hashtag2"],
  "media_suggestion": "Image/video idea if applicable",
  "best_time_to_post": "When to post for max engagement",
  "engagement_strategy": "How to respond to comments"
}}

Be creative. Make it viral-worthy."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            post = json.loads(response.content[0].text)

            post['job_id'] = job['id']
            post['generated_at'] = datetime.utcnow().isoformat()

            logger.info(f"✅ Generated {platform} post for {job['title']}")

            return post

        except Exception as e:
            logger.error(f"Error generating post: {e}")
            return self._get_default_post(job, platform)

    async def post_to_twitter(self, content: str, job_url: str) -> Dict:
        """
        Post job to Twitter/X via API

        Note: Requires Twitter API v2 with write permissions
        """
        if not self.twitter_bearer_token:
            return {
                'status': 'not_configured',
                'message': 'Twitter API credentials not set',
                'manual_post': content,
                'url': job_url
            }

        try:
            # Twitter API v2 endpoint
            url = "https://api.twitter.com/2/tweets"

            headers = {
                'Authorization': f'Bearer {self.twitter_bearer_token}',
                'Content-Type': 'application/json'
            }

            data = {
                'text': f"{content}\n\n{job_url}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)

                if response.status_code == 201:
                    tweet_data = response.json()
                    logger.info(f"✅ Posted to Twitter: {tweet_data['data']['id']}")

                    return {
                        'status': 'success',
                        'platform': 'twitter',
                        'tweet_id': tweet_data['data']['id'],
                        'url': f"https://twitter.com/user/status/{tweet_data['data']['id']}",
                        'posted_at': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'status': 'error',
                        'error': response.text,
                        'manual_post': content
                    }

        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'manual_post': content,
                'instructions': 'Post this manually to Twitter'
            }

    async def post_to_linkedin(self, content: str, job_url: str) -> Dict:
        """
        Post job to LinkedIn via API

        Note: Requires LinkedIn API access
        """
        if not self.linkedin_access_token:
            return {
                'status': 'not_configured',
                'message': 'LinkedIn API credentials not set',
                'manual_post': content,
                'url': job_url
            }

        try:
            # LinkedIn UGC API
            url = "https://api.linkedin.com/v2/ugcPosts"

            headers = {
                'Authorization': f'Bearer {self.linkedin_access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            }

            # Get person URN (would need to be configured)
            author = os.getenv('LINKEDIN_PERSON_URN', 'urn:li:person:XXXXXX')

            data = {
                'author': author,
                'lifecycleState': 'PUBLISHED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {
                            'text': f"{content}\n\n{job_url}"
                        },
                        'shareMediaCategory': 'NONE'
                    }
                },
                'visibility': {
                    'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)

                if response.status_code in [200, 201]:
                    logger.info(f"✅ Posted to LinkedIn")

                    return {
                        'status': 'success',
                        'platform': 'linkedin',
                        'posted_at': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'status': 'error',
                        'error': response.text,
                        'manual_post': content
                    }

        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'manual_post': content
            }

    async def find_developers_on_twitter(
        self,
        skills: List[str],
        location: str = "remote"
    ) -> List[Dict]:
        """
        Search Twitter for developers with required skills

        Args:
            skills: List of required skills
            location: Target location

        Returns:
            List of potential candidates with contact info
        """
        if not self.twitter_bearer_token:
            return []

        try:
            # Build search query
            skill_query = ' OR '.join([f'"{skill}"' for skill in skills[:3]])
            query = f'({skill_query}) (developer OR engineer) -job -hiring'

            url = "https://api.twitter.com/2/tweets/search/recent"

            headers = {
                'Authorization': f'Bearer {self.twitter_bearer_token}'
            }

            params = {
                'query': query,
                'max_results': 100,
                'tweet.fields': 'author_id,created_at',
                'user.fields': 'username,description,url'
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()

                    # Extract unique developers
                    candidates = []
                    seen_authors = set()

                    for tweet in data.get('data', []):
                        author_id = tweet['author_id']

                        if author_id not in seen_authors:
                            seen_authors.add(author_id)

                            # Get user details from includes
                            user = next(
                                (u for u in data.get('includes', {}).get('users', [])
                                 if u['id'] == author_id),
                                None
                            )

                            if user:
                                candidates.append({
                                    'platform': 'twitter',
                                    'username': user['username'],
                                    'bio': user.get('description', ''),
                                    'url': user.get('url', ''),
                                    'twitter_id': author_id,
                                    'profile_url': f"https://twitter.com/{user['username']}"
                                })

                    logger.info(f"✅ Found {len(candidates)} potential candidates on Twitter")

                    return candidates[:50]

        except Exception as e:
            logger.error(f"Error searching Twitter: {e}")
            return []

    async def generate_outreach_dm(
        self,
        candidate: Dict,
        job: Dict
    ) -> str:
        """
        Generate personalized DM for candidate outreach

        Args:
            candidate: Candidate profile info
            job: Job details

        Returns:
            Personalized outreach message
        """
        if not self.client:
            return self._get_default_dm(candidate, job)

        try:
            prompt = f"""Generate a personalized DM to recruit this developer.

CANDIDATE:
Username: {candidate.get('username')}
Bio: {candidate.get('bio', 'Not available')}
Platform: {candidate.get('platform')}

JOB:
Title: {job['title']}
What's unique: AI interviews, crypto payments, autonomous systems
Budget: ${job['budget']}
Duration: {job['duration']}
URL: http://198.54.123.234:8008/jobs/{job['id']}

WRITE A DM THAT:
1. References something specific from their bio/tweets (personalized)
2. Explains why they're a great fit
3. Highlights what's unique about this opportunity
4. Keeps it brief (under 200 chars for Twitter DM)
5. Not salesy - genuine and respectful
6. Clear call to action

Make it feel human and personal, not automated."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            dm_text = response.content[0].text.strip()

            logger.info(f"✅ Generated DM for {candidate.get('username')}")

            return dm_text

        except Exception as e:
            logger.error(f"Error generating DM: {e}")
            return self._get_default_dm(candidate, job)

    async def monitor_engagement(
        self,
        post_id: str,
        platform: str
    ) -> Dict:
        """
        Monitor engagement on social media post

        Returns metrics and requires attention items
        """
        # Would integrate with platform APIs to track:
        # - Views, likes, retweets/shares
        # - Comments requiring responses
        # - DMs from interested candidates

        return {
            'post_id': post_id,
            'platform': platform,
            'metrics': {
                'views': 0,
                'likes': 0,
                'shares': 0,
                'comments': 0,
                'applications_attributed': 0
            },
            'requires_attention': [],
            'ai_suggested_responses': []
        }

    def _get_default_post(self, job: Dict, platform: str) -> Dict:
        """Fallback post when AI not available"""
        return {
            'platform': platform,
            'content': f"""🚀 Hiring: {job['title']}

Work on autonomous AI systems. Get paid in crypto. AI reviews your code.

${job['budget']} | {job['duration']} | Remote

Apply: http://198.54.123.234:8008/jobs/{job['id']}

#hiring #ai #remote""",
            'hashtags': ['hiring', 'ai', 'remote'],
            'ai_available': False
        }

    def _get_default_dm(self, candidate: Dict, job: Dict) -> str:
        """Fallback DM when AI not available"""
        return f"""Hi {candidate.get('username')}!

Saw your profile and thought you might be interested in this: {job['title']}

It's unique - AI interviews, crypto payments, working on autonomous systems.

Check it out: http://198.54.123.234:8008/jobs/{job['id']}"""


# Global instance
social_media_recruiter = SocialMediaRecruiter()
