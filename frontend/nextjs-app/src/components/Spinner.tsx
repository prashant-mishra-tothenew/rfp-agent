export function Spinner({
  size = "md",
  variant = "light",
}: {
  size?: "sm" | "md" | "lg";
  variant?: "light" | "dark";
}) {
  const classes = [
    "spinner",
    size === "lg" ? "spinner-lg" : "",
    variant === "dark" ? "spinner-dark" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return <span className={classes} aria-hidden="true" />;
}

export function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
