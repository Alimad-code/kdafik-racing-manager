import type { ReactNode } from "react";

type ActionPanelProps = {
  title: string;
  description: string;
  children?: ReactNode;
};

export function ActionPanel({ title, description, children }: ActionPanelProps) {
  return (
    <section className="border border-primary/30 bg-primary/10 p-4 shadow-insetLine sm:p-5">
      <p className="text-[11px] font-black uppercase tracking-[0.18em] text-primary sm:text-xs sm:tracking-[0.2em]">
        {title}
      </p>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-foreground sm:mt-3">{description}</p>
      {children ? (
        <div className="mt-4 flex flex-wrap gap-2 sm:mt-5 sm:gap-3">{children}</div>
      ) : null}
    </section>
  );
}
