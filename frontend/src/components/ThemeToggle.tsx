import { useTheme } from "../hooks/useTheme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={theme === "dark"}
      aria-label="Dark mode"
      title="Dark mode"
      className="rounded-md border border-rule px-2.5 py-1 text-sm text-soft hover:bg-panel2 hover:text-ink"
    >
      {theme === "dark" ? "☾" : "☀"}
    </button>
  );
}
