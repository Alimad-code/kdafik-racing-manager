import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.services.live_simulation import LiveRaceEngine
from app.services.text_content import build_radio_message, radio_situation

logger = logging.getLogger(__name__)

IMPORTANT_TRIGGER_TYPES = {"TECHNICAL_ISSUE", "INCIDENT"}
TRIGGER_PRIORITY = {
    "TECHNICAL_ISSUE": 0,
    "INCIDENT": 1,
    "CLIFF_REACHED": 2,
    "RAIN_ON_SLICKS": 3,
    "TIRE_RULE_WARNING": 4,
}


class LiveRaceSession:
    def __init__(
        self,
        stage_id: UUID,
        engine: LiveRaceEngine,
        monotonic_now: Any = time.monotonic,
        persist_callback: Callable[[LiveRaceEngine], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        on_websocket_failure: Callable[[WebSocket], None] | None = None,
        post_finish_grace_seconds: float = 30.0,
    ):
        self.stage_id = stage_id
        self.engine = engine
        self.websockets: set[WebSocket] = set()
        self._task: asyncio.Task | None = None
        self._last_processed_tick = -1
        self._speed_multiplier = 1.0
        self._monotonic_now = monotonic_now
        self._last_leader_gap_cue_at = self._monotonic_now()
        self._timing_cue_sequence = 1
        self._radio_variant_counts: dict[tuple[str, str], int] = {}
        self._persist_callback = persist_callback
        self._persisting = False
        self._persisted = False
        self._persisted_at: float | None = None
        self._on_finished = on_finished
        self._on_websocket_failure = on_websocket_failure
        self._post_finish_grace_seconds = max(0.0, post_finish_grace_seconds)

    def set_speed(self, multiplier: float) -> None:
        self._speed_multiplier = max(0.1, min(10.0, multiplier))
        logger.info(f"Speed for stage {self.stage_id} set to {self._speed_multiplier}x")

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
            logger.info(f"Started live race background task for stage {self.stage_id}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self.websockets:
            return

        for ws in list(self.websockets):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send update to websocket: {e}")
                self.websockets.discard(ws)
                if self._on_websocket_failure is not None:
                    self._on_websocket_failure(ws)

    async def _run_loop(self) -> None:
        try:
            while True:
                # Calculate sleep based on speed multiplier.
                # If speed is 2x, we sleep 0.5s instead of 1.0s.
                sleep_time = 1.0 / self._speed_multiplier
                await asyncio.sleep(sleep_time)

                update = self.engine.tick()

                triggers = update.pop("triggers", [])
                update["notification"] = self._notification_from_triggers(triggers)
                self._append_wall_timing_cue(update)
                self._decorate_update(update)

                await self.broadcast(update)
                self._persist_if_complete()
                if self._grace_period_expired():
                    if self._on_finished is not None:
                        self._on_finished()
                    return
        except asyncio.CancelledError:
            logger.info(f"Live race task for stage {self.stage_id} cancelled.")
        except Exception as e:
            logger.error(f"Error in live race loop for stage {self.stage_id}: {e}", exc_info=True)

    def _persist_if_complete(self) -> None:
        if self._persist_callback is None or self._persisting or self._persisted:
            return
        if not self.engine.is_complete():
            return

        self._persisting = True
        try:
            self._persist_callback(self.engine)
            self._persisted = True
            self._persisted_at = self._monotonic_now()
        except Exception:
            logger.error(f"Failed to persist live race for stage {self.stage_id}", exc_info=True)
        finally:
            self._persisting = False

    def _grace_period_expired(self) -> bool:
        return (
            self._persisted_at is not None
            and self._monotonic_now() - self._persisted_at >= self._post_finish_grace_seconds
        )

    def _append_wall_timing_cue(self, update: dict[str, Any]) -> None:
        now = self._monotonic_now()
        if now - self._last_leader_gap_cue_at < 30.0:
            return
        self._last_leader_gap_cue_at = now
        update.setdefault("timingCues", []).append(
            {
                "id": f"leader-gaps-{self._timing_cue_sequence}",
                "type": "SHOW_LEADER_GAPS",
                "durationMs": 5000,
            }
        )
        self._timing_cue_sequence += 1

    def _decorate_update(self, update: dict[str, Any]) -> None:
        update["gameTimeRate"] = self.engine.tick_game_seconds * self._speed_multiplier

    def snapshot(self) -> dict[str, Any]:
        payload = self.engine.snapshot()
        self._decorate_update(payload)
        return payload

    def _notification_from_triggers(self, triggers: list[dict[str, Any]]) -> dict[str, Any] | None:
        eligible = []
        player_driver_ids = set(self.engine.player_driver_ids)
        for trigger in triggers:
            car = next((item for item in self.engine.cars if item.id == trigger["carId"]), None)
            if car is None:
                continue

            is_player = car.driver_id in player_driver_ids
            is_important = trigger["type"] in IMPORTANT_TRIGGER_TYPES and (
                trigger["type"] == "TECHNICAL_ISSUE"
                or car.status == "DNF"
                or "Серьёзная" in str(trigger.get("trigger", ""))
            )
            if not is_player and not is_important:
                continue

            eligible.append(
                (
                    0 if is_player else 1,
                    TRIGGER_PRIORITY.get(trigger["type"], 99),
                    trigger,
                    car,
                )
            )

        if not eligible:
            return None

        _, _, trigger, car = sorted(eligible, key=lambda item: (item[0], item[1]))[0]
        situation = radio_situation(trigger["type"], trigger.get("trigger"))
        counter_key = (car.id, situation)
        occurrence_index = self._radio_variant_counts.get(counter_key, 0)
        message = build_radio_message(
            trigger_type=trigger["type"],
            trigger_detail=trigger.get("trigger"),
            driver_id=car.driver_id,
            pace=car.driver_pace,
            stability=car.driver_stability,
            occurrence_index=occurrence_index,
        )
        self._radio_variant_counts[counter_key] = occurrence_index + 1
        if trigger["type"] == "TIRE_RULE_WARNING":
            car.tire_rule_warning_sent = True
        return {
            "carId": car.id,
            "driverId": car.driver_id,
            "pilotName": car.pilot_name,
            "teamId": car.team_id,
            "teamColor": car.team_color,
            "type": trigger["type"],
            "message": message,
            "trigger": trigger.get("trigger"),
            "isPlayerDriver": car.driver_id in self.engine.player_driver_ids,
        }

    def stop(self) -> None:
        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            current_task = None
        if self._task and self._task is not current_task:
            self._task.cancel()


class LiveSimulationManager:
    def __init__(self, post_finish_grace_seconds: float = 30.0) -> None:
        self._sessions: dict[UUID, LiveRaceSession] = {}
        # This is intentionally process-local.  It is an admission control for a
        # live race, not an account/session record and must never be persisted.
        self._active_connections: dict[tuple[UUID, UUID], WebSocket] = {}
        self.post_finish_grace_seconds = max(0.0, post_finish_grace_seconds)

    def get_or_create_session(
        self,
        stage_id: UUID,
        engine: LiveRaceEngine,
        persist_callback: Callable[[LiveRaceEngine], None] | None = None,
        post_finish_grace_seconds: float | None = None,
    ) -> LiveRaceSession:
        if stage_id not in self._sessions:
            session: LiveRaceSession

            def cleanup() -> None:
                self._cleanup_session(stage_id, session)

            def release_failed_websocket(websocket: WebSocket) -> None:
                self._release_websocket_reservation(stage_id, websocket)

            session = LiveRaceSession(
                stage_id,
                engine,
                persist_callback=persist_callback,
                on_finished=cleanup,
                on_websocket_failure=release_failed_websocket,
                post_finish_grace_seconds=(
                    self.post_finish_grace_seconds
                    if post_finish_grace_seconds is None
                    else post_finish_grace_seconds
                ),
            )
            self._sessions[stage_id] = session
        return self._sessions[stage_id]

    def reserve_connection(self, user_id: UUID, stage_id: UUID, websocket: WebSocket) -> bool:
        """Atomically reserve the one live socket allowed for a user and stage.

        This method deliberately has no ``await``.  Calls from the ASGI event
        loop therefore cannot interleave between checking and inserting the
        reservation.
        """
        key = (user_id, stage_id)
        if key in self._active_connections:
            return False
        self._active_connections[key] = websocket
        return True

    def connect(self, stage_id: UUID, user_id: UUID, websocket: WebSocket) -> bool:
        """Attach a previously reserved socket to its live-race session."""
        if self._active_connections.get((user_id, stage_id)) is not websocket:
            return False
        session = self._sessions.get(stage_id)
        if session is None:
            return False
        session.websockets.add(websocket)
        session.start()
        return True

    def disconnect(self, stage_id: UUID, user_id: UUID, websocket: WebSocket) -> None:
        """Detach a socket without releasing a newer connection's reservation."""
        session = self._sessions.get(stage_id)
        if session:
            session.websockets.discard(websocket)
        key = (user_id, stage_id)
        if self._active_connections.get(key) is websocket:
            self._active_connections.pop(key, None)

    def _release_websocket_reservation(self, stage_id: UUID, websocket: WebSocket) -> None:
        """Release the reservation belonging to a failed broadcast socket."""
        for key, reserved_websocket in tuple(self._active_connections.items()):
            if key[1] == stage_id and reserved_websocket is websocket:
                self._active_connections.pop(key, None)
                return

    def process_command(
        self,
        stage_id: UUID,
        car_id: str | None,
        action: str,
        **kwargs: Any,
    ) -> None:
        session = self._sessions.get(stage_id)
        if not session:
            return

        if action == "SET_SPEED":
            multiplier = kwargs.get("multiplier", 1.0)
            session.set_speed(float(multiplier))
        elif car_id:
            session.engine.process_command(car_id, action, **kwargs)

    def get_engine(self, stage_id: UUID) -> LiveRaceEngine | None:
        session = self._sessions.get(stage_id)
        return session.engine if session else None

    def get_snapshot(self, stage_id: UUID) -> dict[str, Any] | None:
        session = self._sessions.get(stage_id)
        return session.snapshot() if session else None

    def stop_session(self, stage_id: UUID) -> None:
        session = self._sessions.pop(stage_id, None)
        if session:
            session.stop()

    def _cleanup_session(self, stage_id: UUID, session: LiveRaceSession) -> None:
        if self._sessions.get(stage_id) is not session:
            return
        self._sessions.pop(stage_id, None)
        session.stop()


# Global singleton for the application
live_manager = LiveSimulationManager()
