import type { SeasonStage, Track } from "@/entities";

export function getGrandPrixTitle(track: Track) {
  return `ЭТАП · ${track.country.toUpperCase()}`;
}

export function getCurrentStageMeta(
  stage: Pick<SeasonStage, "stageNumber">,
  track: Pick<Track, "country">
) {
  return {
    label: "Текущий этап",
    value: `${stage.stageNumber} · ${track.country}`
  };
}

export function getStageMeta(
  stage: Pick<SeasonStage, "stageNumber">,
  track: Pick<Track, "country">
) {
  return {
    label: "Этап",
    value: `${stage.stageNumber} · ${track.country}`
  };
}
