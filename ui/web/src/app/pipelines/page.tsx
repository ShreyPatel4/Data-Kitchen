export default function PipelinesPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Pipelines</h1>
        <p className="text-gray-500 mt-1">Create and monitor data pipelines</p>
      </div>

      <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border)] p-6">
        <div className="text-center py-12 text-gray-500">
          <p>No pipelines configured yet.</p>
          <p className="text-sm mt-2">Use the pipeline builder or AI assistant to create your first pipeline.</p>
        </div>
      </div>
    </div>
  );
}
