/** IANA timezone from the browser (client-only). */
export function getClientTimeZone(): string {
  if (typeof window === "undefined") return "UTC";
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

/** SQLite / API datetimes are UTC without a suffix. */
export function parseApiDateTime(value: string): Date | null {
  const trimmed = value.trim();
  if (!trimmed) return null;

  if (trimmed.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(trimmed)) {
    const date = new Date(trimmed);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  const iso = trimmed.includes("T")
    ? trimmed
    : trimmed.replace(" ", "T");
  const date = new Date(`${iso}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTimeInZone(
  value: string,
  timeZone: string
): string {
  const date = parseApiDateTime(value);
  if (!date) return value || "—";

  return date.toLocaleString(undefined, {
    timeZone,
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export function formatTimeZoneAbbrev(timeZone: string): string {
  try {
    const parts = new Intl.DateTimeFormat(undefined, {
      timeZone,
      timeZoneName: "short",
    }).formatToParts(new Date());
    return parts.find((p) => p.type === "timeZoneName")?.value ?? timeZone;
  } catch {
    return timeZone;
  }
}
