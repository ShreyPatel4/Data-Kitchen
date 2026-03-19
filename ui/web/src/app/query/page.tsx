export default function QueryPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Query</h1>
        <p className="text-gray-500 mt-1">Write SQL or ask questions in natural language</p>
      </div>

      <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border)] p-6">
        <div className="text-center py-12 text-gray-500">
          <p>Query editor coming in Sprint 8.</p>
          <p className="text-sm mt-2">You will be able to write Trino SQL or use the AI SQL assistant here.</p>
        </div>
      </div>
    </div>
  );
}
