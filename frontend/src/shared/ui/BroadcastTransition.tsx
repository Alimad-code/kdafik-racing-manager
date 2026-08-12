import type { CSSProperties, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker } from "react-router-dom";
import { KdafikLogo } from "@/shared/ui/KdafikLogo";
import { prefersReducedMotion } from "@/shared/ui/useBroadcastTransitionPreference";

const WIPE_DURATION_MS = 700;
const COVER_HOLD_MS = 550;
const ANIMATION_FALLBACK_MS = WIPE_DURATION_MS + 150;

type WipeState = "idle" | "wiping_in" | "wiping_out";

function isBroadcastRoute(pathname: string) {
  return pathname !== "/login";
}

export function BroadcastWipe({
  state,
  scope = "page",
  onPhaseComplete
}: {
  state: WipeState;
  scope?: "page" | "container";
  onPhaseComplete?: () => void;
}) {
  const bars = useMemo(() => Array.from({ length: 5 }, (_, index) => index), []);

  if (state === "idle") return null;

  return (
    <div
      aria-hidden="true"
      data-testid="broadcast-wipe"
      className={`broadcast-wipe pointer-events-none inset-0 z-50 overflow-hidden ${
        scope === "page" ? "fixed" : "absolute"
      }`}
    >
      {bars.map((barIndex) => (
        <div
          key={barIndex}
          className={`broadcast-wipe-bar absolute inset-x-0 ${
            state === "wiping_in" ? "animate-wipe-in" : "animate-wipe-out"
          }`}
          style={
            {
              "--bar-idx": barIndex,
              top: `${barIndex * 20}%`,
              height: "20.2%",
              background:
                barIndex % 2 === 0
                  ? "linear-gradient(90deg, hsl(var(--background)), hsl(var(--surface-track)))"
                  : "linear-gradient(90deg, hsl(var(--surface-track)), hsl(var(--background)))"
            } as CSSProperties
          }
          onAnimationEnd={barIndex === bars.length - 1 ? onPhaseComplete : undefined}
        />
      ))}
      <KdafikLogo
        data-testid="broadcast-wipe-logo"
        className={`broadcast-wipe-logo absolute left-1/2 top-1/2 h-[clamp(5.5rem,18vh,9.5rem)] w-[clamp(14rem,42vw,30rem)] opacity-90 [filter:drop-shadow(0_0_18px_rgba(109,40,217,0.24))] ${
          state === "wiping_in" ? "animate-wipe-logo-in" : "animate-wipe-logo-out"
        }`}
      />
    </div>
  );
}

export function BroadcastRouteTransition({
  children,
  enabled
}: {
  children: ReactNode;
  enabled: boolean;
}) {
  const [transitionState, setTransitionState] = useState<WipeState>("idle");
  const isTransitioningRef = useRef(false);
  const wipeInCompletedRef = useRef(false);
  const animationFallbackRef = useRef<number | null>(null);
  const revealTimerRef = useRef<number | null>(null);
  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    if (!enabled || isTransitioningRef.current || prefersReducedMotion()) return false;
    if (currentLocation.pathname === nextLocation.pathname) return false;

    return isBroadcastRoute(currentLocation.pathname) && isBroadcastRoute(nextLocation.pathname);
  });

  const clearTimers = useCallback(() => {
    if (animationFallbackRef.current !== null) {
      window.clearTimeout(animationFallbackRef.current);
      animationFallbackRef.current = null;
    }
    if (revealTimerRef.current !== null) {
      window.clearTimeout(revealTimerRef.current);
      revealTimerRef.current = null;
    }
  }, []);

  const finishTransition = useCallback(() => {
    clearTimers();
    setTransitionState("idle");
    isTransitioningRef.current = false;
    wipeInCompletedRef.current = false;
  }, [clearTimers]);

  const finishWipeIn = useCallback(() => {
    if (!isTransitioningRef.current || wipeInCompletedRef.current) return;

    wipeInCompletedRef.current = true;
    if (animationFallbackRef.current !== null) {
      window.clearTimeout(animationFallbackRef.current);
      animationFallbackRef.current = null;
    }
    blocker.proceed?.();
    revealTimerRef.current = window.setTimeout(() => {
      setTransitionState("wiping_out");
      animationFallbackRef.current = window.setTimeout(finishTransition, ANIMATION_FALLBACK_MS);
    }, COVER_HOLD_MS);
  }, [blocker, finishTransition]);

  const finishWipeOut = useCallback(() => {
    if (transitionState === "wiping_out") finishTransition();
  }, [finishTransition, transitionState]);

  useEffect(() => {
    return clearTimers;
  }, [clearTimers]);

  useEffect(() => {
    if (!enabled || prefersReducedMotion()) {
      clearTimers();
      setTransitionState("idle");
      isTransitioningRef.current = false;
      wipeInCompletedRef.current = false;
      return;
    }

    if (blocker.state !== "blocked" || isTransitioningRef.current) return;

    isTransitioningRef.current = true;
    wipeInCompletedRef.current = false;
    setTransitionState("wiping_in");
    animationFallbackRef.current = window.setTimeout(finishWipeIn, ANIMATION_FALLBACK_MS);
  }, [blocker.state, clearTimers, enabled, finishWipeIn]);

  return (
    <>
      {children}
      <BroadcastWipe
        state={transitionState}
        onPhaseComplete={transitionState === "wiping_in" ? finishWipeIn : finishWipeOut}
      />
    </>
  );
}
