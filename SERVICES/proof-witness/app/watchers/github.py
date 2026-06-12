"""
Proof Witness - GitHub Watcher

Automatically captures commits as proof candidates.
Zero human effort - just commit code and proof gets logged.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import hashlib
import hmac

from app.models import ProofCandidate, ProofSource, ProofType
from app.storage import storage
from app.tagging import tagger
from app.config import settings

logger = logging.getLogger(__name__)


class GitHubWatcher:
    """
    Watches GitHub for commits and creates proof candidates

    Receives webhooks from GitHub, validates them, creates proof.
    """

    def verify_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """Verify GitHub webhook signature"""
        if not settings.GITHUB_WEBHOOK_SECRET:
            logger.warning("GitHub webhook secret not configured, skipping verification")
            return True

        if not signature_header:
            return False

        hash_algorithm, github_signature = signature_header.split('=')
        algorithm = hashlib.__dict__.get(hash_algorithm)
        encoded_key = settings.GITHUB_WEBHOOK_SECRET.encode()
        mac = hmac.new(encoded_key, msg=payload_body, digestmod=algorithm)

        return hmac.compare_digest(mac.hexdigest(), github_signature)

    async def handle_push(self, payload: Dict[str, Any]) -> list[str]:
        """
        Handle GitHub push webhook

        Returns: List of proof candidate IDs created
        """
        repo_name = payload.get('repository', {}).get('name', 'unknown')
        commits = payload.get('commits', [])
        pusher = payload.get('pusher', {}).get('name', 'unknown')

        candidate_ids = []

        for commit in commits:
            commit_id = commit.get('id', '')
            message = commit.get('message', '')
            url = commit.get('url', '')
            author = commit.get('author', {}).get('username', pusher)
            timestamp_str = commit.get('timestamp', '')

            # Parse timestamp
            try:
                occurred_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                occurred_at = datetime.utcnow()

            # Create title
            title = f"{repo_name}: {message.split('\n')[0][:100]}"

            # Auto-tag
            text = f"{repo_name} {message}"
            suggested_tags = tagger.suggest_tags(text, url)
            tags = [tag for tag, conf in suggested_tags]
            confidence = suggested_tags[0][1] if suggested_tags else 0.5

            # Suggest question
            suggested_question = tagger.suggest_question(tags, title) if tags else None

            # Generate content draft
            content_draft = tagger.generate_content_draft(title, tags, url)

            # Create proof candidate
            candidate = ProofCandidate(
                id="",  # Will be assigned by storage
                source=ProofSource.GITHUB,
                type=ProofType.CODE,
                owner=author,
                title=title,
                description=message,
                url=url,
                data={
                    "repo": repo_name,
                    "commit_id": commit_id[:7],
                    "full_commit_id": commit_id,
                    "files_changed": len(commit.get('added', [])) + len(commit.get('modified', [])) + len(commit.get('removed', []))
                },
                tags=tags,
                suggested_question=suggested_question,
                confidence=confidence,
                occurred_at=occurred_at,
                content_draft=content_draft
            )

            # Store
            candidate_id = storage.add_candidate(candidate)
            candidate_ids.append(candidate_id)

            logger.info(f"Created proof candidate from GitHub commit: {candidate_id} ({author}: {title})")

        return candidate_ids

    async def handle_deployment(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        Handle GitHub deployment webhook

        Deployments are high-value proof - something shipped to production.
        """
        deployment = payload.get('deployment', {})
        repo_name = payload.get('repository', {}).get('name', 'unknown')
        environment = deployment.get('environment', 'production')
        creator = deployment.get('creator', {}).get('login', 'unknown')
        description = deployment.get('description', '')

        # Create title
        title = f"{repo_name} deployed to {environment}"

        # Auto-tag
        text = f"{repo_name} {environment} {description}"
        suggested_tags = tagger.suggest_tags(text)
        tags = [tag for tag, conf in suggested_tags]

        # Deployments are always high confidence
        confidence = 0.9

        # Generate content draft
        content_draft = f"🚀 Deployed {repo_name} to {environment}\n\n{description}\n\n#ShipIt #Deployment"

        # Create proof candidate
        candidate = ProofCandidate(
            id="",
            source=ProofSource.GITHUB,
            type=ProofType.CODE,
            owner=creator,
            title=title,
            description=description or f"Deployed to {environment}",
            url=deployment.get('url', ''),
            data={
                "repo": repo_name,
                "environment": environment,
                "deployment_id": deployment.get('id', '')
            },
            tags=tags,
            suggested_question=None,
            confidence=confidence,
            occurred_at=datetime.utcnow(),
            content_draft=content_draft
        )

        # Store
        candidate_id = storage.add_candidate(candidate)

        logger.info(f"Created proof candidate from GitHub deployment: {candidate_id} ({creator}: {title})")

        return candidate_id


# Global instance
github_watcher = GitHubWatcher()
