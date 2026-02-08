"""
Google Calendar Tools for ADK Agent.
Uses service account authentication to access a shared calendar.
"""

import os
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
# CALENDAR_ID is optional. If not set, calendar tools will return a message indicating configuration is missing.
CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID")
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')

# Cache the service to avoid repeated initialization
_calendar_service = None


def _get_calendar_service():
    """Get authenticated Calendar service using service account credentials."""
    global _calendar_service
    if _calendar_service is not None:
        return _calendar_service

    try:
        if not os.path.exists(CREDENTIALS_PATH):
            logger.error(f"Credentials file not found: {CREDENTIALS_PATH}")
            return None

        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH, scopes=SCOPES
        )
        _calendar_service = build('calendar', 'v3', credentials=credentials)
        return _calendar_service
    except Exception as e:
        logger.error(f"Failed to initialize Calendar service: {e}")
        return None


def get_calendar_events(max_results: int = 10, days_ahead: int = 7) -> str:
    """
    Retrieves upcoming events from the shared Google Calendar.

    Args:
        max_results: Maximum number of events to retrieve (default: 10)
        days_ahead: Number of days ahead to look for events (default: 7)

    Returns:
        JSON string containing list of upcoming events or error message
    """
    if not CALENDAR_ID:
        return json.dumps({"status": "error", "message": "Google Calendar ID is not configured."})

    service = _get_calendar_service()
    if service is None:
        return json.dumps({"error": "Calendar service not available. Check credentials."})

    try:
        # Calculate time range
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days_ahead)).isoformat()

        # Fetch events
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return json.dumps({
                "status": "success",
                "message": "今後の予定はありません。",
                "events": []
            }, ensure_ascii=False)

        # Format events for response
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            formatted_events.append({
                "id": event.get('id'),
                "summary": event.get('summary', '(タイトルなし)'),
                "start": start,
                "end": end,
                "description": event.get('description', ''),
                "location": event.get('location', '')
            })

        return json.dumps({
            "status": "success",
            "message": f"{len(formatted_events)}件の予定が見つかりました。",
            "events": formatted_events
        }, ensure_ascii=False, indent=2)

    except HttpError as e:
        logger.error(f"Calendar API error: {e}")
        return json.dumps({"error": f"Calendar API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Failed to get calendar events: {e}")
        return json.dumps({"error": f"Failed to get events: {str(e)}"})


def create_calendar_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = ""
) -> str:
    """
    Creates a new event on the shared Google Calendar.

    Args:
        summary: Event title/summary (required)
        start_datetime: Start date and time in ISO format, e.g., "2026-02-10T10:00:00" (required)
        end_datetime: End date and time in ISO format, e.g., "2026-02-10T11:00:00" (required)
        description: Event description (optional)
        location: Event location (optional)

    Returns:
        JSON string containing creation result or error message
    """
    if not CALENDAR_ID:
        return json.dumps({"status": "error", "message": "Google Calendar ID is not configured."})

    service = _get_calendar_service()
    if service is None:
        return json.dumps({"error": "Calendar service not available. Check credentials."})

    try:
        # Build event body
        event_body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'Asia/Tokyo',
            },
        }

        # Create event
        event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event_body
        ).execute()

        return json.dumps({
            "status": "success",
            "message": f"予定「{summary}」を作成しました。",
            "event_id": event.get('id'),
            "html_link": event.get('htmlLink')
        }, ensure_ascii=False)

    except HttpError as e:
        logger.error(f"Calendar API error: {e}")
        return json.dumps({"error": f"Calendar API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return json.dumps({"error": f"Failed to create event: {str(e)}"})
