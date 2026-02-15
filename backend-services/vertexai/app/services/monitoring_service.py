
"""
MonitoringLoopService: バックグラウンドで定期的にカメラ画像を取得・分析するサービス。
is_suspended フラグにより、Explorer Agent との排他制御を実現する。
"""

from typing import Optional, Callable
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class MonitoringLoopService:
    """定期的な監視ループを管理するサービスクラス。

    is_suspended フラグで一時停止・再開を制御し、
    Explorer Agent がカメラを操作する際の競合を防ぐ。
    また、一定時間アイドル状態が続いた場合に全方位スキャンを行う。
    """

    def __init__(
        self,
        scan_interval_seconds: int = 30,
        idle_threshold_seconds: int = 3600, # Default 60 minutes
        rotation_step_degrees: int = 30,
        rotation_steps: int = 12,
        rotation_settle_time_seconds: int = 15,
        scan_callback: Optional[Callable[[int], None]] = None,
        rotate_callback: Optional[Callable[[int], None]] = None
    ):
        self._is_suspended = False
        self._suspended_by: Optional[str] = None
        self._suspended_at: Optional[float] = None
        self._suspend_duration: Optional[int] = None
        self._scan_interval = scan_interval_seconds
        
        # Idle Scan Settings
        self._idle_threshold = idle_threshold_seconds
        self._rotation_step = rotation_step_degrees
        self._rotation_steps = rotation_steps
        self._rotation_settle_time = rotation_settle_time_seconds
        self._last_activity_time = time.time()
        self._is_scanning = False
        
        # Callbacks for actions
        self._scan_callback = scan_callback
        self._rotate_callback = rotate_callback

        self._loop_task: Optional[asyncio.Task] = None
        self._running = False
        logger.info(
            f"MonitoringLoopService initialized (interval={scan_interval_seconds}s, idle={idle_threshold_seconds}s)"
        )

    def set_callbacks(self, scan_callback: Callable[[int], None], rotate_callback: Callable[[int], None]):
        """スキャン（撮影・分析）と回転のアクションを実行するコールバックを設定する。"""
        self._scan_callback = scan_callback
        self._rotate_callback = rotate_callback

    def update_activity(self):
        """アクティビティを更新し、アイドルタイマーをリセットする。"""
        self._last_activity_time = time.time()
        logger.debug("Activity updated. Idle timer reset.")

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
        """監視ループを一時停止する。"""
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
        """監視ループを再開する。"""
        was_suspended = self._is_suspended
        self._is_suspended = False
        suspended_by = self._suspended_by
        self._suspended_by = None
        self._suspended_at = None
        self._suspend_duration = None
        
        # Resume時にアクティビティも更新して即座にスキャンが走らないようにする
        self.update_activity()

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
            "idle_threshold": self._idle_threshold,
            "seconds_since_activity": time.time() - self._last_activity_time
        }

    async def start(self):
        """監視ループを開始する。"""
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("Monitoring loop started.")

    async def stop(self):
        """監視ループを停止する。"""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring loop stopped.")

    async def _run_loop(self):
        """メイン監視ループ。"""
        logger.info("Monitoring loop running...")
        while self._running:
            try:
                if not self.is_suspended and not self._is_scanning:
                    # Check for idle
                    idle_time = time.time() - self._last_activity_time
                    if idle_time >= self._idle_threshold:
                        logger.info(f"Idle threshold ({self._idle_threshold}s) reached. Starting periodic scan.")
                        await self._perform_periodic_scan()
                
                await asyncio.sleep(self._scan_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self._scan_interval)

    async def _perform_periodic_scan(self):
        """全方位スキャンを実行する。"""
        if not self._scan_callback or not self._rotate_callback:
            logger.warning("Callbacks not set. Skipping scan.")
            return

        self._is_scanning = True
        # Suspend monitoring during scan to prevent interference? 
        # Actually we are the monitoring loop, so we just block other logic.
        
        try:
            logger.info(f"Starting {self._rotation_steps}-step rotation scan.")
            for i in range(self._rotation_steps):
                if not self._running or self.is_suspended:
                     logger.info("Scan interrupted.")
                     break
                
                # Rotate
                angle = i * self._rotation_step
                logger.info(f"Scan step {i+1}/{self._rotation_steps}: Rotating to {angle}")
                self._rotate_callback(angle)
                
                # Wait for rotation to settle (arbitrary small delay)
                await asyncio.sleep(self._rotation_settle_time)
                
                # Scan/Analyze
                logger.info(f"Scan step {i+1}: Analyzing...")
                # We assume scan_callback handles the async nature or is fast enough
                # If it's blocking detection, we might want to run in executor, but let's keep simple.
                # Since callbacks might be sync, we wrap if needed, but for now direct call.
                # Actually detect_objects in monitor.py is sync (detect_objects -> Agent model call).
                # But we want to call the logic, not the tool string.
                # The callback should be `detect_objects` directly.
                
                # Check if callback is async pattern? The provided tools define sync functions.
                # We will assume sync execution for now or wrap in simple await if needed.
                try:
                    await asyncio.to_thread(self._scan_callback, angle) # Pass angle or some context if needed
                except Exception as e:
                    logger.error(f"Error during scan Step {i}: {e}")

                await asyncio.sleep(1)

            logger.info("Periodic scan completed.")
            
        finally:
            self._is_scanning = False
            self.update_activity() # Reset timer after scan


# グローバルシングルトンインスタンス
# Monitor Agent プロセス内で一つだけ存在する
_monitoring_service: Optional[MonitoringLoopService] = None


def get_monitoring_service() -> MonitoringLoopService:
    """MonitoringLoopService のシングルトンインスタンスを取得する。"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringLoopService()
    return _monitoring_service

