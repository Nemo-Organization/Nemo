import { DashboardTopbar } from "./dashboard-topbar";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <DashboardTopbar />
      <main className="mx-auto max-w-7xl px-6 py-6 sm:px-8 sm:py-8">
        {children}
      </main>
    </div>
  );
}
