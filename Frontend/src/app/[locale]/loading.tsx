import { Skeleton } from "@/components/ui/skeleton";

export default function LocaleLoading() {
  return (
    <main className="flex min-h-screen flex-col gap-4 p-4" aria-busy="true">
      <Skeleton className="h-17 w-full" />
      <Skeleton className="h-10 w-1/3" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Skeleton className="h-80 lg:col-span-2" />
        <Skeleton className="h-80" />
      </div>
    </main>
  );
}
