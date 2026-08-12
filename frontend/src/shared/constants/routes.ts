export const ROUTES = {
  home: "/",
  login: "/login",
  verifyEmail: "/verify-email",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  legalPrivacy: "/legal/privacy",
  legalConsent: "/legal/consent",
  legalAgreement: "/legal/agreement",
  legalCookies: "/legal/cookies",
  profile: "/profile",
  seasonSetup: "/season-setup",
  seasonOverview: "/season-overview",
  practiceSetup: "/practice-setup",
  practiceResults: "/practice-results",
  qualifying: "/qualifying",
  qualifyingResults: "/qualifying-results",
  raceGrid: "/race-grid",
  raceResults: "/race-results",
  championshipSummary: "/championship-summary",
  budgetHistory: "/budget-history",
  liveRace: "/stage/:id/live"
} as const;

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES];
