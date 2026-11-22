import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const messagesDir = path.join(root, 'src/i18n/messages');
const SOURCE_LOCALE = 'en';
const strict = process.argv.includes('--strict');

const warnings = [];

const listNamespaces = (locale) => {
  const dir = path.join(messagesDir, locale);
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .map((f) => f.slice(0, -'.json'.length))
    .sort();
};

// { a: { b: 1 }, c: 2 } -> ['a.b', 'c']
const flattenKeys = (obj, prefix = '') =>
  Object.entries(obj).flatMap(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    return v && typeof v === 'object' && !Array.isArray(v)
      ? flattenKeys(v, key)
      : [key];
  });

const readKeys = (locale, ns) => {
  const file = path.join(messagesDir, locale, `${ns}.json`);
  try {
    return new Set(flattenKeys(JSON.parse(readFileSync(file, 'utf8'))));
  } catch (e) {
    warnings.push(`[${locale}] ${ns}.json: JSON không hợp lệ (${e.message})`);
    return null;
  }
};

const namespaces = listNamespaces(SOURCE_LOCALE);
if (namespaces.length === 0) {
  console.error(`[i18n] Cannot find any message files in messages/${SOURCE_LOCALE}/`);
  process.exit(1);
}

const locales = readdirSync(messagesDir, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => d.name)
  .filter((l) => l !== SOURCE_LOCALE);

for (const locale of locales) {
  const target = listNamespaces(locale);

  for (const ns of namespaces) {
    if (!target.includes(ns)) {
      warnings.push(`[${locale}] thiếu file: ${ns}.json`);
      continue;
    }
    const sourceKeys = readKeys(SOURCE_LOCALE, ns);
    const targetKeys = readKeys(locale, ns);
    if (!sourceKeys || !targetKeys) continue;

    for (const key of sourceKeys) {
      if (!targetKeys.has(key)) warnings.push(`[${locale}] ${ns}.json thiếu key: ${key}`);
    }
    for (const key of targetKeys) {
      if (!sourceKeys.has(key)) warnings.push(`[${locale}] ${ns}.json dư key (không có trong ${SOURCE_LOCALE}): ${key}`);
    }
  }

  for (const ns of target) {
    if (!namespaces.includes(ns)) {
      warnings.push(`[${locale}] dư file (không có trong ${SOURCE_LOCALE}): ${ns}.json`);
    }
  }
}

const output = `
export const namespaces = ${JSON.stringify(namespaces)} as const;
export type Namespace = (typeof namespaces)[number];
`;
writeFileSync(path.join(root, 'src/i18n/namespaces.generated.ts'), output);
console.log(`[i18n] ${namespaces.length} namespaces: ${namespaces.join(', ')}`);

if (warnings.length > 0) {
  console.warn(`\n[i18n] ${warnings.length} warnings:`);
  for (const w of warnings) console.warn(`  - ${w}`);
  if (strict) {
    console.error('\n[i18n] Stopping due to warnings.');
    process.exit(1);
  }
}