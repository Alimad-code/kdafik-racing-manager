import type { CSSProperties, SVGProps } from "react";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";

type TeamIconProps = Omit<SVGProps<SVGSVGElement>, "color"> & {
  teamId?: string | null;
  color?: string | null;
  label?: string;
};

const KNOWN_TEAM_IDS = new Set([
  "team-apex",
  "team-velocity",
  "team-nordline",
  "team-orion",
  "team-titan",
  "team-vector",
  "team-quantum",
  "team-zenith",
  "team-eclipse",
  "team-nebula"
]);

function TeamMark({ teamId }: { teamId: string }) {
  switch (teamId) {
    case "team-apex":
      return (
        <path
          d="M3 18 8 6l4 8 3-5 6 9H3Zm5-4h8"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="miter"
        />
      );
    case "team-velocity":
      return (
        <path
          d="m3 6 7 12 4-7 2 4 5-9M7 6h10"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="square"
          strokeLinejoin="miter"
        />
      );
    case "team-nordline":
      return (
        <path
          d="M12 3v14m0-14 5 6-5-2-5 2 5-6ZM4 20h16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="miter"
        />
      );
    case "team-orion":
      return (
        <>
          <ellipse
            cx="12"
            cy="12"
            rx="9"
            ry="4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            transform="rotate(-28 12 12)"
          />
          <path
            d="m12 8 .9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9L12 8Z"
            fill="currentColor"
          />
        </>
      );
    case "team-titan":
      return (
        <path
          d="M5 4h14v8c0 4.7-3.1 7.4-7 8-3.9-.6-7-3.3-7-8V4Zm3 3h8v3h-2v6h-4v-6H8V7Z"
          fill="currentColor"
        />
      );
    case "team-vector":
      return (
        <path
          d="m4 18 3-7 3 7m2 0 3-11 3 11m2 0 1.5-5 1.5 5M3 20h18"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="square"
          strokeLinejoin="miter"
        />
      );
    case "team-quantum":
      return (
        <>
          <path
            d="M18.6 7.2A8 8 0 1 0 19 16.4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="square"
          />
          <circle cx="12" cy="12" r="2.4" fill="currentColor" />
        </>
      );
    case "team-zenith":
      return (
        <>
          <path
            d="M4 19h16M6 19l6-8 6 8"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="miter"
          />
          <path d="M9 8a3 3 0 0 1 6 0v1H9V8Z" fill="currentColor" />
          <path
            d="M12 3v2m-5 1.2 1.5 1m8.5-1-1.5 1"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="square"
          />
        </>
      );
    case "team-eclipse":
      return (
        <>
          <circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M14.5 5.5a7 7 0 1 1 0 13 5.4 5.4 0 0 0 0-13Z" fill="currentColor" />
        </>
      );
    case "team-nebula":
      return (
        <path
          d="M12 12c3.7-5.3 8.3-3.5 6.6.5-1.7 4-6.6 4.1-6.6-.5Zm0 0c2.8 5.9-1.5 8.9-4.2 5.5-2.7-3.4-.6-7.8 4.2-5.5Zm0 0C5.5 11.4 5.2 6.1 9.3 6c4.1-.1 6 4.4 2.7 6Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      );
    default:
      return (
        <path
          d="M4 16h3l2-8 3 8 3-8 2 8h3M5 20h14"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="square"
          strokeLinejoin="miter"
        />
      );
  }
}

export function TeamIcon({ teamId, color, label, className, style, ...props }: TeamIconProps) {
  const resolvedTeamId = teamId && KNOWN_TEAM_IDS.has(teamId) ? teamId : "fallback";
  const mergedStyle = {
    color: getReadableTeamAccent(color),
    ...style
  } as CSSProperties;

  return (
    <svg
      {...props}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      className={className}
      data-team-icon={resolvedTeamId}
      focusable="false"
      role={label ? "img" : undefined}
      style={mergedStyle}
      viewBox="0 0 24 24"
    >
      <TeamMark teamId={resolvedTeamId} />
    </svg>
  );
}
