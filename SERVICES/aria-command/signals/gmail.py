#!/usr/bin/env python3
"""
Gmail Integration
=================
Fetches and processes emails from Gmail.

Features:
- OAuth2 authentication
- Fetch unread emails
- Extract sender, subject, body
- Priority classification
- Mark as processed
"""
import os
import json
import base64
import logging
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger("signals.gmail")

# Gmail credentials path
GMAIL_CREDENTIALS = os.getenv("GMAIL_CREDENTIALS", "/opt/fpai/gmail_credentials.json")
GMAIL_TOKEN = os.getenv("GMAIL_TOKEN", "/opt/fpai/gmail_token.json")


@dataclass
class Email:
    """An email message."""
    id: str
    thread_id: str
    sender: str
    sender_email: str
    subject: str
    body: str
    received_at: str
    is_unread: bool


class GmailClient:
    """
    Gmail API client.
    """
    
    def __init__(self):
        self.service = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize Gmail API connection."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
                      'https://www.googleapis.com/auth/gmail.modify']
            
            creds = None
            
            # Load existing token
            if os.path.exists(GMAIL_TOKEN):
                creds = Credentials.from_authorized_user_file(GMAIL_TOKEN, SCOPES)
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(GMAIL_CREDENTIALS):
                        logger.warning("Gmail credentials not found")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GMAIL_CREDENTIALS, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save token
                with open(GMAIL_TOKEN, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=creds)
            self.initialized = True
            logger.info("Gmail client initialized")
            return True
            
        except ImportError:
            logger.warning("Gmail API libraries not installed")
            return False
        except Exception as e:
            logger.error(f"Gmail initialization error: {e}")
            return False
    
    def get_unread_emails(self, max_results: int = 10) -> List[Email]:
        """Fetch unread emails."""
        if not self.initialized and not self.initialize():
            return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg_info in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=msg_info['id'],
                    format='full'
                ).execute()
                
                email = self._parse_message(msg)
                if email:
                    emails.append(email)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _parse_message(self, msg: Dict) -> Optional[Email]:
        """Parse Gmail message into Email object."""
        try:
            headers = msg.get('payload', {}).get('headers', [])
            
            # Extract headers
            sender = ""
            sender_email = ""
            subject = ""
            received_at = ""
            
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                
                if name == 'from':
                    # Parse "Name <email@example.com>"
                    if '<' in value:
                        parts = value.split('<')
                        sender = parts[0].strip().strip('"')
                        sender_email = parts[1].strip('>')
                    else:
                        sender_email = value
                        sender = value.split('@')[0]
                
                elif name == 'subject':
                    subject = value
                
                elif name == 'date':
                    received_at = value
            
            # Extract body
            body = self._get_body(msg.get('payload', {}))
            
            return Email(
                id=msg['id'],
                thread_id=msg.get('threadId', ''),
                sender=sender,
                sender_email=sender_email,
                subject=subject,
                body=body[:1000],  # Limit body length
                received_at=received_at,
                is_unread='UNREAD' in msg.get('labelIds', [])
            )
            
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None
    
    def _get_body(self, payload: Dict) -> str:
        """Extract body from message payload."""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    if 'body' in part and part['body'].get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                
                # Recurse into multipart
                if 'parts' in part:
                    body = self._get_body(part)
                    if body:
                        return body
        
        return ""
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        if not self.initialized:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking as read: {e}")
            return False


# Singleton
_client: Optional[GmailClient] = None

def get_gmail_client() -> GmailClient:
    global _client
    if _client is None:
        _client = GmailClient()
    return _client


async def fetch_unread_emails(max_results: int = 10) -> List[Email]:
    """Fetch unread emails."""
    return get_gmail_client().get_unread_emails(max_results)








