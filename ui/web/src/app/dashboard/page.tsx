export default function DashboardPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Mission Control</h1>
        <p className="text-gray-500 mt-1">Pipeline status, freshness, and AI-suggested actions</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatusCard title="Pipelines" value="0" subtitle="No pipelines configured" status="neutral" />
        <StatusCard title="Datasets" value="0" subtitle="No datasets registered" status="neutral" />
        <StatusCard title="Freshness" value="--" subtitle="No SLOs defined" status="neutral" />
      </div>

      <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border)] p-6">
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        <div className="text-center py-12 text-gray-500">
          <p>No activity yet. Connect your first data source to get started.</p>
        </div>
      </div>
    </div>
  );
}

function StatusCard({ title, value, subtitle, status }: {
  title: string;
  value: string;
  subtitle: string;
  status: "healthy" | "warning" | "error" | "neutral";
}) {
  const colors = {
    healthy: "text-green-400",
    warning: "text-yellow-400",
    error: "text-red-400",
    neutral: "text-gray-400",
  };

  return (
    <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border)] p-5">
      <p className="text-sm text-gray-500">{title}</p>
      <p className={`text-3xl font-bold mt-1 ${colors[status]}`}>{value}</p>
      <p className="text-xs text-gray-600 mt-1">{subtitle}</p>
    </div>
  );
}
