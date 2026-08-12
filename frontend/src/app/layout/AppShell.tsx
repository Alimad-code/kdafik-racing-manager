import { LogOut, Tv, UserCircle } from "lucide-react";
import { Link, NavLink, useNavigate, useOutlet } from "react-router-dom";
import { useAuthStore } from "@/features/auth/model/useAuthStore";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { getTeam } from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { appNavigation } from "@/shared/config/navigation";
import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/utils";
import {
  BroadcastRouteTransition,
  Button,
  ButtonLink,
  KdafikLogo,
  LegalFooter,
  StatusBadge,
  TeamIcon,
  useBroadcastTransitionPreference
} from "@/shared/ui";

export function AppShell() {
  const navigate = useNavigate();
  const outlet = useOutlet();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const resetSessionState = useSeasonStore((state) => state.resetSessionState);
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const budget = useSeasonStore((state) => state.budget);
  const { enabled: broadcastTransitionsEnabled, setEnabled: setBroadcastTransitionsEnabled } =
    useBroadcastTransitionPreference();
  const selectedTeam = getTeam(selectedTeamId ?? "");
  const stages = seasonRepository.getStages();
  const stagesCount = stages.length;
  const completedStagesCount = stageProgress.filter((p) => p.raceStatus === "completed").length;
  const isSeasonFinished = stagesCount > 0 && completedStagesCount === stagesCount;
  const teamLabel = selectedTeamId ? selectedTeam.shortName : "Команда не выбрана";
  const profileDisplayName = user?.displayName ?? "Профиль";

  const topNavigation = appNavigation.filter(
    (item) =>
      item.to === ROUTES.home ||
      item.to === ROUTES.seasonOverview ||
      item.to === ROUTES.championshipSummary
  );

  async function handleLogout() {
    await logout();
    resetSessionState();
    navigate(ROUTES.login, { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col text-foreground">
      <header className="sticky top-0 z-30 border-b border-border bg-background/95 shadow-insetLine backdrop-blur">
        <div className="mx-auto max-w-7xl px-3 py-2.5 sm:px-5 lg:px-8">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between lg:gap-4">
            <div className="flex min-w-0 items-center justify-between gap-3 lg:shrink-0">
              <Link
                aria-label="Kdafik Racing Manager"
                to={ROUTES.home}
                className="group grid min-h-10 shrink-0 place-items-center"
              >
                <KdafikLogo className="h-7 w-28 sm:h-8 sm:w-32" />
              </Link>

              <div className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-x-4 gap-y-1 sm:justify-start">
                <span className="min-w-0">
                  <span className="block text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground sm:text-[10px]">
                    Команда
                  </span>
                  <span className="flex max-w-28 items-center gap-1.5 sm:max-w-36">
                    {selectedTeamId ? (
                      <TeamIcon
                        className="size-4 shrink-0"
                        color={selectedTeam.color}
                        teamId={selectedTeamId}
                      />
                    ) : null}
                    <span className="truncate font-mono text-[11px] font-black uppercase leading-tight tracking-[0.08em] text-foreground">
                      {teamLabel}
                    </span>
                  </span>
                </span>
                <span className="min-w-0">
                  <span className="block text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground sm:text-[10px]">
                    Бюджет
                  </span>
                  <span className="block font-mono text-[11px] font-black uppercase leading-tight tracking-[0.08em] text-foreground">
                    ${budget.availableMillions.toFixed(1)}М
                  </span>
                </span>
                {isSeasonFinished ? (
                  <span className="hidden 2xl:inline-flex">
                    <StatusBadge variant="completed">Финал</StatusBadge>
                  </span>
                ) : null}
              </div>
            </div>

            <div className="flex min-w-0 items-center gap-2 lg:flex-1 lg:justify-end">
              <nav className="flex min-w-0 flex-1 gap-1 overflow-x-auto border border-border bg-card/70 p-1 shadow-insetLine lg:flex-none">
                {topNavigation.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === ROUTES.home}
                    className={({ isActive }) =>
                      cn(
                        "inline-flex min-h-9 shrink-0 items-center gap-2 px-2.5 py-1.5 font-mono text-[10px] font-black uppercase tracking-[0.08em] transition sm:px-3 sm:py-2 sm:text-[11px]",
                        "text-muted-foreground hover:bg-secondary hover:text-foreground",
                        isActive && "bg-primary/15 text-foreground shadow-insetLine"
                      )
                    }
                  >
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </nav>
              <ButtonLink
                to={ROUTES.profile}
                variant="secondary"
                aria-label={`Открыть профиль: ${profileDisplayName}`}
                className="max-w-[9.5rem] shrink-0 gap-1.5 bg-card/70 px-2.5 py-1.5 text-[10px] tracking-[0.08em] shadow-insetLine sm:max-w-[12rem] sm:px-3 sm:py-2 sm:text-[11px]"
                title={profileDisplayName}
              >
                <UserCircle className="size-4 shrink-0 text-primary" />
                <span className="min-w-0 truncate">{profileDisplayName}</span>
              </ButtonLink>
              <Button
                aria-label={`ТВ-переходы ${broadcastTransitionsEnabled ? "включены" : "выключены"}`}
                aria-pressed={broadcastTransitionsEnabled}
                className="min-h-9 shrink-0 px-2.5 py-1.5 text-[10px] sm:px-3 sm:py-2 sm:text-[11px]"
                title="ТВ-переходы"
                variant={broadcastTransitionsEnabled ? "secondary" : "ghost"}
                onClick={() => setBroadcastTransitionsEnabled(!broadcastTransitionsEnabled)}
              >
                <Tv className="size-4" />
                <span className="hidden xl:inline">ТВ</span>
              </Button>
              <Button
                aria-label="Выйти"
                className="min-h-9 shrink-0 px-2.5 py-1.5 text-[10px] sm:px-3 sm:py-2 sm:text-[11px]"
                variant="ghost"
                onClick={handleLogout}
              >
                <LogOut className="size-4" />
                <span className="hidden sm:inline">Выйти</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-3 py-4 sm:px-5 sm:py-6 lg:px-8">
        <BroadcastRouteTransition enabled={broadcastTransitionsEnabled}>
          {outlet}
        </BroadcastRouteTransition>
      </main>
      <LegalFooter />
    </div>
  );
}
