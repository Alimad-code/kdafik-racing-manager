import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";

type PageSurfaceProps = {
  children: ReactNode;
  className?: string;
};

export function PageSurface({ children, className }: PageSurfaceProps) {
  return <div className={cn("space-y-4 sm:space-y-6", className)}>{children}</div>;
}
