import type { ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accentink hover:opacity-90",
  secondary: "border border-rule bg-panel text-ink hover:bg-panel2",
  ghost: "text-soft hover:bg-panel2 hover:text-ink",
};

export function Button({
  variant = "secondary",
  children,
  onClick,
  disabled,
  ariaLabel,
  title,
}: {
  variant?: Variant;
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  ariaLabel?: string;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      title={title}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]}`}
    >
      {children}
    </button>
  );
}
