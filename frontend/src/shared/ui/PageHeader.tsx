import type { ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  eyebrow?: ReactNode;
  description?: string;
  actions?: ReactNode;
  meta?: ReactNode;
};

export function PageHeader({ title, eyebrow, description, actions, meta }: PageHeaderProps) {
  return (
    <header className="border-b border-border pb-4 sm:pb-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 max-w-3xl">
          {eyebrow ? (
            <p className="mb-2 font-mono text-[11px] font-black uppercase tracking-[0.24em] text-primary">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="page-title-shadow text-3xl font-black uppercase leading-none tracking-tight text-foreground sm:text-4xl lg:text-[3.25rem]">
            {title}
          </h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground sm:mt-3">
              {description}
            </p>
          )}
        </div>
        {actions ? (
          <div className="flex min-w-0 flex-wrap items-center gap-2 sm:gap-3 lg:shrink-0 lg:justify-end lg:pt-16">
            {actions}
          </div>
        ) : null}
      </div>
      {meta ? <div className="mt-3 flex flex-wrap gap-2 sm:mt-4">{meta}</div> : null}
    </header>
  );
}
