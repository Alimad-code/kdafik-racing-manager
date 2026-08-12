import type {
  CarCondition,
  ChampionshipStanding,
  ConstructorStanding,
  Driver,
  SeasonStage,
  SessionEvent,
  SessionResult,
  Team,
  Track
} from "@/entities";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import type { StandingsTableRow } from "@/shared/ui";

const fallbackDriver: Driver = {
  id: "unknown-driver",
  number: 0,
  firstName: "Неизвестный",
  lastName: "Пилот",
  code: "---",
  nationality: "-",
  price: 0,
  pace: 0,
  stability: 0
};

const fallbackTeam: Team = {
  id: "unknown-team",
  name: "Неизвестная команда",
  shortName: "Неизвестно",
  baseCountry: "-",
  powerUnit: "-",
  color: "#64748b",
  price: 0,
  carRating: 0,
  reliability: 0,
  setupCost: 0,
  repairCost: 0,
  carBuildCost: 0,
  minimumRepairReserve: 0,
  minimumSetupReserve: 0,
  minimumReserve: 0
};

const fallbackTrack: Track = {
  id: "unknown-track",
  name: "Неизвестная трасса",
  country: "-",
  profile: "balanced",
  laps: 0,
  lengthKm: 0,
  climate: {
    rainProbability: 0,
    trackTemperatureMinC: 20,
    trackTemperatureMaxC: 30,
    variability: 0
  },
  svgPath: ""
};

const fallbackStage: SeasonStage = {
  id: "unknown-stage",
  stageNumber: 1,
  trackId: fallbackTrack.id,
  status: "locked",
  weekendDate: ""
};

export function getDriver(driverId: string) {
  const driver = seasonRepository.getDrivers().find((item) => item.id === driverId);

  return driver ?? { ...fallbackDriver, id: driverId || fallbackDriver.id };
}

export function getTeam(teamId: string) {
  const team = seasonRepository.getTeams().find((item) => item.id === teamId);

  return team ?? { ...fallbackTeam, id: teamId || fallbackTeam.id };
}

export function getTrack(trackId: string) {
  const track = seasonRepository.getTracks().find((item) => item.id === trackId);

  return track ?? { ...fallbackTrack, id: trackId || fallbackTrack.id };
}

export function getCurrentStage() {
  const currentStageId = useSeasonStore.getState().currentStageId;
  const stages = seasonRepository.getStages();

  const foundById =
    stages.find((stage) => stage.id === currentStageId) ??
    stages.find((stage) => stage.id === seasonRepository.getActiveSeason()?.currentStageId);

  if (foundById) {
    return foundById;
  }

  const available = stages.find((stage) => stage.status === "available");
  if (available) {
    return available;
  }

  // If no available stage, the season might be finished. Fallback to the last completed stage.
  const completed = [...stages].reverse().find((stage) => stage.status === "completed");
  if (completed) {
    return completed;
  }

  return stages[0] ?? fallbackStage;
}

export function formatMoney(value: number) {
  return `$${value.toFixed(1)}М`;
}

export function formatDriverName(driverId: string) {
  const driver = getDriver(driverId);
  return `${driver.firstName} ${driver.lastName}`;
}

export function formatDriverCode(driverId: string) {
  return getDriver(driverId).code;
}

export function formatTeamName(teamId: string) {
  return getTeam(teamId).shortName;
}

export function formatWeather(value: string) {
  const labels: Record<string, string> = {
    none: "Без осадков",
    light: "Лёгкий дождь",
    moderate: "Дождь",
    heavy: "Сильный дождь",
    clear: "Без осадков",
    cloudy: "Без осадков",
    rain: "Дождь",
    mixed: "Дождь",
    dry: "Без осадков",
    "light-rain": "Лёгкий дождь",
    intermediate: "Дождь",
    wet: "Сильный дождь"
  };

  return labels[value] ?? value;
}

export function formatTrackProfile(profile: Track["profile"]) {
  const labels: Record<Track["profile"], string> = {
    speed: "Скоростная",
    balanced: "Сбалансированная",
    technical: "Техническая"
  };

  return labels[profile];
}

export function getDownforceZone(value: number) {
  if (value <= 33) {
    return {
      label: "Скорость / низкая прижимная сила",
      shortLabel: "Скорость",
      tradeoff: "Выше скорость на прямых, но выше риск нестабильности.",
      variant: "info" as const
    };
  }

  if (value >= 67) {
    return {
      label: "Стабильность / высокая прижимная сила",
      shortLabel: "Стабильность",
      tradeoff: "Лучше контроль в поворотах, но ниже максимальная скорость.",
      variant: "success" as const
    };
  }

  return {
    label: "Баланс / средняя прижимная сила",
    shortLabel: "Баланс",
    tradeoff: "Компромисс между скоростью и устойчивостью.",
    variant: "completed" as const
  };
}

export function formatCarCondition(condition: CarCondition) {
  const labels: Record<CarCondition, string> = {
    healthy: "Готов",
    damaged: "Поврежден",
    "heavily-damaged": "Сильно поврежден"
  };

  return labels[condition];
}

export function formatSessionEvent(event?: SessionEvent) {
  const labels: Record<SessionEvent, string> = {
    "clean-run": "Чистая серия",
    "setup-mismatch": "Настройка вне зоны",
    "no-time": "Без времени",
    "clean-race": "Чистая гонка",
    "driver-mistake": "Ошибка пилота",
    damage: "Повреждение",
    dnf: "Сход",
    "technical-issue": "Техпроблема"
  };

  return event ? labels[event] : "Без события";
}

export function toStandingsRows(rows: ChampionshipStanding[]): StandingsTableRow[] {
  const leaderPoints = rows[0]?.points ?? 0;

  return rows.map((row) => {
    const team = getTeam(row.teamId);
    return {
      position: row.position,
      participantId: row.driverId,
      label: formatDriverName(row.driverId),
      teamId: row.teamId,
      teamName: team.name,
      points: row.points,
      delta: row.position === 1 ? "Лидер" : `-${leaderPoints - row.points}`,
      accent: team.color
    };
  });
}

export function toConstructorRows(rows: ConstructorStanding[]): StandingsTableRow[] {
  const leaderPoints = rows[0]?.points ?? 0;

  return rows.map((row) => {
    const team = getTeam(row.teamId);
    return {
      position: row.position,
      participantId: row.teamId,
      label: team.name,
      teamId: row.teamId,
      points: row.points,
      delta: row.position === 1 ? "Лидер" : `-${leaderPoints - row.points}`,
      accent: team.color
    };
  });
}

export function getResultStatusLabel(result: SessionResult) {
  if (result.status === "classified") {
    return "Финишировал";
  }

  if (result.status === "retired") {
    return "Сход";
  }

  return "Без времени";
}
