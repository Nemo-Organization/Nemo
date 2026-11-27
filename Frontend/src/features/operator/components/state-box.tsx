import type { Icon as PhosphorIcon } from "@phosphor-icons/react";

// Gray placeholder for empty or locked sections.
export function StateBox({
  icon: StateIcon,
  title,
  hint,
}: {
  icon: PhosphorIcon;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 bg-muted/60 px-4 py-8 text-center">
      <StateIcon className="size-5 text-muted-foreground" aria-hidden />
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
