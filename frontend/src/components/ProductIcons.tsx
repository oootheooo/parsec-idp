import type { SVGProps } from "react";

export type ProductIconName =
  | "overview"
  | "documents"
  | "processors"
  | "workflows"
  | "api"
  | "settings"
  | "upload"
  | "logout"
  | "chevron";

/**
 * Parsec's product icons use one geometric grammar: open corners, one rounded
 * detail, and a consistent 1.45px stroke. These are intentionally owned SVGs,
 * not a mixed collection of decorative library glyphs.
 */
export function ProductIcon({
  name,
  size = 18,
  ...props
}: SVGProps<SVGSVGElement> & { name: ProductIconName; size?: number }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.45,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  return (
    <svg
      viewBox="0 0 20 20"
      width={size}
      height={size}
      aria-hidden="true"
      data-parse-icon={name}
      {...props}
    >
      <g {...common}>
        {name === "overview" && (
          <>
            <path d="M3.25 15.75V9.5M8 15.75V5.25M12.75 15.75v-3.5M17 15.75V7.5" />
            <path d="M2.75 15.75h14.5" />
          </>
        )}
        {name === "documents" && (
          <>
            <path d="M5.25 2.75h6.1l3.4 3.4v11.1h-9.5z" />
            <path d="M11.25 2.75v3.5h3.5M7.75 10h4.5M7.75 13h4.5" />
          </>
        )}
        {name === "processors" && (
          <>
            <path d="M3 5.25h8.25M14.75 5.25H17M3 10h2.25M8.75 10H17M3 14.75h6.25M12.75 14.75H17" />
            <circle cx="13" cy="5.25" r="1.75" />
            <circle cx="7" cy="10" r="1.75" />
            <circle cx="11" cy="14.75" r="1.75" />
          </>
        )}
        {name === "workflows" && (
          <>
            <circle cx="5" cy="4.25" r="1.75" />
            <circle cx="15" cy="10" r="1.75" />
            <circle cx="5" cy="15.75" r="1.75" />
            <path d="M6.75 4.25h1.5A2.75 2.75 0 0 1 11 7v.25A2.75 2.75 0 0 0 13.75 10M6.75 15.75h1.5A2.75 2.75 0 0 0 11 13v-.25A2.75 2.75 0 0 1 13.75 10" />
          </>
        )}
        {name === "api" && (
          <>
            <path d="M7 3.5 3.75 10 7 16.5M13 3.5 16.25 10 13 16.5M11 6.25 9 13.75" />
          </>
        )}
        {name === "settings" && (
          <>
            <circle cx="10" cy="10" r="2.35" />
            <path d="M7.9 3.6 8.5 2h3l.6 1.6 1.5.85 1.7-.25 1.5 2.6-1.1 1.35v1.7l1.1 1.35-1.5 2.6-1.7-.25-1.5.85-.6 1.6h-3l-.6-1.6-1.5-.85-1.7.25-1.5-2.6 1.1-1.35v-1.7L3.2 6.8l1.5-2.6 1.7.25z" />
          </>
        )}
        {name === "upload" && (
          <>
            <path d="M10 13.5V3.75M6.5 7.25 10 3.75l3.5 3.5" />
            <path d="M4 11.75v4.5h12v-4.5" />
          </>
        )}
        {name === "logout" && (
          <>
            <path d="M9 3.25H4.25v13.5H9M11.5 6.5 15 10l-3.5 3.5M7.5 10H15" />
          </>
        )}
        {name === "chevron" && <path d="m7 8 3 3 3-3" />}
      </g>
    </svg>
  );
}
