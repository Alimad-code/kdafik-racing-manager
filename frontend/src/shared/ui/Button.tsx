import type { ButtonHTMLAttributes, ReactNode } from "react";
import { getButtonClassName, type ButtonVariant } from "@/shared/ui/buttonStyles";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: ButtonVariant;
};

export function Button({
  children,
  className,
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button className={getButtonClassName(variant, className)} type={type} {...props}>
      {children}
    </button>
  );
}
