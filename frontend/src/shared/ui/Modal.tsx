import * as React from "react";
import { createPortal } from "react-dom";
import { cn } from "@/shared/lib/utils";
import { Button } from "./Button";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  isLoading?: boolean;
  children?: React.ReactNode;
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  confirmLabel = "Подтвердить",
  cancelLabel = "Отмена",
  onConfirm,
  isLoading = false,
  children
}: ModalProps) {
  // Close on ESC key
  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleEsc);
    }
    return () => {
      window.removeEventListener("keydown", handleEsc);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Body */}
      <div
        className={cn(
          "race-panel relative z-10 w-full max-w-md overflow-hidden bg-background shadow-2xl animate-in fade-in zoom-in duration-200"
        )}
      >
        <div className="p-6">
          <h2 className="text-xl font-black uppercase tracking-tight text-foreground">{title}</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{description}</p>

          {children ? <div className="mt-5">{children}</div> : null}

          <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button disabled={isLoading} variant="secondary" onClick={onClose}>
              {cancelLabel}
            </Button>
            <Button disabled={isLoading} onClick={onConfirm}>
              {isLoading ? "Обработка..." : confirmLabel}
            </Button>
          </div>
        </div>

        {/* Decorative elements to match site style */}
        <div className="absolute top-0 right-0 h-1 w-24 bg-primary" />
        <div className="absolute bottom-0 left-0 h-1 w-12 bg-muted" />
      </div>
    </div>,
    document.body
  );
}
