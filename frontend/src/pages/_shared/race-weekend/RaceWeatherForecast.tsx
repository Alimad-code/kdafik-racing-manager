import { useState } from "react";
import type { StageWeather, Track } from "@/entities";
import { formatWeather } from "@/features/season/lib/seasonViewData";
import { cn } from "@/shared/lib/utils";
import { TrackMap } from "@/shared/ui";

const pointLabels = {
  start: "Старт",
  "one-third": "1/3",
  "two-thirds": "2/3",
  finish: "Финиш"
} as const;

function clampForecastValue(value: number) {
  return Math.max(0, Math.min(1, value));
}

function getForecastWetness(min: number, max: number) {
  return clampForecastValue((min + max) / 2);
}

function formatPercent(value: number) {
  return `${Math.round(clampForecastValue(value) * 100)}%`;
}

function formatWetnessRange(min: number, max: number) {
  const low = Math.round(clampForecastValue(Math.min(min, max)) * 100);
  const high = Math.round(clampForecastValue(Math.max(min, max)) * 100);

  return low === high ? `${low}%` : `${low}–${high}%`;
}

type RaceWeatherForecastProps = {
  track: Track;
  weather?: StageWeather | null;
  finishOnly?: boolean;
};

export function RaceWeatherForecast({
  track,
  weather,
  finishOnly = false
}: RaceWeatherForecastProps) {
  const [selectedPoint, setSelectedPoint] = useState(finishOnly ? "finish" : "start");
  const points = weather?.raceForecast ?? [];
  const activePoint =
    points.find((point) => point.point === (finishOnly ? "finish" : selectedPoint)) ?? points[0];

  if (!activePoint) {
    return (
      <div className="border border-line bg-secondary px-4 py-3 font-mono uppercase">
        <span className="text-[10px] font-black tracking-[0.22em] text-muted-foreground">
          Прогноз погоды
        </span>
        <strong className="mt-1 block text-sm text-foreground">Ожидается</strong>
      </div>
    );
  }

  return (
    <div
      className="min-w-0 overflow-hidden border border-line bg-secondary p-3 font-mono uppercase"
      data-testid="race-weather-forecast"
    >
      <div className="flex h-8 items-start justify-between gap-2">
        <span className="text-[10px] font-black tracking-[0.2em] text-muted-foreground">
          {finishOnly ? "Условия к финишу" : "Прогноз гонки"}
        </span>
        <strong
          className="flex h-8 max-w-[112px] items-start justify-end text-right text-[10px] leading-4 text-sky-300"
          data-testid="race-weather-condition"
        >
          {formatWeather(activePoint.expectedRain)}
        </strong>
      </div>

      {!finishOnly ? (
        <div className="mt-2 grid grid-cols-4 gap-1" role="tablist" aria-label="Точки прогноза">
          {points.map((point) => (
            <button
              key={point.point}
              type="button"
              role="tab"
              aria-selected={selectedPoint === point.point}
              className={cn(
                "border px-1 py-1.5 text-[9px] font-black tracking-[0.08em]",
                selectedPoint === point.point
                  ? "border-sky-400 bg-sky-400/15 text-sky-200"
                  : "border-line text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setSelectedPoint(point.point)}
            >
              {pointLabels[point.point]}
            </button>
          ))}
        </div>
      ) : null}

      <div className="mt-2 aspect-square w-full" data-testid="race-weather-map-frame">
        <TrackMap
          aria-label={`Прогноз влажности трассы ${track.name}`}
          className="h-full w-full"
          svgPath={track.svgPath}
          trackWetness={getForecastWetness(
            activePoint.trackWetnessMin,
            activePoint.trackWetnessMax
          )}
          variant="square"
        />
      </div>

      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[9px]">
        <dt className="text-muted-foreground">Вероятность дождя</dt>
        <dd className="text-right font-black text-foreground">
          {formatPercent(activePoint.rainChance)}
        </dd>
        <dt className="text-muted-foreground">Температура</dt>
        <dd className="text-right font-black text-foreground">
          {activePoint.trackTemp.toFixed(1)}°C
        </dd>
        <dt className="text-muted-foreground">Влажность трассы</dt>
        <dd className="text-right font-black text-foreground">
          {formatWetnessRange(activePoint.trackWetnessMin, activePoint.trackWetnessMax)}
        </dd>
      </dl>
    </div>
  );
}
