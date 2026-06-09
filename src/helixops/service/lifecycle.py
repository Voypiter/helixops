"""Graceful shutdown and deployment lifecycle management."""

import asyncio
import signal
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ShutdownEvent:
    """Shutdown event record."""

    timestamp: datetime
    signal_name: str
    reason: str
    graceful: bool
    active_runs: int


class LifecycleManager:
    """Manages runtime lifecycle including graceful shutdown."""

    def __init__(self) -> None:
        """Initialize lifecycle manager."""
        self.is_shutting_down = False
        self.shutdown_timeout_seconds = 30
        self.active_runs = 0
        self.active_requests = 0
        self.shutdown_callbacks: list[Callable[..., Any]] = []
        self.startup_callbacks: list[Callable[..., Any]] = []
        self.shutdown_events: list[ShutdownEvent] = []

    def register_shutdown_callback(self, callback: Callable[..., Any]) -> None:
        """Register callback to execute on shutdown.

        Args:
            callback: Async or sync function to call
        """
        self.shutdown_callbacks.append(callback)

    def register_startup_callback(self, callback: Callable[..., Any]) -> None:
        """Register callback to execute on startup.

        Args:
            callback: Async or sync function to call
        """
        self.startup_callbacks.append(callback)

    async def startup(self) -> None:
        """Execute startup sequence."""
        for callback in self.startup_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()

    async def shutdown(self, signal_name: str = "TERM", graceful: bool = True) -> None:
        """Execute graceful shutdown sequence.

        Args:
            signal_name: Signal that triggered shutdown
            graceful: Whether to wait for active work
        """
        if self.is_shutting_down:
            return

        self.is_shutting_down = True

        event = ShutdownEvent(
            timestamp=datetime.utcnow(),
            signal_name=signal_name,
            reason="graceful" if graceful else "forced",
            graceful=graceful,
            active_runs=self.active_runs,
        )
        self.shutdown_events.append(event)

        if graceful:
            await self._graceful_shutdown()
        else:
            await self._forced_shutdown()

    async def _graceful_shutdown(self) -> None:
        """Graceful shutdown: wait for active work."""
        start_time = asyncio.get_event_loop().time()

        while self.active_runs > 0:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.shutdown_timeout_seconds:
                break
            await asyncio.sleep(0.1)

        await self._execute_shutdown_callbacks()

    async def _forced_shutdown(self) -> None:
        """Forced shutdown: interrupt active work."""
        self.active_runs = 0
        self.active_request = 0
        await self._execute_shutdown_callbacks()

    async def _execute_shutdown_callbacks(self) -> None:
        """Execute registered shutdown callbacks."""
        for callback in self.shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception:
                pass  # Callbacks must not raise

    def increment_active_run(self) -> None:
        """Increment active run counter."""
        if not self.is_shutting_down:
            self.active_runs += 1

    def decrement_active_run(self) -> None:
        """Decrement active run counter."""
        self.active_runs = max(0, self.active_runs - 1)

    def increment_active_request(self) -> None:
        """Increment active request counter."""
        if not self.is_shutting_down:
            self.active_requests += 1

    def decrement_active_request(self) -> None:
        """Decrement active request counter."""
        self.active_requests = max(0, self.active_requests - 1)

    def get_shutdown_status(self) -> dict[str, Any]:
        """Get current shutdown status.

        Returns:
            Status dictionary
        """
        return {
            "is_shutting_down": self.is_shutting_down,
            "active_runs": self.active_runs,
            "active_requests": self.active_requests,
            "shutdown_events": len(self.shutdown_events),
        }


# Global lifecycle manager
_lifecycle_manager: LifecycleManager | None = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get the global lifecycle manager.

    Returns:
        LifecycleManager instance
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


def register_signal_handlers(manager: LifecycleManager) -> None:
    """Register OS signal handlers for graceful shutdown.

    Args:
        manager: LifecycleManager instance
    """

    def handle_sigterm(signum: int, frame: Any) -> None:
        asyncio.create_task(manager.shutdown("TERM", graceful=True))

    def handle_sigint(signum: int, frame: Any) -> None:
        asyncio.create_task(manager.shutdown("INT", graceful=True))

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigint)
