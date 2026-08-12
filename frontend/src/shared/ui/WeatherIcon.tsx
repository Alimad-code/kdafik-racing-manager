import { CloudRain, Sun } from "lucide-react";

type WeatherIconProps = {
  value: string;
  className?: string;
};

export function WeatherIcon({ value, className = "h-4 w-4" }: WeatherIconProps) {
  const iconClassName = `${className} shrink-0`;

  if (
    ["light", "moderate", "heavy", "rain", "mixed", "light-rain", "intermediate", "wet"].includes(
      value.toLowerCase()
    )
  ) {
    return <CloudRain aria-hidden="true" className={`${iconClassName} text-info`} />;
  }

  return <Sun aria-hidden="true" className={`${iconClassName} text-warning`} />;
}

export function WeatherSummary({ value }: { value: string }) {
  const labels: Record<string, string> = {
    none: "Без осадков",
    light: "Лёгкий дождь",
    moderate: "Дождь",
    heavy: "Сильный дождь",
    clear: "Без осадков",
    cloudy: "Без осадков",
    rain: "Дождь",
    mixed: "Дождь"
  };

  return (
    <span className="inline-flex items-center gap-2">
      <WeatherIcon value={value} />
      <span>{labels[value] ?? value}</span>
    </span>
  );
}
