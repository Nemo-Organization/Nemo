export function formatVnd(value: number, locale: string) {
  return new Intl.NumberFormat(locale, { style: "currency", currency: "VND" }).format(value);
}
