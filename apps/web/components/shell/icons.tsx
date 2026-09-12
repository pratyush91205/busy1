/**
 * Six 16px glyphs, drawn here rather than pulled from an icon package.
 *
 * The navigation needs exactly these, they never change, and a dependency
 * that ships a thousand icons to render six is a dependency to keep current
 * for no reason.
 */
type IconProps = { className?: string };

function Glyph({
  children,
  className,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={className ?? "size-4 shrink-0"}
    >
      {children}
    </svg>
  );
}

export function DashboardIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </Glyph>
  );
}

export function VehiclesIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <path d="M1.5 11V4.5h8V11" />
      <path d="M9.5 7h2.6l2.4 2.4V11" />
      <circle cx="4.5" cy="11.5" r="1.5" />
      <circle cx="11.5" cy="11.5" r="1.5" />
      <path d="M6 11.5h4" />
    </Glyph>
  );
}

export function ServicesIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <rect x="3" y="2" width="10" height="12" rx="1.5" />
      <path d="M5.5 5.5h5M5.5 8h5M5.5 10.5h3" />
    </Glyph>
  );
}

export function AlertsIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <path d="M8 2.2 14.5 13.3h-13L8 2.2Z" />
      <path d="M8 6.3v3" />
      <path d="M8 11.2h.01" />
    </Glyph>
  );
}

export function ReportsIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <path d="M9 1.8H4.5A1.5 1.5 0 0 0 3 3.3v9.4a1.5 1.5 0 0 0 1.5 1.5h7a1.5 1.5 0 0 0 1.5-1.5V5.8L9 1.8Z" />
      <path d="M9 1.8v4h4" />
      <path d="M5.8 9h4.4M5.8 11.3h3" />
    </Glyph>
  );
}

export function WorkIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <rect x="2.5" y="4" width="11" height="9.5" rx="1.5" />
      <path d="M5.8 4V2.8a1 1 0 0 1 1-1h2.4a1 1 0 0 1 1 1V4" />
      <path d="m6 8.8 1.5 1.5L10.3 7" />
    </Glyph>
  );
}
