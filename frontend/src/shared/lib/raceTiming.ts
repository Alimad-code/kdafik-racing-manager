const secondsPattern = /^([+-]?)(\d+(?:[.,]\d+)?)(?:\s*[сСcCsS])?$/;

function formatSecondsValue(sign: string, rawValue: string) {
  const seconds = Number(rawValue.replace(",", "."));

  if (!Number.isFinite(seconds)) {
    return `${sign}${rawValue.replace(/[сСcCsS]\s*$/u, "")}`;
  }

  if (seconds < 60) {
    return `${sign}${seconds.toFixed(3)}`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  const milliseconds = Math.round((seconds - Math.floor(seconds)) * 1000);

  return `${sign}${minutes}:${String(remainingSeconds).padStart(2, "0")}:${String(
    milliseconds
  ).padStart(3, "0")}`;
}

export function formatRaceGap(value?: string | null) {
  const rawValue = value?.trim();

  if (!rawValue || rawValue === "-") {
    return "-";
  }

  const normalized = rawValue.toLowerCase();

  if (normalized === "leader" || normalized === "winner" || normalized === "pole") {
    return "Лидер";
  }

  if (normalized === "dnf" || normalized === "out" || normalized === "retired") {
    return "Сход";
  }

  if (normalized === "no time" || normalized === "no-time" || normalized === "no_time") {
    return "Без времени";
  }

  if (normalized === "in pit" || normalized === "in pits") {
    return "в питах";
  }

  const secondsMatch = rawValue.match(secondsPattern);

  if (secondsMatch) {
    return formatSecondsValue(secondsMatch[1] ?? "", secondsMatch[2] ?? "");
  }

  return rawValue.replace(/\s*[сСcCsS]\s*$/u, "");
}
