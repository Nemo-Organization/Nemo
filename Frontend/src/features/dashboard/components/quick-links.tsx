import { useTranslations } from "next-intl";
import {
  ArrowRightIcon,
  PlugsConnectedIcon,
  TerminalWindowIcon,
  UsersThreeIcon,
} from "@phosphor-icons/react/ssr";

import { Link } from "@/i18n/navigation";
import type { QuickLink, QuickLinkKey } from "../types/dashboard.types";

const LINK_VISUALS: Record<
  QuickLinkKey,
  {
    icon: typeof PlugsConnectedIcon;
    iconClass: string;
  }
> = {
  endpoints: {
    icon: PlugsConnectedIcon,
    iconClass: "text-teal-600 dark:text-teal-400",
  },
  leads: {
    icon: UsersThreeIcon,
    iconClass: "text-emerald-600 dark:text-emerald-400",
  },
  logs: {
    icon: TerminalWindowIcon,
    iconClass: "text-sky-600 dark:text-sky-400",
  },
};

export function QuickLinks({ links }: { links: QuickLink[] }) {
  const t = useTranslations("dashboard.links");

  return (
    <>
      {links.map((link) => {
        const { icon: Icon, iconClass } = LINK_VISUALS[link.key];

        return (
          <Link
            key={link.key}
            href={link.href}
            className="group flex items-start gap-3.5 border bg-card p-5 shadow-2xs transition-all hover:border-primary/60 hover:bg-accent/35"
          >
            <Icon
              className={`mt-0.5 size-6 shrink-0 ${iconClass}`}
              weight="duotone"
              aria-hidden
            />
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground">
                  {t(`${link.key}.name`)}
                </span>
                <ArrowRightIcon
                  className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary"
                  aria-hidden
                />
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {t(`${link.key}.description`)}
              </p>
            </div>
          </Link>
        );
      })}
    </>
  );
}
