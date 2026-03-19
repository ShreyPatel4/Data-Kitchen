export default function CatalogPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Catalog</h1>
        <p className="text-gray-500 mt-1">Browse datasets, schemas, lineage, and data quality</p>
      </div>

      <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border)] p-6">
        <div className="text-center py-12 text-gray-500">
          <p>No datasets registered yet.</p>
          <p className="text-sm mt-2">Datasets will appear here once you run your first pipeline.</p>
        </div>
      </div>
    </div>
  );
}
