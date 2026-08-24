from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import Driver, SeasonStage, Team, Track, TrackSegment
from app.services.track_geometry import (
    average_raw_svg_length,
    build_track_geometry_profile,
    build_track_geometry_segments,
    derived_laps_for_race,
    normalized_track_length_meters,
    predicted_lap_seconds,
    raw_svg_path_length,
)

DRIVERS: list[dict[str, Any]] = [
    {
        "id": "driver-novak",
        "number": 7,
        "first_name": "Милан",
        "last_name": "Новак",
        "code": "НОВ",
        "nationality": "Чех",
        "price_millions": Decimal("28.00"),
        "pace": 87,
        "stability": 78,
        "is_active": True,
    },
    {
        "id": "driver-moreau",
        "number": 12,
        "first_name": "Лео",
        "last_name": "Моро",
        "code": "МОР",
        "nationality": "Француз",
        "price_millions": Decimal("24.00"),
        "pace": 82,
        "stability": 84,
        "is_active": True,
    },
    {
        "id": "driver-sato",
        "number": 18,
        "first_name": "Рэн",
        "last_name": "Сато",
        "code": "САТ",
        "nationality": "Японец",
        "price_millions": Decimal("20.00"),
        "pace": 76,
        "stability": 88,
        "is_active": True,
    },
    {
        "id": "driver-silva",
        "number": 21,
        "first_name": "Матео",
        "last_name": "Силва",
        "code": "СИЛ",
        "nationality": "Бразилец",
        "price_millions": Decimal("18.00"),
        "pace": 80,
        "stability": 69,
        "is_active": True,
    },
    {
        "id": "driver-keller",
        "number": 31,
        "first_name": "Йонас",
        "last_name": "Келлер",
        "code": "КЕЛ",
        "nationality": "Немец",
        "price_millions": Decimal("16.00"),
        "pace": 72,
        "stability": 82,
        "is_active": True,
    },
    {
        "id": "driver-petrov",
        "number": 44,
        "first_name": "Алексей",
        "last_name": "Петров",
        "code": "ПЕТ",
        "nationality": "Болгарин",
        "price_millions": Decimal("14.00"),
        "pace": 70,
        "stability": 75,
        "is_active": True,
    },
    {
        "id": "driver-jones",
        "number": 55,
        "first_name": "Оливер",
        "last_name": "Джонс",
        "code": "ДЖО",
        "nationality": "Британец",
        "price_millions": Decimal("15.00"),
        "pace": 74,
        "stability": 77,
        "is_active": True,
    },
    {
        "id": "driver-kim",
        "number": 88,
        "first_name": "Мин-джун",
        "last_name": "Ким",
        "code": "КИМ",
        "nationality": "Южнокореец",
        "price_millions": Decimal("22.00"),
        "pace": 81,
        "stability": 80,
        "is_active": True,
    },
    {
        "id": "driver-rossi",
        "number": 11,
        "first_name": "Лукас",
        "last_name": "Росси",
        "code": "РОС",
        "nationality": "Итальянец",
        "price_millions": Decimal("19.00"),
        "pace": 78,
        "stability": 81,
        "is_active": True,
    },
    {
        "id": "driver-martinez",
        "number": 14,
        "first_name": "Диего",
        "last_name": "Мартинес",
        "code": "МАР",
        "nationality": "Испанец",
        "price_millions": Decimal("21.00"),
        "pace": 79,
        "stability": 83,
        "is_active": True,
    },
    {
        "id": "driver-eriksen",
        "number": 22,
        "first_name": "Ларс",
        "last_name": "Эриксен",
        "code": "ЭРИ",
        "nationality": "Швед",
        "price_millions": Decimal("17.00"),
        "pace": 75,
        "stability": 79,
        "is_active": True,
    },
    {
        "id": "driver-mendez",
        "number": 33,
        "first_name": "Карлос",
        "last_name": "Мендес",
        "code": "МЕН",
        "nationality": "Мексиканец",
        "price_millions": Decimal("25.00"),
        "pace": 85,
        "stability": 75,
        "is_active": True,
    },
    {
        "id": "driver-chen",
        "number": 41,
        "first_name": "Вэй",
        "last_name": "Чэнь",
        "code": "ЧЕН",
        "nationality": "Китаец",
        "price_millions": Decimal("15.00"),
        "pace": 73,
        "stability": 76,
        "is_active": True,
    },
    {
        "id": "driver-williams",
        "number": 47,
        "first_name": "Итан",
        "last_name": "Уильямс",
        "code": "УИЛ",
        "nationality": "Австралиец",
        "price_millions": Decimal("23.00"),
        "pace": 83,
        "stability": 82,
        "is_active": True,
    },
    {
        "id": "driver-smith",
        "number": 63,
        "first_name": "Ноа",
        "last_name": "Смит",
        "code": "СМИ",
        "nationality": "Американец",
        "price_millions": Decimal("16.00"),
        "pace": 74,
        "stability": 80,
        "is_active": True,
    },
    {
        "id": "driver-jansen",
        "number": 72,
        "first_name": "Элиас",
        "last_name": "Янсен",
        "code": "ЯНС",
        "nationality": "Нидерландец",
        "price_millions": Decimal("26.00"),
        "pace": 86,
        "stability": 79,
        "is_active": True,
    },
    {
        "id": "driver-muller",
        "number": 77,
        "first_name": "Феликс",
        "last_name": "Мюллер",
        "code": "МЮЛ",
        "nationality": "Швейцарец",
        "price_millions": Decimal("20.00"),
        "pace": 77,
        "stability": 85,
        "is_active": True,
    },
    {
        "id": "driver-clarke",
        "number": 81,
        "first_name": "Эйден",
        "last_name": "Кларк",
        "code": "КЛА",
        "nationality": "Канадец",
        "price_millions": Decimal("18.00"),
        "pace": 76,
        "stability": 80,
        "is_active": True,
    },
    {
        "id": "driver-davis",
        "number": 92,
        "first_name": "Лиам",
        "last_name": "Дэвис",
        "code": "ДЭВ",
        "nationality": "Новозеландец",
        "price_millions": Decimal("19.00"),
        "pace": 80,
        "stability": 74,
        "is_active": True,
    },
    {
        "id": "driver-hassan",
        "number": 99,
        "first_name": "Омар",
        "last_name": "Хассан",
        "code": "ХАС",
        "nationality": "Египтянин",
        "price_millions": Decimal("17.00"),
        "pace": 75,
        "stability": 82,
        "is_active": True,
    },
]

TEAMS: list[dict[str, Any]] = [
    {
        "id": "team-apex",
        "name": "Эйпекс Рейсинг",
        "short_name": "Эйпекс",
        "base_country": "Великобритания",
        "power_unit": "Эйпекс V6 Гибрид",
        "color": "#D91E36",
        "price_millions": Decimal("42.00"),
        "engine_power": 92,
        "aero_efficiency": 88,
        "chassis_grip": 84,
        "reliability": 79,
        "setup_cost_millions": Decimal("0.25"),
        "repair_cost_millions": Decimal("6.00"),
        "car_build_cost_millions": Decimal("10.00"),
        "is_active": True,
    },
    {
        "id": "team-velocity",
        "name": "Велосити Рейсинг",
        "short_name": "Велосити",
        "base_country": "Италия",
        "power_unit": "Велоче Гибрид",
        "color": "#F3C623",
        "price_millions": Decimal("34.00"),
        "engine_power": 82,
        "aero_efficiency": 82,
        "chassis_grip": 82,
        "reliability": 84,
        "setup_cost_millions": Decimal("0.20"),
        "repair_cost_millions": Decimal("5.00"),
        "car_build_cost_millions": Decimal("9.00"),
        "is_active": True,
    },
    {
        "id": "team-nordline",
        "name": "Нордлайн Моторспорт",
        "short_name": "Нордлайн",
        "base_country": "Германия",
        "power_unit": "Нордлайн E-Турбо",
        "color": "#2F80ED",
        "price_millions": Decimal("27.00"),
        "engine_power": 75,
        "aero_efficiency": 78,
        "chassis_grip": 85,
        "reliability": 88,
        "setup_cost_millions": Decimal("0.15"),
        "repair_cost_millions": Decimal("4.00"),
        "car_build_cost_millions": Decimal("8.00"),
        "is_active": True,
    },
    {
        "id": "team-orion",
        "name": "Орион Уоркс",
        "short_name": "Орион",
        "base_country": "Франция",
        "power_unit": "Орион Пульс",
        "color": "#27AE60",
        "price_millions": Decimal("22.00"),
        "engine_power": 70,
        "aero_efficiency": 72,
        "chassis_grip": 74,
        "reliability": 80,
        "setup_cost_millions": Decimal("0.13"),
        "repair_cost_millions": Decimal("3.50"),
        "car_build_cost_millions": Decimal("7.00"),
        "is_active": True,
    },
    {
        "id": "team-titan",
        "name": "Титан Моторспорт",
        "short_name": "Титан",
        "base_country": "США",
        "power_unit": "Титан Форс",
        "color": "#111111",
        "price_millions": Decimal("38.00"),
        "engine_power": 88,
        "aero_efficiency": 82,
        "chassis_grip": 78,
        "reliability": 75,
        "setup_cost_millions": Decimal("0.23"),
        "repair_cost_millions": Decimal("5.50"),
        "car_build_cost_millions": Decimal("9.50"),
        "is_active": True,
    },
    {
        "id": "team-vector",
        "name": "Вектор Моторспорт",
        "short_name": "Вектор",
        "base_country": "Россия",
        "power_unit": "Вектор Турбо",
        "color": "#E83E8C",
        "price_millions": Decimal("30.00"),
        "engine_power": 79,
        "aero_efficiency": 84,
        "chassis_grip": 81,
        "reliability": 82,
        "setup_cost_millions": Decimal("0.18"),
        "repair_cost_millions": Decimal("4.50"),
        "car_build_cost_millions": Decimal("8.50"),
        "is_active": True,
    },
    {
        "id": "team-quantum",
        "name": "Квантум Рейсинг",
        "short_name": "Квантум",
        "base_country": "Япония",
        "power_unit": "Квантум V6",
        "color": "#9B51E0",
        "price_millions": Decimal("25.00"),
        "engine_power": 72,
        "aero_efficiency": 75,
        "chassis_grip": 88,
        "reliability": 86,
        "setup_cost_millions": Decimal("0.14"),
        "repair_cost_millions": Decimal("3.80"),
        "car_build_cost_millions": Decimal("7.50"),
        "is_active": True,
    },
    {
        "id": "team-zenith",
        "name": "Зенит Рейсинг",
        "short_name": "Зенит",
        "base_country": "Бразилия",
        "power_unit": "Зенит Форс",
        "color": "#F2994A",
        "price_millions": Decimal("28.00"),
        "engine_power": 80,
        "aero_efficiency": 78,
        "chassis_grip": 76,
        "reliability": 81,
        "setup_cost_millions": Decimal("0.16"),
        "repair_cost_millions": Decimal("4.20"),
        "car_build_cost_millions": Decimal("8.00"),
        "is_active": True,
    },
    {
        "id": "team-eclipse",
        "name": "Эклипс Моторспорт",
        "short_name": "Эклипс",
        "base_country": "Австралия",
        "power_unit": "Эклипс Драйв",
        "color": "#56CCF2",
        "price_millions": Decimal("32.00"),
        "engine_power": 84,
        "aero_efficiency": 80,
        "chassis_grip": 79,
        "reliability": 80,
        "setup_cost_millions": Decimal("0.18"),
        "repair_cost_millions": Decimal("4.80"),
        "car_build_cost_millions": Decimal("8.80"),
        "is_active": True,
    },
    {
        "id": "team-nebula",
        "name": "Небьюла Уоркс",
        "short_name": "Небьюла",
        "base_country": "Канада",
        "power_unit": "Небьюла Кор",
        "color": "#00C9A7",
        "price_millions": Decimal("24.00"),
        "engine_power": 70,
        "aero_efficiency": 75,
        "chassis_grip": 82,
        "reliability": 85,
        "setup_cost_millions": Decimal("0.13"),
        "repair_cost_millions": Decimal("3.60"),
        "car_build_cost_millions": Decimal("7.20"),
        "is_active": True,
    },
]

TRACKS: list[dict[str, Any]] = [
    {
        "id": "track-sakhir",
        "name": "Пустынное кольцо",
        "country": "Бахрейн",
        "rain_probability": Decimal("0.08"),
        "track_temperature_min_c": Decimal("32"),
        "track_temperature_max_c": Decimal("48"),
        "variability": Decimal("0.25"),
    },
    {
        "id": "track-imola",
        "name": "Холмистая трасса",
        "country": "Италия",
        "rain_probability": Decimal("0.35"),
        "track_temperature_min_c": Decimal("20"),
        "track_temperature_max_c": Decimal("36"),
        "variability": Decimal("0.55"),
    },
    {
        "id": "track-silverstone",
        "name": "Северное кольцо",
        "country": "Великобритания",
        "rain_probability": Decimal("0.48"),
        "track_temperature_min_c": Decimal("16"),
        "track_temperature_max_c": Decimal("30"),
        "variability": Decimal("0.75"),
    },
    {
        "id": "track-suzuka",
        "name": "Тихоокеанская восьмёрка",
        "country": "Япония",
        "rain_probability": Decimal("0.55"),
        "track_temperature_min_c": Decimal("22"),
        "track_temperature_max_c": Decimal("38"),
        "variability": Decimal("0.70"),
    },
    {
        "id": "track-monza",
        "name": "Королевский автодром",
        "country": "Италия",
        "rain_probability": Decimal("0.28"),
        "track_temperature_min_c": Decimal("22"),
        "track_temperature_max_c": Decimal("40"),
        "variability": Decimal("0.45"),
    },
    {
        "id": "track-monaco",
        "name": "Лазурная городская трасса",
        "country": "Монако",
        "rain_probability": Decimal("0.25"),
        "track_temperature_min_c": Decimal("22"),
        "track_temperature_max_c": Decimal("38"),
        "variability": Decimal("0.35"),
    },
    {
        "id": "track-spa",
        "name": "Лесное кольцо",
        "country": "Бельгия",
        "rain_probability": Decimal("0.62"),
        "track_temperature_min_c": Decimal("14"),
        "track_temperature_max_c": Decimal("28"),
        "variability": Decimal("0.85"),
    },
    {
        "id": "track-zandvoort",
        "name": "Дюнный парк",
        "country": "Нидерланды",
        "rain_probability": Decimal("0.45"),
        "track_temperature_min_c": Decimal("16"),
        "track_temperature_max_c": Decimal("30"),
        "variability": Decimal("0.75"),
    },
    {
        "id": "track-austin",
        "name": "Техасское кольцо",
        "country": "США",
        "rain_probability": Decimal("0.25"),
        "track_temperature_min_c": Decimal("26"),
        "track_temperature_max_c": Decimal("44"),
        "variability": Decimal("0.55"),
    },
    {
        "id": "track-interlagos",
        "name": "Озёрная трасса",
        "country": "Бразилия",
        "rain_probability": Decimal("0.52"),
        "track_temperature_min_c": Decimal("22"),
        "track_temperature_max_c": Decimal("42"),
        "variability": Decimal("0.80"),
    },
    {
        "id": "track-vegas",
        "name": "Неоновая городская трасса",
        "country": "США",
        "rain_probability": Decimal("0.05"),
        "track_temperature_min_c": Decimal("18"),
        "track_temperature_max_c": Decimal("38"),
        "variability": Decimal("0.25"),
    },
    {
        "id": "track-abudhabi",
        "name": "Прибрежная трасса",
        "country": "ОАЭ",
        "rain_probability": Decimal("0.03"),
        "track_temperature_min_c": Decimal("30"),
        "track_temperature_max_c": Decimal("48"),
        "variability": Decimal("0.15"),
    },
]

MVP_CALENDAR: list[dict[str, Any]] = [
    {
        "stage_number": 1,
        "track_id": "track-sakhir",
        "weekend_date": date(2026, 3, 1),
    },
    {
        "stage_number": 2,
        "track_id": "track-imola",
        "weekend_date": date(2026, 3, 15),
    },
    {
        "stage_number": 3,
        "track_id": "track-monaco",
        "weekend_date": date(2026, 4, 5),
    },
    {
        "stage_number": 4,
        "track_id": "track-silverstone",
        "weekend_date": date(2026, 4, 19),
    },
    {
        "stage_number": 5,
        "track_id": "track-zandvoort",
        "weekend_date": date(2026, 5, 3),
    },
    {
        "stage_number": 6,
        "track_id": "track-spa",
        "weekend_date": date(2026, 5, 17),
    },
    {
        "stage_number": 7,
        "track_id": "track-monza",
        "weekend_date": date(2026, 6, 7),
    },
    {
        "stage_number": 8,
        "track_id": "track-suzuka",
        "weekend_date": date(2026, 6, 21),
    },
    {
        "stage_number": 9,
        "track_id": "track-austin",
        "weekend_date": date(2026, 7, 12),
    },
    {
        "stage_number": 10,
        "track_id": "track-vegas",
        "weekend_date": date(2026, 7, 26),
    },
    {
        "stage_number": 11,
        "track_id": "track-interlagos",
        "weekend_date": date(2026, 8, 9),
    },
    {
        "stage_number": 12,
        "track_id": "track-abudhabi",
        "weekend_date": date(2026, 8, 23),
    },
]


@dataclass(frozen=True)
class SeedSummary:
    drivers: int
    teams: int
    tracks: int
    calendar_stages: int


def seed_mvp_catalog(session: Session) -> SeedSummary:
    validate_mvp_seed_data()

    for driver in DRIVERS:
        session.merge(Driver(**driver))
    for team in TEAMS:
        session.merge(Team(**team))
    for track in TRACKS:
        track_payload = dict(track)
        track_payload["svg_path"] = svg_path_for_track(track)
        track_payload["track_length_meters"] = track_length_meters(track)
        track_payload["length_km"] = (
            track_payload["track_length_meters"] / Decimal("1000")
        ).quantize(Decimal("0.001"))
        track_payload["laps"] = track_laps(track)
        merged_track = session.get(Track, track["id"])
        if merged_track is None:
            merged_track = Track(**track_payload)
            session.add(merged_track)
        else:
            for key, value in track_payload.items():
                setattr(merged_track, key, value)
            if merged_track.segments:
                merged_track.segments.clear()
                session.flush()
        merged_track.segments = [
            TrackSegment(**segment) for segment in track_segments_for_track(track)
        ]

    update_existing_season_stages(session)

    return SeedSummary(
        drivers=len(DRIVERS),
        teams=len(TEAMS),
        tracks=len(TRACKS),
        calendar_stages=len(MVP_CALENDAR),
    )


def validate_mvp_seed_data() -> None:
    for entity_name, rows in (
        ("drivers", DRIVERS),
        ("teams", TEAMS),
        ("tracks", TRACKS),
    ):
        ids = [row["id"] for row in rows]
        duplicate_ids = sorted({entity_id for entity_id in ids if ids.count(entity_id) > 1})
        if duplicate_ids:
            raise ValueError(f"Duplicate {entity_name} seed ids: {', '.join(duplicate_ids)}")

    track_ids = {track["id"] for track in TRACKS}
    missing_calendar_track_ids = sorted({stage["track_id"] for stage in MVP_CALENDAR} - track_ids)
    if missing_calendar_track_ids:
        raise ValueError(
            "MVP calendar references missing track ids: " + ", ".join(missing_calendar_track_ids)
        )


def update_existing_season_stages(session: Session) -> None:
    for stage in MVP_CALENDAR:
        session.execute(
            update(SeasonStage)
            .where(
                SeasonStage.stage_number == stage["stage_number"],
                SeasonStage.track_id == stage["track_id"],
            )
            .values(weekend_date=stage["weekend_date"])
        )


def track_length_meters(track: dict[str, Any]) -> Decimal:
    average_length = average_raw_svg_length(svg_path_for_track(item) for item in TRACKS)
    normalized_length = normalized_track_length_meters(
        raw_svg_path_length(svg_path_for_track(track)),
        average_length,
    )
    return Decimal(str(normalized_length)).quantize(Decimal("0.1"))


def track_laps(track: dict[str, Any]) -> int:
    length = float(track_length_meters(track))
    profile = build_track_geometry_profile(
        svg_path_for_track(track),
        track_length_meters=length,
    )
    return derived_laps_for_race(predicted_lap_seconds(profile, length))


MONACO_SVG_PATH = (
    "M 291 40 L 302 42 L 356 86 L 384 104 L 434 132 L 473 161 "
    "L 546 194 L 603 233 L 623 242 L 634 246 L 650 247 L 662 244 "
    "L 673 239 L 688 224 L 698 199 L 703 163 L 708 151 L 714 146 "
    "L 744 137 L 848 126 L 875 126 L 888 130 L 896 135 L 898 140 "
    "L 898 148 L 884 165 L 881 183 L 883 186 L 887 186 L 900 175 "
    "L 908 174 L 924 175 L 940 183 L 949 188 L 958 197 L 959 201 "
    "L 960 210 L 956 222 L 932 241 L 879 271 L 830 290 L 789 302 "
    "L 750 308 L 714 309 L 660 302 L 620 289 L 571 267 L 535 246 "
    "L 506 224 L 492 219 L 470 215 L 430 176 L 382 140 L 330 98 "
    "L 313 89 L 298 89 L 271 97 L 252 108 L 235 120 L 218 137 "
    "L 210 149 L 202 166 L 199 190 L 195 199 L 178 225 L 159 247 "
    "L 138 255 L 121 271 L 108 292 L 96 333 L 95 364 L 100 388 "
    "L 98 401 L 93 406 L 81 406 L 63 396 L 46 382 L 41 373 "
    "L 40 364 L 52 338 L 53 329 L 65 294 L 91 241 L 110 211 "
    "L 136 175 L 188 113 L 207 95 L 223 82 L 260 60 L 280 44 "
    "L 290 41 Z"
)


SPA_SVG_PATH = (
    "M 40 627 L 44 604 L 78 505 L 179 387 L 194 367 L 210 331 "
    "L 215 326 L 230 317 L 271 301 L 292 288 L 360 223 L 401 194 "
    "L 507 144 L 679 68 L 706 55 L 717 46 L 737 40 L 750 43 "
    "L 769 64 L 781 67 L 798 64 L 836 47 L 857 49 L 895 92 "
    "L 955 151 L 960 164 L 959 185 L 951 195 L 932 194 L 925 189 "
    "L 879 140 L 865 133 L 854 134 L 834 150 L 798 169 L 681 208 "
    "L 642 226 L 631 240 L 626 253 L 626 288 L 632 306 L 646 332 "
    "L 665 346 L 690 354 L 739 360 L 809 378 L 831 386 L 847 399 "
    "L 852 414 L 851 431 L 843 464 L 848 481 L 859 490 L 936 522 "
    "L 950 532 L 957 541 L 959 559 L 955 576 L 945 599 L 933 617 "
    "L 917 632 L 896 640 L 879 640 L 863 636 L 839 626 L 761 582 "
    "L 731 551 L 669 467 L 633 434 L 549 404 L 512 400 L 494 405 "
    "L 446 437 L 396 459 L 341 473 L 302 475 L 299 478 L 298 500 "
    "L 290 509 L 272 513 L 255 503 L 246 502 L 214 505 L 191 513 "
    "L 151 538 L 91 595 L 60 620 L 42 625 Z"
)


SAKHIR_SVG_PATH = (
    "M 130 40 L 121 43 L 111 53 L 109 60 L 55 462 L 56 496 "
    "L 77 547 L 80 566 L 76 579 L 43 615 L 40 627 L 42 632 "
    "L 47 636 L 62 638 L 858 636 L 900 633 L 928 627 L 950 617 "
    "L 958 608 L 960 599 L 957 585 L 950 573 L 733 214 L 660 106 "
    "L 648 94 L 635 91 L 613 96 L 595 110 L 564 167 L 545 212 "
    "L 543 243 L 546 275 L 554 291 L 574 312 L 611 333 L 667 353 "
    "L 688 366 L 696 375 L 715 404 L 727 434 L 728 447 L 726 459 "
    "L 724 466 L 714 477 L 704 484 L 689 487 L 272 487 L 197 481 "
    "L 172 477 L 168 469 L 170 457 L 182 440 L 199 424 L 224 414 "
    "L 246 414 L 458 437 L 481 437 L 486 434 L 490 428 L 486 413 "
    "L 478 405 L 377 335 L 350 311 L 345 301 L 344 288 L 346 227 "
    "L 341 208 L 336 202 L 319 190 L 279 176 L 186 88 L 172 66 "
    "L 163 56 L 142 42 L 131 41 Z"
)


IMOLA_SVG_PATH = (
    "M 926 40 L 935 41 L 946 57 L 959 84 L 960 94 L 957 102 "
    "L 930 117 L 894 133 L 877 144 L 784 239 L 754 262 L 721 280 "
    "L 668 304 L 655 307 L 647 306 L 641 297 L 634 295 L 518 299 "
    "L 452 303 L 414 302 L 399 297 L 384 297 L 361 330 L 357 343 "
    "L 358 360 L 379 445 L 380 458 L 377 479 L 368 507 L 360 524 "
    "L 349 536 L 343 540 L 327 541 L 255 529 L 229 529 L 188 534 "
    "L 59 556 L 47 554 L 41 548 L 40 533 L 47 522 L 134 442 "
    "L 136 432 L 128 398 L 129 386 L 202 186 L 213 177 L 244 161 "
    "L 256 152 L 262 146 L 270 122 L 276 114 L 336 98 L 407 87 "
    "L 466 85 L 494 87 L 601 106 L 743 104 L 780 98 L 906 45 "
    "L 925 41 Z"
)


SILVERSTONE_SVG_PATH = (
    "M 268 40 L 284 42 L 322 67 L 437 153 L 485 190 L 495 201 "
    "L 502 215 L 505 237 L 497 303 L 499 319 L 504 334 L 523 365 "
    "L 563 410 L 574 433 L 574 442 L 570 449 L 525 465 L 519 470 "
    "L 517 481 L 519 488 L 523 491 L 539 498 L 572 506 L 603 507 "
    "L 617 501 L 845 240 L 849 227 L 849 209 L 845 195 L 828 187 "
    "L 799 186 L 782 181 L 774 172 L 772 160 L 771 150 L 775 136 "
    "L 788 129 L 801 129 L 816 133 L 853 150 L 894 175 L 922 203 "
    "L 931 220 L 937 240 L 960 450 L 958 480 L 950 499 L 929 513 "
    "L 885 529 L 821 543 L 690 553 L 676 557 L 653 572 L 637 578 "
    "L 617 578 L 577 563 L 556 559 L 539 563 L 502 584 L 489 587 "
    "L 480 586 L 467 581 L 451 567 L 421 523 L 190 401 L 93 345 "
    "L 60 319 L 42 298 L 40 280 L 45 258 L 59 243 L 130 199 "
    "L 212 126 L 214 119 L 213 110 L 201 97 L 199 87 L 200 78 "
    "L 210 65 L 239 47 L 254 42 L 267 41 Z"
)


ZANDVOORT_SVG_PATH = (
    "M 226 40 L 261 41 L 361 66 L 478 77 L 502 88 L 516 107 "
    "L 535 165 L 537 222 L 525 283 L 516 302 L 502 313 L 475 313 "
    "L 453 300 L 425 269 L 375 194 L 344 165 L 330 161 L 306 161 "
    "L 284 172 L 272 188 L 269 224 L 276 260 L 313 357 L 329 392 "
    "L 370 464 L 416 526 L 473 592 L 512 632 L 566 679 L 566 701 "
    "L 547 730 L 547 749 L 552 761 L 573 775 L 593 776 L 604 772 "
    "L 833 628 L 859 623 L 881 624 L 900 633 L 922 664 L 941 707 "
    "L 956 756 L 960 781 L 960 815 L 952 846 L 932 881 L 911 902 "
    "L 897 911 L 856 929 L 828 933 L 94 936 L 69 932 L 54 922 "
    "L 42 902 L 40 881 L 44 868 L 53 856 L 71 843 L 94 839 "
    "L 238 841 L 264 836 L 333 810 L 353 807 L 381 814 L 456 897 "
    "L 475 901 L 494 899 L 508 888 L 515 873 L 515 855 L 508 839 "
    "L 418 734 L 391 691 L 371 634 L 353 522 L 336 479 L 323 461 "
    "L 287 423 L 214 366 L 193 345 L 172 309 L 153 262 L 124 174 "
    "L 123 148 L 127 123 L 138 97 L 168 63 L 195 47 L 225 41 Z"
)


MONZA_SVG_PATH = (
    "M 158 40 L 173 42 L 180 48 L 240 138 L 284 191 L 392 296 "
    "L 452 352 L 462 359 L 500 359 L 513 364 L 530 379 L 543 382 "
    "L 719 387 L 914 388 L 932 390 L 945 395 L 953 404 L 959 414 "
    "L 960 432 L 958 442 L 947 463 L 929 477 L 900 488 L 848 497 "
    "L 799 502 L 395 499 L 388 497 L 380 486 L 369 487 L 324 500 "
    "L 277 500 L 225 494 L 194 481 L 165 457 L 142 420 L 131 385 "
    "L 106 228 L 101 221 L 88 216 L 85 211 L 72 170 L 48 116 "
    "L 40 88 L 44 71 L 59 60 L 120 45 L 158 41 Z"
)


SUZUKA_SVG_PATH = (
    "M 105 42 L 119 54 L 167 157 L 203 184 L 260 204 L 304 205 "
    "L 334 196 L 398 118 L 413 115 L 393 186 L 412 288 L 449 289 "
    "L 493 271 L 592 191 L 624 201 L 659 182 L 705 188 L 743 219 "
    "L 953 491 L 960 510 L 954 545 L 940 565 L 915 567 L 855 480 "
    "L 804 468 L 794 458 L 779 406 L 767 391 L 718 383 L 695 367 "
    "L 687 343 L 705 280 L 685 254 L 638 235 L 592 237 L 556 258 "
    "L 494 325 L 422 328 L 405 280 L 152 178 L 60 111 L 40 84 "
    "L 42 55 L 70 40 L 106 43 Z"
)


AUSTIN_SVG_PATH = (
    "M 959 40 L 953 92 L 892 278 L 797 346 L 736 335 L 689 421 "
    "L 601 423 L 567 451 L 557 483 L 561 543 L 529 584 L 517 652 "
    "L 442 776 L 453 814 L 516 890 L 517 911 L 392 889 L 40 781 "
    "L 47 754 L 160 643 L 191 649 L 286 708 L 328 711 L 360 701 "
    "L 397 655 L 397 614 L 388 595 L 301 526 L 299 510 L 343 503 "
    "L 399 541 L 440 532 L 443 522 L 346 452 L 343 435 L 634 269 "
    "L 767 178 L 921 54 L 960 41 Z"
)


VEGAS_SVG_PATH = (
    "M 310 40 L 349 61 L 368 85 L 375 110 L 378 198 L 381 206 "
    "L 394 210 L 767 202 L 801 195 L 821 177 L 829 149 L 824 131 "
    "L 795 96 L 790 68 L 800 50 L 823 52 L 937 153 L 957 188 "
    "L 960 539 L 927 592 L 853 595 L 422 587 L 310 568 L 218 535 "
    "L 40 441 L 41 395 L 53 365 L 73 338 L 157 299 L 193 258 "
    "L 206 187 L 211 53 L 228 49 L 262 65 L 275 58 L 282 41 "
    "L 311 41 Z"
)


INTERLAGOS_SVG_PATH = (
    "M 788 40 L 579 45 L 499 56 L 146 242 L 72 290 L 45 317 "
    "L 40 335 L 47 352 L 93 383 L 87 464 L 94 505 L 110 542 "
    "L 142 574 L 180 588 L 232 591 L 692 592 L 747 581 L 761 553 "
    "L 764 497 L 758 449 L 738 410 L 693 377 L 569 337 L 455 284 "
    "L 417 249 L 409 200 L 421 168 L 453 139 L 502 119 L 556 112 "
    "L 570 123 L 560 189 L 564 205 L 589 214 L 620 211 L 640 192 "
    "L 677 127 L 737 92 L 760 88 L 772 101 L 768 127 L 724 200 "
    "L 718 228 L 734 276 L 754 299 L 782 313 L 886 347 L 933 347 "
    "L 952 326 L 960 295 L 960 240 L 948 200 L 865 82 L 827 51 "
    "L 790 41 Z"
)


ABUDHABI_SVG_PATH = (
    "M 832 40 L 840 41 L 845 44 L 847 49 L 848 55 L 846 61 "
    "L 829 71 L 794 85 L 777 102 L 777 122 L 769 141 L 754 159 "
    "L 729 185 L 697 217 L 672 239 L 654 251 L 631 263 L 602 276 "
    "L 581 289 L 567 302 L 557 314 L 552 326 L 548 339 L 546 352 "
    "L 546 364 L 548 376 L 553 394 L 562 418 L 567 436 L 567 447 "
    "L 557 466 L 538 494 L 516 523 L 491 553 L 473 568 L 464 570 "
    "L 457 569 L 451 567 L 388 510 L 266 398 L 202 341 L 196 339 "
    "L 191 339 L 186 340 L 180 344 L 174 350 L 162 375 L 144 419 "
    "L 135 446 L 134 456 L 134 462 L 135 466 L 161 492 L 213 542 "
    "L 242 572 L 249 584 L 252 595 L 253 604 L 247 615 L 235 628 "
    "L 221 640 L 207 649 L 195 652 L 186 648 L 174 639 L 159 625 "
    "L 150 616 L 146 615 L 141 614 L 135 615 L 122 628 L 101 653 "
    "L 90 676 L 89 698 L 90 720 L 93 743 L 96 758 L 99 765 "
    "L 132 799 L 195 858 L 226 894 L 226 905 L 213 922 L 185 946 "
    "L 168 958 L 161 959 L 154 958 L 147 955 L 140 953 L 133 952 "
    "L 122 954 L 107 958 L 98 959 L 93 956 L 82 923 L 66 861 "
    "L 54 813 L 48 779 L 44 744 L 41 709 L 40 643 L 41 546 "
    "L 43 489 L 46 473 L 49 460 L 54 448 L 61 435 L 72 418 "
    "L 84 401 L 98 382 L 105 369 L 106 359 L 103 350 L 96 340 "
    "L 93 332 L 92 325 L 99 318 L 112 310 L 152 294 L 220 269 "
    "L 291 241 L 368 209 L 496 160 L 675 94 L 780 56 L 811 46 "
    "L 827 41 L 828 40 Z"
)


TRACK_SVG_PATHS: dict[str, str] = {
    "track-silverstone": SILVERSTONE_SVG_PATH,
    "track-abudhabi": ABUDHABI_SVG_PATH,
    "track-vegas": VEGAS_SVG_PATH,
    "track-interlagos": INTERLAGOS_SVG_PATH,
    "track-austin": AUSTIN_SVG_PATH,
    "track-zandvoort": ZANDVOORT_SVG_PATH,
    "track-monaco": MONACO_SVG_PATH,
    "track-spa": SPA_SVG_PATH,
    "track-monza": MONZA_SVG_PATH,
    "track-sakhir": SAKHIR_SVG_PATH,
    "track-imola": IMOLA_SVG_PATH,
    "track-suzuka": SUZUKA_SVG_PATH,
}


def svg_path_for_track(track: dict[str, Any]) -> str:
    try:
        return TRACK_SVG_PATHS[track["id"]]
    except KeyError as error:
        raise ValueError(f"No SVG path configured for track {track['id']!r}") from error


def track_segments_for_track(track: dict[str, Any]) -> list[dict[str, Any]]:
    length = float(track_length_meters(track))
    svg_path = svg_path_for_track(track)
    return [
        {
            "track_id": track["id"],
            "segment_index": segment.segment_index,
            "type": segment.type,
            "length_meters": Decimal(str(segment.length_meters)),
            "base_speed": Decimal(str(segment.base_speed)),
            "overtake_chance": Decimal(str(segment.overtake_chance)),
        }
        for segment in build_track_geometry_segments(
            svg_path,
            track_length_meters=length,
        )
    ]


def seed_mvp_catalog_database(database_url: str | None = None) -> SeedSummary:
    engine = create_engine(database_url or get_settings().database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    try:
        with session_factory.begin() as session:
            return seed_mvp_catalog(session)
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Заполнить базу данных PostgreSQL MVP-каталогом пилотов, команд, трасс и календаря."
        )
    )
    parser.add_argument(
        "--database-url",
        help=(
            "URL базы данных SQLAlchemy. По умолчанию берётся "
            "DATABASE_URL из settings или .env."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Не выводить сводку после заполнения.",
    )
    args = parser.parse_args(argv)

    try:
        summary = seed_mvp_catalog_database(args.database_url)
    except (SQLAlchemyError, ValueError) as exc:
        raise SystemExit(f"Не удалось заполнить MVP-каталог: {exc}") from exc

    if not args.quiet:
        print(
            "MVP-каталог заполнен: "
            f"drivers={summary.drivers}, "
            f"teams={summary.teams}, "
            f"tracks={summary.tracks}, "
            f"calendarStages={summary.calendar_stages}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
