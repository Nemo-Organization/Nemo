import { Suspense } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { routing } from '@/i18n/routing';
import StoreProvider from '@/store/store-provider';
import '../globals.css';
import { Toaster } from '@/components/ui/sonner';
import { fontSans } from '@/config/fonts';
import { getLocale } from 'next-intl/server';
import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('common');

  return {
    title: {
      default: t('app.name'),
      template: `%s | ${t('app.name')}`,
    },
    description: t('app.description'),
  };
}

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  return (
    <html lang={locale} className={fontSans.variable}>
      <body className="font-sans antialiased">
        <NextIntlClientProvider>
          <Suspense fallback={null}>
            <StoreProvider>{children}</StoreProvider>
            <Toaster />
          </Suspense>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}