export const LIVE_TIRE_COMPOUNDS = ["Soft", "Medium", "Hard", "Intermediate", "Wet"] as const;

export const liveTireLabels: Record<string, string> = {
  Soft: "Софт",
  Medium: "Медиум",
  Hard: "Хард",
  Intermediate: "Интер",
  Wet: "Дождь"
};

export const compoundShortLabels: Record<string, string> = {
  Soft: "С",
  Medium: "М",
  Hard: "Х",
  Intermediate: "И",
  Wet: "Д"
};

export const compoundTextClassName: Record<string, string> = {
  Soft: "text-danger",
  Medium: "text-warning",
  Hard: "text-muted-foreground",
  Intermediate: "text-sky-300",
  Wet: "text-blue-300"
};
