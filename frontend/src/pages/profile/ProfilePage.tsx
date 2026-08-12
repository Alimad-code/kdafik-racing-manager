import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError } from "@/features/season/api/apiClient";
import {
  acceptLegalDocuments,
  changePassword,
  deleteAccount,
  exportMyData,
  getLegalAcceptanceStatus,
  getProfile,
  updateMe
} from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/model/useAuthStore";
import type {
  LegalAcceptanceStatusReadDto,
  ProfileReadDto
} from "@/features/season/api/backendDtos";
import type { User } from "@/entities";
import { ROUTES } from "@/shared/constants/routes";
import { Button, Modal, PageHeader, PageSurface, SectionHeader } from "@/shared/ui";
import { useNavigate } from "react-router-dom";

const inputClass =
  "min-h-10 w-full border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary";

function getProfileError(error: unknown, fallback: string) {
  if (!(error instanceof ApiError)) return fallback;
  if (error.code === "DISPLAY_NAME_ALREADY_REGISTERED") return "Это имя уже занято";
  if (error.code === "INVALID_CREDENTIALS") return "Текущий пароль указан неверно";
  if (error.code === "VALIDATION_ERROR" && error.details.field === "newPassword") {
    return "Новый пароль должен отличаться от текущего";
  }
  if (error.code === "VALIDATION_ERROR") return "Проверьте данные формы";
  return error.message || fallback;
}

export function ProfilePage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);
  const logout = useAuthStore((state) => state.logout);
  const [profile, setProfile] = useState<ProfileReadDto | null>(null);
  const [displayName, setDisplayName] = useState(user?.displayName ?? "");
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [legalStatuses, setLegalStatuses] = useState<LegalAcceptanceStatusReadDto[]>([]);
  const [legalError, setLegalError] = useState("");
  const [legalLoading, setLegalLoading] = useState(false);
  const [legalChecks, setLegalChecks] = useState<Record<string, boolean>>({});
  const [exportLoading, setExportLoading] = useState(false);
  const [exportMessage, setExportMessage] = useState("");
  const exportUrlRef = useRef<string | null>(null);
  const exportRevokeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    const profileRequest = getProfile();
    const legalRequest = getLegalAcceptanceStatus();
    void profileRequest
      .then((data) => {
        if (!active) return;
        setProfile(data);
        setDisplayName(data.displayName);
      })
      .catch((error: unknown) => {
        if (active) setProfileError(getProfileError(error, "Не удалось загрузить профиль"));
      });
    void legalRequest
      .then((statuses) => {
        if (active) setLegalStatuses(statuses);
      })
      .catch(() => {
        if (active) setLegalError("Не удалось загрузить актуальные документы. Попробуйте ещё раз.");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(
    () => () => {
      if (exportRevokeTimerRef.current !== null) {
        window.clearTimeout(exportRevokeTimerRef.current);
      }
      if (exportUrlRef.current) {
        URL.revokeObjectURL(exportUrlRef.current);
      }
    },
    []
  );

  async function reloadLegalStatuses() {
    setLegalLoading(true);
    setLegalError("");
    try {
      setLegalStatuses(await getLegalAcceptanceStatus());
    } catch {
      setLegalError("Не удалось загрузить актуальные документы. Попробуйте ещё раз.");
    } finally {
      setLegalLoading(false);
    }
  }

  async function handleExport() {
    setExportLoading(true);
    setExportMessage("");
    try {
      const { blob, contentDisposition } = await exportMyData();
      const match = /filename="?([^";]+)"?/i.exec(contentDisposition ?? "");
      const filename =
        match?.[1]?.replace(/[^a-zA-Z0-9._-]/g, "_") || "kdafik-racing-manager-data.json";
      if (exportRevokeTimerRef.current !== null) {
        window.clearTimeout(exportRevokeTimerRef.current);
      }
      if (exportUrlRef.current) {
        URL.revokeObjectURL(exportUrlRef.current);
      }
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.style.display = "none";
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      exportUrlRef.current = url;
      exportRevokeTimerRef.current = window.setTimeout(() => {
        if (exportUrlRef.current === url) {
          URL.revokeObjectURL(url);
          exportUrlRef.current = null;
        }
        exportRevokeTimerRef.current = null;
      }, 0);
      setExportMessage("Выгрузка подготовлена.");
    } catch {
      setExportMessage("Не удалось подготовить выгрузку. Попробуйте ещё раз.");
    } finally {
      setExportLoading(false);
    }
  }

  async function handleLegalAcceptances() {
    const current = legalStatuses;
    if (current.some((item) => !item.accepted && !legalChecks[item.document.kind])) {
      setLegalError("Подтвердите каждый новый документ.");
      return;
    }
    setLegalLoading(true);
    setLegalError("");
    try {
      await acceptLegalDocuments(
        current.map((item) => ({
          kind: item.document.kind,
          version: item.document.version,
          accepted: item.accepted || legalChecks[item.document.kind] === true
        }))
      );
      setLegalStatuses((items) => items.map((item) => ({ ...item, accepted: true })));
      setLegalChecks({});
    } catch (error) {
      setLegalError(getProfileError(error, "Не удалось сохранить подтверждения."));
    } finally {
      setLegalLoading(false);
    }
  }

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextName = displayName.trim();
    setProfileError("");
    setProfileSuccess("");
    if (!nextName) {
      setProfileError("Введите имя профиля");
      return;
    }
    setProfileLoading(true);
    try {
      const updated = await updateMe({ displayName: nextName });
      const mappedUser: User = {
        id: updated.id,
        displayName: updated.displayName,
        email: updated.email,
        role: updated.role,
        selectedTeamId: user?.selectedTeamId ?? null,
        activeSeasonId: updated.activeSeasonId
      };
      updateUser(mappedUser);
      setDisplayName(updated.displayName);
      setProfile((current) => (current ? { ...current, ...updated } : current));
      setProfileSuccess("Имя профиля обновлено");
    } catch (error) {
      setProfileError(getProfileError(error, "Не удалось сохранить изменения"));
    } finally {
      setProfileLoading(false);
    }
  }

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");
    if (newPassword.length < 8) {
      setPasswordError("Новый пароль должен содержать минимум 8 символов");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Пароли не совпадают");
      return;
    }
    setPasswordLoading(true);
    try {
      await changePassword({ currentPassword, newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordSuccess("Пароль успешно изменён");
    } catch (error) {
      setPasswordError(getProfileError(error, "Не удалось изменить пароль"));
    } finally {
      setPasswordLoading(false);
    }
  }

  async function handleDeleteAccount() {
    if (!deletePassword) {
      setDeleteError("Введите текущий пароль");
      return;
    }
    setDeleteError("");
    setDeleteLoading(true);
    try {
      await deleteAccount({ currentPassword: deletePassword });
      try {
        await logout();
      } catch {
        // logout очищает локальную сессию в finally даже если backend недоступен.
      }
      navigate(ROUTES.login, { replace: true });
    } catch (error) {
      setDeleteError(getProfileError(error, "Не удалось удалить аккаунт"));
      setDeleteLoading(false);
    }
  }

  return (
    <PageSurface className="mx-auto w-full max-w-4xl">
      <PageHeader title="Профиль" description="Данные аккаунта и настройки безопасности." />

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="race-panel p-4 sm:p-5">
          <SectionHeader title="Аккаунт" description="Имя отображается в шапке приложения." />
          <form className="mt-5 grid gap-4" onSubmit={handleProfileSubmit}>
            <label className="grid gap-2 text-sm" htmlFor="profile-display-name">
              <span className="metadata-label">Имя профиля</span>
              <input
                id="profile-display-name"
                className={inputClass}
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                autoComplete="nickname"
              />
              {profileError ? <span className="text-sm text-danger">{profileError}</span> : null}
            </label>
            <label className="grid gap-2 text-sm" htmlFor="profile-email">
              <span className="metadata-label">Email</span>
              <input
                id="profile-email"
                className={inputClass}
                value={profile?.email ?? user?.email ?? "—"}
                readOnly
              />
            </label>
            {profileSuccess ? <p className="text-sm text-success">{profileSuccess}</p> : null}
            <Button type="submit" disabled={profileLoading} className="w-fit">
              {profileLoading ? "Сохранение..." : "Сохранить имя"}
            </Button>
          </form>
        </section>

        <section className="race-panel p-4 sm:p-5">
          <SectionHeader title="Безопасность" description="Смена пароля требует текущий пароль." />
          <form className="mt-5 grid gap-4" onSubmit={handlePasswordSubmit}>
            <label className="grid gap-2 text-sm" htmlFor="profile-current-password">
              <span className="metadata-label">Текущий пароль</span>
              <input
                id="profile-current-password"
                className={inputClass}
                type="password"
                maxLength={128}
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                autoComplete="current-password"
              />
            </label>
            <label className="grid gap-2 text-sm" htmlFor="profile-new-password">
              <span className="metadata-label">Новый пароль</span>
              <input
                id="profile-new-password"
                className={inputClass}
                type="password"
                maxLength={128}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                autoComplete="new-password"
              />
            </label>
            <label className="grid gap-2 text-sm" htmlFor="profile-confirm-password">
              <span className="metadata-label">Повторите новый пароль</span>
              <input
                id="profile-confirm-password"
                className={inputClass}
                type="password"
                maxLength={128}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
              />
            </label>
            {passwordError ? <p className="text-sm text-danger">{passwordError}</p> : null}
            {passwordSuccess ? <p className="text-sm text-success">{passwordSuccess}</p> : null}
            <Button type="submit" disabled={passwordLoading} variant="secondary" className="w-fit">
              {passwordLoading ? "Сохранение..." : "Изменить пароль"}
            </Button>
          </form>
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="race-panel p-4 sm:p-5">
          <SectionHeader
            title="Ваши данные"
            description="Можно скачать данные, связанные с аккаунтом."
          />
          <Button
            className="mt-5"
            type="button"
            disabled={exportLoading}
            onClick={() => void handleExport()}
          >
            {exportLoading ? "Готовим выгрузку..." : "Скачать мои данные"}
          </Button>
          {exportMessage ? (
            <p className="mt-3 text-sm text-muted-foreground" role="status">
              {exportMessage}
            </p>
          ) : null}
        </section>

        <section className="race-panel p-4 sm:p-5">
          <SectionHeader
            title="Документы"
            description="Актуальные версии условий использования аккаунта."
          />
          {legalStatuses.length === 0 ? (
            <div className="mt-5 grid gap-3">
              <p className="text-sm text-muted-foreground">
                {legalError || "Документы пока не удалось загрузить."}
              </p>
              <Button
                className="w-fit"
                type="button"
                variant="secondary"
                disabled={legalLoading}
                onClick={() => void reloadLegalStatuses()}
              >
                {legalLoading ? "Загружаем..." : "Повторить загрузку"}
              </Button>
            </div>
          ) : null}
          <div className="mt-5 grid gap-3">
            {legalStatuses.map((item) =>
              item.accepted ? (
                <p key={item.document.kind} className="text-sm text-muted-foreground">
                  Принято: {item.document.title} (версия {item.document.version})
                </p>
              ) : (
                <label key={item.document.kind} className="flex items-start gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={legalChecks[item.document.kind] ?? false}
                    onChange={(event) =>
                      setLegalChecks((current) => ({
                        ...current,
                        [item.document.kind]: event.target.checked
                      }))
                    }
                  />
                  <span>
                    Принимаю{" "}
                    <a
                      className="underline"
                      href={item.document.publicPath}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {item.document.title} (версия {item.document.version})
                    </a>
                  </span>
                </label>
              )
            )}
          </div>
          {legalStatuses.some((item) => !item.accepted) ? (
            <>
              <Button
                className="mt-5"
                type="button"
                disabled={legalLoading}
                onClick={() => void handleLegalAcceptances()}
              >
                {legalLoading ? "Сохраняем..." : "Подтвердить новые версии"}
              </Button>
              {legalError ? (
                <p className="mt-3 text-sm text-danger" role="alert">
                  {legalError}
                </p>
              ) : null}
            </>
          ) : null}
        </section>
      </div>

      <section className="race-panel border-danger/50 p-4 sm:p-5">
        <SectionHeader
          title="Удаление аккаунта"
          description="Аккаунт и связанные данные будут удалены без возможности восстановления."
        />
        <Button
          className="mt-5"
          variant="danger"
          onClick={() => {
            setDeleteError("");
            setDeletePassword("");
            setIsDeleteOpen(true);
          }}
        >
          Удалить аккаунт
        </Button>
      </section>

      <Modal
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        title="Удалить аккаунт?"
        description="Это действие нельзя отменить. Для подтверждения введите текущий пароль."
        confirmLabel="Удалить аккаунт"
        onConfirm={handleDeleteAccount}
        isLoading={deleteLoading}
      >
        <label className="grid gap-2 text-sm" htmlFor="delete-account-password">
          <span className="metadata-label">Текущий пароль</span>
          <input
            id="delete-account-password"
            className={inputClass}
            type="password"
            maxLength={128}
            value={deletePassword}
            onChange={(event) => setDeletePassword(event.target.value)}
            autoComplete="current-password"
          />
          {deleteError ? <span className="text-sm text-danger">{deleteError}</span> : null}
        </label>
      </Modal>
    </PageSurface>
  );
}
