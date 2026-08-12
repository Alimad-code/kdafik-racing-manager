import type { TireCompound } from "@/entities";
import { getTeam } from "@/features/season/lib/seasonViewData";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";

export const FALLBACK_TEAM_COLOR = "#64748b";

export const compoundStyles = {
  Soft: "border-danger text-danger",
  Medium: "border-warning text-warning",
  Hard: "border-muted-foreground/60 text-muted-foreground",
  Intermediate: "border-sky-400 text-sky-300",
  Wet: "border-blue-500 text-blue-300"
} satisfies Record<TireCompound, string>;

export const compoundLabels: Record<TireCompound, string> = {
  Soft: "Софт",
  Medium: "Медиум",
  Hard: "Хард",
  Intermediate: "Интер",
  Wet: "Дождь"
};

export const compoundShortLabels: Record<TireCompound, string> = {
  Soft: "С",
  Medium: "М",
  Hard: "Х",
  Intermediate: "И",
  Wet: "Д"
};

export function getTeamAccent(teamId: string) {
  return getReadableTeamAccent(getTeam(teamId).color || FALLBACK_TEAM_COLOR);
}
