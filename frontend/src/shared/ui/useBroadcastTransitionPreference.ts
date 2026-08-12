import { useState } from "react";

const STORAGE_KEY = "kdafik:broadcast-transitions:v1";

export function prefersReducedMotion() {
  return (
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

function readStoredPreference() {
  if (typeof window === "undefined") return true;

  const stored = window.localStorage.getItem(STORAGE_KEY);

  if (stored === "off") return false;
  if (stored === "on") return true;

  return !prefersReducedMotion();
}

export function useBroadcastTransitionPreference() {
  const [enabled, setEnabled] = useState(readStoredPreference);

  function updateEnabled(nextEnabled: boolean) {
    setEnabled(nextEnabled);
    window.localStorage.setItem(STORAGE_KEY, nextEnabled ? "on" : "off");
  }

  return { enabled, setEnabled: updateEnabled };
}
