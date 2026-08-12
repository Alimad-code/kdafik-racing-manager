import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { Link } from "react-router-dom";
import { getButtonClassName, type ButtonVariant } from "@/shared/ui/buttonStyles";

type ButtonLinkProps = ComponentPropsWithoutRef<typeof Link> & {
  children: ReactNode;
  variant?: ButtonVariant;
};

export function ButtonLink({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonLinkProps) {
  return (
    <Link className={getButtonClassName(variant, className)} {...props}>
      {children}
    </Link>
  );
}
