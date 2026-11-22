import { namespaces } from '../namespaces.generated';

export async function loadMessages(locale: string) {
  const entries = await Promise.all(
    namespaces.map(async (ns) => {
      const mod = await import(`../../i18n/messages/${locale}/${ns}.json`);
      return [ns, mod.default] as const;
    }),
  );
  return Object.fromEntries(entries);
}