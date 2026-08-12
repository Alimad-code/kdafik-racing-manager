import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/app/layout/AppShell";
import { ProtectedRoute } from "@/app/router/ProtectedRoute";
import { ROUTES } from "@/shared/constants/routes";
import { ChampionshipSummaryPage } from "@/pages/championship-summary/ChampionshipSummaryPage";
import { HomePage } from "@/pages/home/HomePage";
import { LoginPage } from "@/pages/login/LoginPage";
import { LiveRacePage } from "@/pages/live-race/LiveRacePage";
import { PracticeResultsPage } from "@/pages/practice-results/PracticeResultsPage";
import { PracticeSetupPage } from "@/pages/practice-setup/PracticeSetupPage";
import { QualifyingPage } from "@/pages/qualifying/QualifyingPage";
import { QualifyingResultsPage } from "@/pages/qualifying-results/QualifyingResultsPage";
import { RaceGridPage } from "@/pages/race-grid/RaceGridPage";
import { RaceResultsPage } from "@/pages/race-results/RaceResultsPage";
import { SeasonOverviewPage } from "@/pages/season-overview/SeasonOverviewPage";
import { SeasonSetupPage } from "@/pages/season-setup/SeasonSetupPage";
import { BudgetHistoryPage } from "@/pages/budget-history/BudgetHistoryPage";
import { ProfilePage } from "@/pages/profile/ProfilePage";
import { VerifyEmailPage } from "@/pages/auth-actions/VerifyEmailPage";
import { ForgotPasswordPage } from "@/pages/auth-actions/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth-actions/ResetPasswordPage";
import { LegalDocumentPage } from "@/pages/legal/LegalDocumentPage";

export const router = createBrowserRouter([
  {
    path: ROUTES.login,
    element: <LoginPage />
  },
  { path: ROUTES.verifyEmail, element: <VerifyEmailPage /> },
  { path: ROUTES.forgotPassword, element: <ForgotPasswordPage /> },
  { path: ROUTES.resetPassword, element: <ResetPasswordPage /> },
  { path: ROUTES.legalPrivacy, element: <LegalDocumentPage kind="privacy_policy" /> },
  { path: ROUTES.legalConsent, element: <LegalDocumentPage kind="personal_data_consent" /> },
  { path: ROUTES.legalAgreement, element: <LegalDocumentPage kind="user_agreement" /> },
  { path: ROUTES.legalCookies, element: <LegalDocumentPage kind="cookie_storage_notice" /> },
  {
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <HomePage />
      },
      {
        path: ROUTES.seasonSetup,
        element: <SeasonSetupPage />
      },
      {
        path: ROUTES.seasonOverview,
        element: <SeasonOverviewPage />
      },
      {
        path: ROUTES.practiceSetup,
        element: <PracticeSetupPage />
      },
      {
        path: ROUTES.practiceResults,
        element: <PracticeResultsPage />
      },
      {
        path: ROUTES.qualifying,
        element: <QualifyingPage />
      },
      {
        path: ROUTES.qualifyingResults,
        element: <QualifyingResultsPage />
      },
      {
        path: ROUTES.raceGrid,
        element: <RaceGridPage />
      },
      {
        path: ROUTES.raceResults,
        element: <RaceResultsPage />
      },
      {
        path: "/stage/:id/results",
        element: <RaceResultsPage />
      },
      {
        path: ROUTES.championshipSummary,
        element: <ChampionshipSummaryPage />
      },
      {
        path: ROUTES.liveRace,
        element: <LiveRacePage />
      },
      {
        path: ROUTES.budgetHistory,
        element: <BudgetHistoryPage />
      },
      {
        path: ROUTES.profile,
        element: <ProfilePage />
      }
    ]
  },
  {
    path: "*",
    element: <Navigate to={ROUTES.home} replace />
  }
]);
