#!/usr/bin/env python3
"""
Calendar Integration
====================
Integrates with Google Calendar for:
- Fetching upcoming events
- Checking availability
- Creating events
- Sending heads-up notifications
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger("signals.calendar")

CALENDAR_TOKEN = os.getenv("CALENDAR_TOKEN", "/opt/fpai/calendar_token.json")
CALENDAR_CREDENTIALS = os.getenv("CALENDAR_CREDENTIALS", "/opt/fpai/calendar_credentials.json")


@dataclass
class CalendarEvent:
    """A calendar event."""
    id: str
    title: str
    start: datetime
    end: datetime
    location: Optional[str]
    description: Optional[str]
    attendees: List[str]
    is_all_day: bool


class CalendarClient:
    """
    Google Calendar API client.
    """
    
    def __init__(self):
        self.service = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize Calendar API connection."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
                      'https://www.googleapis.com/auth/calendar.events']
            
            creds = None
            
            if os.path.exists(CALENDAR_TOKEN):
                creds = Credentials.from_authorized_user_file(CALENDAR_TOKEN, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(CALENDAR_CREDENTIALS):
                        logger.warning("Calendar credentials not found")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CALENDAR_CREDENTIALS, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                with open(CALENDAR_TOKEN, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('calendar', 'v3', credentials=creds)
            self.initialized = True
            logger.info("Calendar client initialized")
            return True
            
        except ImportError:
            logger.warning("Calendar API libraries not installed")
            return False
        except Exception as e:
            logger.error(f"Calendar initialization error: {e}")
            return False
    
    def get_upcoming_events(self, hours: int = 24, max_results: int = 10) -> List[CalendarEvent]:
        """Get upcoming events in the next N hours."""
        if not self.initialized and not self.initialize():
            return []
        
        try:
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(hours=hours)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [self._parse_event(e) for e in events]
            
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []
    
    def _parse_event(self, event: Dict) -> CalendarEvent:
        """Parse Google Calendar event."""
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        # Check if all-day event
        is_all_day = 'date' in event['start'] and 'dateTime' not in event['start']
        
        # Parse dates
        if is_all_day:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            end_dt = datetime.strptime(end, '%Y-%m-%d')
        else:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        return CalendarEvent(
            id=event['id'],
            title=event.get('summary', 'Untitled'),
            start=start_dt,
            end=end_dt,
            location=event.get('location'),
            description=event.get('description'),
            attendees=[a.get('email', '') for a in event.get('attendees', [])],
            is_all_day=is_all_day
        )
    
    def get_events_needing_heads_up(self, minutes_before: int = 30) -> List[Dict]:
        """Get events that need a heads-up notification."""
        events = self.get_upcoming_events(hours=2)
        
        now = datetime.now()
        heads_up = []
        
        for event in events:
            time_until = event.start - now
            minutes_until = time_until.total_seconds() / 60
            
            if 0 < minutes_until <= minutes_before:
                # Format time until
                if minutes_until < 60:
                    time_str = f"{int(minutes_until)} minutes"
                else:
                    hours = int(minutes_until / 60)
                    time_str = f"{hours} hour{'s' if hours > 1 else ''}"
                
                heads_up.append({
                    "event": event,
                    "name": event.title,
                    "time_until": time_str,
                    "context": event.description[:100] if event.description else ""
                })
        
        return heads_up
    
    def check_availability(self, start: datetime, end: datetime) -> bool:
        """Check if time slot is available."""
        if not self.initialized and not self.initialize():
            return True  # Assume available if can't check
        
        try:
            time_min = start.isoformat() + 'Z'
            time_max = end.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True
            ).execute()
            
            events = events_result.get('items', [])
            return len(events) == 0
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return True
    
    def get_available_slots(self, date: datetime, duration_hours: int = 1) -> List[Dict]:
        """Get available time slots on a given date."""
        if not self.initialized and not self.initialize():
            return []
        
        # Business hours: 9 AM - 5 PM
        start_hour = 9
        end_hour = 17
        
        slots = []
        current = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        
        while current.hour < end_hour:
            end = current + timedelta(hours=duration_hours)
            
            if self.check_availability(current, end):
                slots.append({
                    "start": current.strftime("%I:%M %p"),
                    "end": end.strftime("%I:%M %p"),
                    "datetime": current
                })
            
            current += timedelta(hours=1)
        
        return slots


# Singleton
_client: Optional[CalendarClient] = None

def get_calendar_client() -> CalendarClient:
    global _client
    if _client is None:
        _client = CalendarClient()
    return _client


async def get_upcoming_events(hours: int = 24) -> List[CalendarEvent]:
    """Get upcoming events."""
    return get_calendar_client().get_upcoming_events(hours)


async def get_heads_up_events() -> List[Dict]:
    """Get events needing heads-up notifications."""
    return get_calendar_client().get_events_needing_heads_up()


def check_availability(start: datetime, end: datetime) -> bool:
    """Check availability for a time slot."""
    return get_calendar_client().check_availability(start, end)








