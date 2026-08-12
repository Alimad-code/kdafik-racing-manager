import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import {
  getCurrentStage,
  getTrack,
  getTeam,
  toStandingsRows
} from "@/features/season/lib/seasonViewData";
import { ROUTES } from "@/shared/constants/routes";
import { formatPositionLabel } from "@/shared/lib/positionLabel";
import { getCurrentStageMeta } from "@/pages/_shared/race-weekend";
import {
  Button,
  ButtonLink,
  InfoChip,
  Modal,
  PageHeader,
  PageSurface,
  SectionHeader,
  StandingsTable,
  StatBlock
} from "@/shared/ui";

export function HomePage() {
  const navigate = useNavigate();
  const [isRestartModalOpen, setIsRestartModalOpen] = useState(false);
  const budget = useSeasonStore((state) => state.budget);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const startNewSeason = useSeasonStore((state) => state.startNewSeason);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const currentStage = getCurrentStage();
  const currentTrack = getTrack(currentStage.trackId);
  const standings = seasonRepository.getChampionshipStandings();
  const constructorStandings = seasonRepository.getConstructorStandings();
  const stages = seasonRepository.getStages();

  const completedStagesCount = stageProgress.filter((p) => p.raceStatus === "completed").length;
  const isSeasonFinished = stages.length > 0 && completedStagesCount === stages.length;

  const constructorLeader = constructorStandings[0];
  const selectedTeam = getTeam(selectedTeamId ?? "");
  const playerTeamStanding = constructorStandings.find((s) => s.teamId === selectedTeamId);

  function handleRestartSeason() {
    setIsRestartModalOpen(true);
  }

  async function confirmRestart() {
    try {
      await startNewSeason();
      setIsRestartModalOpen(false);
      navigate(ROUTES.seasonSetup);
    } catch {
      setIsRestartModalOpen(false);
    }
  }

  return (
    <PageSurface>
      <PageHeader
        title="Главная панель"
        actions={
          <>
            <ButtonLink to={ROUTES.budgetHistory} variant="secondary">
              История бюджета
            </ButtonLink>
            {isSeasonFinished ? (
              <ButtonLink to={ROUTES.championshipSummary}>Итоги чемпионата</ButtonLink>
            ) : (
              <>
                <ButtonLink to={ROUTES.seasonOverview}>Продолжить сезон</ButtonLink>
                <Button disabled={isLoading} variant="secondary" onClick={handleRestartSeason}>
                  {isLoading ? "Запуск..." : "Начать новый сезон"}
                </Button>
              </>
            )}
          </>
        }
        meta={
          <>
            <InfoChip label="Свободно" value={`$${budget.freeMillions.toFixed(1)}М`} />
            <InfoChip label="Настройки" value={`$${budget.setupReserveMillions.toFixed(1)}М`} />
            <InfoChip label="Ремонт" value={`$${budget.repairReserveMillions.toFixed(1)}М`} />
            <InfoChip
              {...(isSeasonFinished
                ? { label: "Финал", value: "Сезон завершен" }
                : getCurrentStageMeta(currentStage, currentTrack))}
            />
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2">
        <StatBlock
          label="Место в кубке конструкторов"
          value={formatPositionLabel(playerTeamStanding?.position)}
          detail={
            playerTeamStanding
              ? `${playerTeamStanding.points} очков команды`
              : "Данные зачета ожидаются"
          }
          status=""
          accent={selectedTeam.color}
        />
        <StatBlock
          label="Лидер чемпионата"
          value={constructorLeader ? getTeam(constructorLeader.teamId).name : "-"}
          detail={
            constructorLeader
              ? `${constructorLeader.points} очков, ${constructorLeader.wins} побед`
              : "Ожидание первых гонок"
          }
          status=""
          accent={constructorLeader ? getTeam(constructorLeader.teamId).color : undefined}
        />
      </section>

      <section className="min-w-0 space-y-4">
        <SectionHeader title="Срез чемпионата" />
        <StandingsTable rows={toStandingsRows(standings)} caption="Личный зачет" />
      </section>

      <Modal
        description="Вы уверены, что хотите прервать текущий сезон и начать новый? Весь текущий прогресс, результаты гонок и накопленный бюджет будут безвозвратно утерян."
        confirmLabel="Начать заново"
        isLoading={isLoading}
        isOpen={isRestartModalOpen}
        title="Сброс сезона"
        onClose={() => setIsRestartModalOpen(false)}
        onConfirm={confirmRestart}
      />
    </PageSurface>
  );
}
