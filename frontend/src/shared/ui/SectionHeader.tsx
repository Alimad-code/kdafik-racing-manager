type SectionHeaderProps = {
  title: string;
  description?: string;
};

export function SectionHeader({ title, description }: SectionHeaderProps) {
  return (
    <div className="flex min-w-0 items-end justify-between gap-3 border-b border-border pb-2.5 sm:gap-4 sm:pb-3">
      <div className="min-w-0">
        <h2 className="text-xs font-black uppercase tracking-[0.16em] text-foreground sm:text-sm sm:tracking-[0.18em]">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 max-w-full text-sm leading-5 text-muted-foreground sm:leading-6">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  );
}
