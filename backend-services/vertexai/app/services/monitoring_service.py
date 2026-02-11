"""
MonitoringLoopService: バックグラウンドで定期的にカメラ画像を取得・分析するサービス。
is_suspended フラグにより、Explorer Agent との排他制御を実現する。
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class MonitoringLoopService:
    """定期的な監視ループを管理するサービスクラス。

    is_suspended フラグで一時停止・再開を制御し、
    Explorer Agent がカメラを操作する際の競合を防ぐ。
    """

    def __init__(self, scan_interval_seconds: int = 30):
        self._is_suspended = False
        self._suspended_by: Optional[str] = None
        self._suspended_at: Optional[float] = None
        self._suspend_duration: Optional[int] = None
        self._scan_interval = scan_interval_seconds
        self._loop_task: Optional[asyncio.Task] = None
        self._running = False
        logger.info(
            f"MonitoringLoopService initialized (interval={scan_interval_seconds}s)"
        )

    @property
    def is_suspended(self) -> bool:
        """現在の一時停止状態を返す。タイムアウトも自動チェックする。"""
        if self._is_suspended and self._suspend_duration and self._suspended_at:
            elapsed = time.time() - self._suspended_at
            if elapsed >= self._suspend_duration:
                logger.info(
                    f"Suspend duration ({self._suspend_duration}s) expired. Auto-resuming."
                )
                self._is_suspended = False
                self._suspended_by = None
                self._suspended_at = None
                self._suspend_duration = None
        return self._is_suspended

    def suspend(self, reason: str = "explorer_request", duration: int = 300) -> dict:
        """監視ループを一時停止する。

        Args:
            reason: 一時停止の理由（例: "explorer_request"）
            duration: 一時停止の最大秒数（デフォルト: 300秒）

        Returns:
            一時停止の状態を示す辞書
        """
        self._is_suspended = True
        self._suspended_by = reason
        self._suspended_at = time.time()
        self._suspend_duration = duration
        logger.info(
            f"Monitoring SUSPENDED by '{reason}' for {duration}s"
        )
        return {
            "status": "suspended",
            "reason": reason,
            "duration_seconds": duration,
            "message": f"監視を {duration} 秒間停止しました。理由: {reason}",
        }

    def resume(self) -> dict:
        """監視ループを再開する。

        Returns:
            再開の状態を示す辞書
        """
        was_suspended = self._is_suspended
        self._is_suspended = False
        suspended_by = self._suspended_by
        self._suspended_by = None
        self._suspended_at = None
        self._suspend_duration = None

        if was_suspended:
            logger.info(
                f"Monitoring RESUMED (was suspended by '{suspended_by}')"
            )
            return {
                "status": "resumed",
                "message": "監視を再開しました。",
            }
        else:
            logger.info("Resume called but monitoring was not suspended.")
            return {
                "status": "already_running",
                "message": "監視は既に実行中です。",
            }

    def get_status(self) -> dict:
        """現在の監視ステータスを返す。"""
        return {
            "is_suspended": self.is_suspended,
            "suspended_by": self._suspended_by,
            "scan_interval_seconds": self._scan_interval,
            "loop_running": self._running,
        }


# グローバルシングルトンインスタンス
# Monitor Agent プロセス内で一つだけ存在する
_monitoring_service: Optional[MonitoringLoopService] = None


def get_monitoring_service() -> MonitoringLoopService:
    """MonitoringLoopService のシングルトンインスタンスを取得する。"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringLoopService()
    return _monitoring_service
