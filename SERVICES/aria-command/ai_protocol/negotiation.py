#!/usr/bin/env python3
"""
Scheduling Negotiation
======================
Handles scheduling negotiation between AIs.

Flow:
1. External AI requests meeting
2. JAI checks calendar, proposes times
3. External AI picks a time
4. JAI confirms, updates calendar
5. Both parties notified
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

logger = logging.getLogger("ai_protocol.negotiation")


class ScheduleNegotiator:
    """
    Negotiates schedules with external AIs.
    """
    
    def __init__(self):
        self.business_hours = (9, 17)  # 9 AM - 5 PM
        self.buffer_minutes = 15  # Buffer between meetings
        self.max_slots_to_propose = 5
    
    def get_available_slots(
        self,
        duration: int = 1,
        preferred_days: List[str] = None,
        days_ahead: int = 14
    ) -> List[Dict]:
        """
        Get available time slots.
        
        Args:
            duration: Meeting duration in hours
            preferred_days: List of preferred weekdays (e.g., ["Monday", "Tuesday"])
            days_ahead: How many days ahead to look
        
        Returns:
            List of available slots
        """
        slots = []
        
        try:
            from signals.calendar import check_availability
            calendar_available = True
        except:
            calendar_available = False
        
        now = datetime.now()
        
        for day_offset in range(1, days_ahead + 1):
            check_date = now + timedelta(days=day_offset)
            
            # Skip weekends
            if check_date.weekday() >= 5:
                continue
            
            # Check preferred days
            day_name = check_date.strftime("%A")
            if preferred_days and day_name not in preferred_days:
                continue
            
            # Check each hour in business hours
            for hour in range(self.business_hours[0], self.business_hours[1]):
                slot_start = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(hours=duration)
                
                # Skip if past business hours
                if slot_end.hour > self.business_hours[1]:
                    continue
                
                # Check calendar if available
                is_available = True
                if calendar_available:
                    is_available = check_availability(slot_start, slot_end)
                
                if is_available:
                    slots.append({
                        "date": check_date.strftime("%Y-%m-%d"),
                        "day": day_name,
                        "start": slot_start.strftime("%I:%M %p"),
                        "end": slot_end.strftime("%I:%M %p"),
                        "start_iso": slot_start.isoformat(),
                        "end_iso": slot_end.isoformat()
                    })
                    
                    if len(slots) >= self.max_slots_to_propose:
                        return slots
        
        return slots
    
    def confirm_slot(self, slot: Dict, attendees: List[str], title: str) -> bool:
        """
        Confirm a slot and create calendar event.
        
        Args:
            slot: The slot to confirm
            attendees: List of attendee emails
            title: Meeting title
        
        Returns:
            True if successfully confirmed
        """
        try:
            # For now, just log - would create calendar event
            logger.info(f"Confirmed slot: {slot['date']} {slot['start']} - {title}")
            
            # Log activity
            try:
                from presence import log_activity
                log_activity("meeting", f"Scheduled: {title} on {slot['date']}", "handled")
            except:
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error confirming slot: {e}")
            return False
    
    def propose_alternative(
        self,
        original_request: Dict,
        reason: str
    ) -> Dict:
        """
        Propose alternative when original request can't be met.
        """
        # Get new slots
        new_slots = self.get_available_slots(
            duration=original_request.get("duration", 1)
        )
        
        return {
            "reason": reason,
            "alternative_slots": new_slots,
            "message": f"The requested time isn't available. Here are {len(new_slots)} alternatives."
        }


# Singleton
_negotiator: Optional[ScheduleNegotiator] = None

def get_negotiator() -> ScheduleNegotiator:
    global _negotiator
    if _negotiator is None:
        _negotiator = ScheduleNegotiator()
    return _negotiator








