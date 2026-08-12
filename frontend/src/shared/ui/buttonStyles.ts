import { cn } from "@/shared/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const buttonVariantClassName: Record<ButtonVariant, string> = {
  primary: "border-primary bg-primary text-primary-foreground hover:bg-primary/85",
  secondary: "border-border bg-secondary text-foreground hover:border-line-strong hover:bg-muted",
  ghost:
    "border-transparent bg-transparent text-muted-foreground hover:border-border hover:text-foreground",
  danger: "border-danger bg-danger text-danger-foreground hover:bg-danger/85"
};

export function getButtonClassName(variant: ButtonVariant = "primary", className?: string) {
  return cn(
    "inline-flex min-h-9 items-center justify-center whitespace-nowrap border px-3 py-2 text-xs font-black uppercase tracking-[0.12em] transition sm:min-h-10 sm:px-4 sm:py-2.5 sm:text-sm sm:tracking-[0.14em]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:cursor-not-allowed disabled:border-border disabled:bg-secondary disabled:text-muted-foreground disabled:opacity-70",
    buttonVariantClassName[variant],
    className
  );
}
