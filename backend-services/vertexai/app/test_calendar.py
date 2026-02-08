#!/usr/bin/env python3
"""
Test script for Google Calendar API integration.
Tests the calendar tools directly without the Agent framework.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coco_agent.tools.calendar_tools import get_calendar_events, create_calendar_event


def main():
    print("🤖 Google Calendar API テスト開始...")
    print("=" * 50)

    # Test 1: Get upcoming events
    print("\n📅 テスト1: 今後の予定を取得中...")
    try:
        result = get_calendar_events(max_results=5, days_ahead=14)
        print(f"結果:\n{result}")
    except Exception as e:
        print(f"❌ 読み取りエラー: {e}")

    print("\n" + "=" * 50)

    # Test 2: Create a test event
    print("\n📝 テスト2: テスト予定を作成中...")
    try:
        # Create an event for tomorrow at 15:00-16:00 JST
        from datetime import datetime, timedelta

        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        end_time = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)

        result = create_calendar_event(
            summary="【テスト】ロボットからの招待",
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            description="Calendar API テストで作成された予定です。"
        )
        print(f"作成結果:\n{result}")
    except Exception as e:
        print(f"❌ 書き込みエラー: {e}")

    print("\n" + "=" * 50)
    print("✅ テスト完了")


if __name__ == "__main__":
    main()
