from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import AuthServiceDependency, CurrentUserDependency
from app.core.security import hash_refresh_token
from app.db.session import get_db_session
from app.domain.enums import CarCondition, StageStatus
from app.repositories.auth import AuthRepository
from app.repositories.stage_session import StageSessionRepository
from app.schemas.auth import WebSocketTicketRead
from app.services.live_manager import live_manager
from app.services.live_simulation import LiveRaceCarState, LiveRaceEngine, TrackSegmentSnapshot
from app.services.stage_session import StageSessionService
from app.services.tire_strategy import (
    TireStrategy,
    build_tire_strategies,
    recommended_starting_compound,
    weather_starting_compound,
)
from app.services.tires import TIRE_COMPOUNDS
from app.services.track_geometry import (
    TrackGeometryError,
    TrackGeometryProfile,
    build_track_geometry_profile,
)
from app.services.weather import (
    build_race_keyframes,
    build_weather_payload,
    climate_from_track,
)

router = APIRouter(prefix="/ws", tags=["live-race"])


@router.post("/ticket", response_model=WebSocketTicketRead)
def issue_websocket_ticket(
    user: CurrentUserDependency,
    service: AuthServiceDependency,
) -> WebSocketTicketRead:
    ticket, expires_in_seconds = service.issue_websocket_ticket(user)
    return WebSocketTicketRead(ticket=ticket, expires_in_seconds=expires_in_seconds)


@router.websocket("/seasons/{season_id}/stages/{stage_id}/race")
async def stream_live_race(
    websocket: WebSocket,
    season_id: UUID,
    stage_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> None:
    user_id = _consume_websocket_ticket(websocket, session)
    if user_id is None:
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # Check authorization and existence of stage
    season_data = StageSessionRepository(session).get_for_user(season_id, user_id)
    if season_data is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    stage = next((item for item in season_data.stages if item.id == stage_id), None)
    if stage is None or not stage.track.segments:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if stage.race_status == StageStatus.COMPLETED and live_manager.get_engine(stage_id) is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if stage.qualifying_status != StageStatus.COMPLETED:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if any(
        car.condition == CarCondition.HEAVILY_DAMAGED
        and car.team_id == season_data.selected_team_id
        for car in season_data.cars
    ):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    qualifying_results = StageSessionRepository(session).list_qualifying_results(stage_id)
    car_ids = {str(car.id) for car in season_data.cars}
    grid_map = {str(result.car_id): result.position for result in qualifying_results}
    if (
        not qualifying_results
        or not season_data.cars
        or len(qualifying_results) != len(season_data.cars)
        or set(grid_map) != car_ids
        or set(grid_map.values()) != set(range(1, len(season_data.cars) + 1))
    ):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Stage ownership and validity are now known. Reserve before constructing a
    # potentially expensive engine so duplicate handshakes cannot multiply it.
    if not live_manager.reserve_connection(user_id, stage_id, websocket):
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        return

    # Engine construction below is synchronous, but this final task callback is
    # a last-resort release guard for an unexpected exception before the normal
    # receive-loop ``finally`` is entered.
    current_task = asyncio.current_task()
    if current_task is not None:
        current_task.add_done_callback(
            lambda _: live_manager.disconnect(stage_id, user_id, websocket)
        )

    # Initialize engine ONLY if session doesn't exist yet
    if not live_manager.get_engine(stage_id):
        persistence_factory = sessionmaker(
            bind=session.get_bind(),
            autoflush=False,
            expire_on_commit=False,
        )

        def persist_completed_race(engine: LiveRaceEngine) -> None:
            with persistence_factory() as persistence_session:
                service = StageSessionService(StageSessionRepository(persistence_session))
                service.persist_completed_live_race(season_id, stage_id, user_id, engine)

        weather_manifest = stage.weather_scenario
        climate = weather_manifest.get("climate") or climate_from_track(stage.track)
        weather_seed = int(weather_manifest["seed"])
        weather_keyframes = build_race_keyframes(
            seed=weather_seed,
            climate=climate,
            scenario=weather_manifest.get("scenario"),
        )
        start_weather = weather_keyframes[0]
        weather_payload = build_weather_payload(weather_manifest)
        strategies = build_tire_strategies(stage.track, weather_payload)
        recommended_start = recommended_starting_compound(
            stage.track,
            weather_payload,
            strategies,
            weather_manifest,
        )
        weather_start = weather_starting_compound(
            stage.track,
            weather_payload,
            weather_manifest,
        )

        # Sort cars by the persisted qualifying grid.
        sorted_cars = sorted(
            season_data.cars,
            key=lambda c: grid_map[str(c.id)],
        )
        player_driver_ids = [str(driver.id) for driver in season_data.selected_drivers]
        assigned_strategies = _assign_bot_strategies(
            sorted_cars,
            grid_map,
            strategies,
            stage_seed=int(stage_id.int % 1000000),
            player_driver_ids=set(player_driver_ids),
        )

        engine = LiveRaceEngine(
            segments=[
                TrackSegmentSnapshot(
                    id=segment.id,
                    segment_index=segment.segment_index,
                    type=segment.type,
                    length_meters=segment.length_meters,
                    base_speed=segment.base_speed,
                    overtake_chance=segment.overtake_chance,
                )
                for segment in stage.track.segments
            ],
            cars=[
                LiveRaceCarState(
                    id=str(car.id),
                    driver_id=car.driver_id,
                    driver_code=car.driver.code,
                    pilot_name=car.driver.last_name,
                    driver_pace=car.driver.pace,
                    driver_stability=car.driver.stability,
                    team_id=car.team_id,
                    team_color=car.team.color,
                    current_segment_id=stage.track.segments[0].id,
                    engine_power=car.engine_power,
                    aero_efficiency=car.aero_efficiency,
                    chassis_grip=car.chassis_grip,
                    reliability=car.reliability,
                    condition=car.condition,
                    wings_setting=car.wings_setting,
                    suspension_setting=car.suspension_setting,
                    gearbox_setting=car.gearbox_setting,
                    confidence=float(car.confidence),
                    tire_compound=_starting_tire_for_car(
                        car,
                        player_driver_ids=set(player_driver_ids),
                        query_params=websocket.query_params,
                        assigned_strategy=assigned_strategies.get(str(car.id)),
                        weather_start=weather_start,
                        recommended_start=recommended_start,
                    ),
                    grid_position=grid_map[str(car.id)],
                    strategy_plan=(
                        assigned_strategies[str(car.id)].stints
                        if str(car.id) in assigned_strategies
                        else ()
                    ),
                )
                for car in sorted_cars
            ],
            track_length_meters=stage.track.track_length_meters,
            total_laps=stage.track.laps,
            player_driver_ids=player_driver_ids,
            initial_track_temp=float(start_weather["trackTemp"]),
            initial_track_wetness=float(start_weather["trackWetness"]),
            weather_keyframes=weather_keyframes,
            climate=climate,
            weather_seed=weather_seed,
            track_geometry=_build_track_geometry(
                stage.track.svg_path,
                float(stage.track.track_length_meters),
            ),
            seed=int(stage_id.int % 1000000),
        )
        live_manager.get_or_create_session(
            stage_id,
            engine,
            persist_callback=persist_completed_race,
        )

    try:
        # Join manager (connection already accepted). A reservation mismatch is
        # treated as a transient server condition and never receives a snapshot.
        if not live_manager.connect(stage_id, user_id, websocket):
            await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
            return

        # Send current state snapshot immediately
        snapshot = live_manager.get_snapshot(stage_id)
        if snapshot is None:
            return
        await websocket.send_json(snapshot)

        # Keep connection open and listen for commands
        while True:
            data = await websocket.receive_json()
            # Command format: {"action": "BOX_THIS_LAP", "carId": "...", "target_tires": "Soft"}
            action = data.pop("action", None)
            car_id = data.pop("carId", None)
            if action:
                live_manager.process_command(stage_id, car_id, action, **data)
    except WebSocketDisconnect:
        pass
    finally:
        live_manager.disconnect(stage_id, user_id, websocket)


def _consume_websocket_ticket(websocket: WebSocket, session: Session) -> UUID | None:
    """Consume only `ticket`; legacy access-token query authentication is unsupported."""
    ticket = websocket.query_params.get("ticket")
    if not ticket:
        return None
    try:
        now = datetime.now(UTC)
        repository = AuthRepository(session)
        user_id = repository.consume_websocket_ticket(hash_refresh_token(ticket), now)
        if user_id is None:
            session.rollback()
            return None
        repository.cleanup_expired_websocket_tickets(now)
        session.commit()
        return user_id
    except Exception:
        session.rollback()
        return None


def _build_track_geometry(
    svg_path: str,
    track_length_meters: float,
) -> TrackGeometryProfile | None:
    try:
        return build_track_geometry_profile(
            svg_path,
            track_length_meters=track_length_meters,
        )
    except TrackGeometryError:
        return None


def _assign_bot_strategies(
    cars,
    grid_map: dict,
    strategies: list[TireStrategy] | None,
    *,
    stage_seed: int,
    player_driver_ids: set[str],
) -> dict[str, TireStrategy]:
    if not strategies:
        return {}

    by_team = defaultdict(list)
    for car in cars:
        if car.driver_id not in player_driver_ids:
            by_team[car.team_id].append(car)

    assignments: dict[str, TireStrategy] = {}
    for team_id in sorted(by_team):
        teammates = sorted(
            by_team[team_id],
            key=lambda car: grid_map[str(car.id)],
        )
        assignments[str(teammates[0].id)] = strategies[0]
        if len(teammates) < 2:
            continue
        alternative_count = min(2, len(strategies) - 1)
        if alternative_count <= 0:
            assignments[str(teammates[1].id)] = strategies[0]
            continue
        digest = sha256(f"{stage_seed}:{team_id}".encode()).digest()
        alternative_index = 1 + int.from_bytes(digest[:4], "big") % alternative_count
        assignments[str(teammates[1].id)] = strategies[alternative_index]
        for extra_car in teammates[2:]:
            assignments[str(extra_car.id)] = strategies[0]
    return assignments


def _starting_tire_for_car(
    car,
    *,
    player_driver_ids: set[str],
    query_params,
    assigned_strategy: TireStrategy | None,
    weather_start: str | None,
    recommended_start: str | None,
) -> str:
    fallback = (
        weather_start
        or (assigned_strategy.stints[0].compound if assigned_strategy is not None else None)
        or recommended_start
        or "Medium"
    )
    if car.driver_id not in player_driver_ids:
        return fallback
    requested = query_params.get(f"tire_{car.driver_id}")
    return requested if requested in TIRE_COMPOUNDS else fallback
