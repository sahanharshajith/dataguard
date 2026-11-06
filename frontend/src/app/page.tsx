import ServiceStatusCard from "@/components/ServiceStatusCard";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-6 py-12">
        <header className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">DataGuard</h1>
          <p className="mt-1 text-slate-600">Data Quality &amp; Observability Platform</p>
          <span className="mt-3 inline-block rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
            Work in progress
          </span>
        </header>

        <section aria-labelledby="platform-status">
          <h2 id="platform-status" className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Platform status
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <ServiceStatusCard
              title="API"
              description="FastAPI backend is running"
              path="/health"
            />
            <ServiceStatusCard
              title="Database"
              description="Backend can reach PostgreSQL"
              path="/health/db"
            />
          </div>
        </section>
      </div>
    </main>
  );
}