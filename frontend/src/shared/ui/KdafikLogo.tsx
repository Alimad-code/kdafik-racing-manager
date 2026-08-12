import type { ComponentPropsWithoutRef } from "react";

type KdafikLogoProps = ComponentPropsWithoutRef<"img">;

export function KdafikLogo({ alt = "", ...props }: KdafikLogoProps) {
  return (
    <img src="/Kdafik_Racing_logo.svg" alt={alt} aria-hidden={alt ? undefined : true} {...props} />
  );
}
