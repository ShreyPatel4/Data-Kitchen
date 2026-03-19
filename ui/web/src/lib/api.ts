const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// Type definitions matching Pydantic schemas
export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  zone: "raw" | "staging" | "curated";
  format: string;
  schema_version: number;
  owner: string | null;
  tags: Record<string, string> | null;
  freshness_slo_seconds: number | null;
  created_at: string;
  updated_at: string;
  columns: Column[];
}

export interface Column {
  id: string;
  name: string;
  data_type: string;
  nullable: boolean;
  description: string | null;
  is_pii: boolean;
  is_partition_key: boolean;
  ordinal_position: number;
}

export interface Connector {
  id: string;
  project_id: string;
  name: string;
  connector_type: string;
  source_type: string;
  config: Record<string, unknown>;
  enabled: boolean;
  last_sync_at: string | null;
  created_at: string;
}

export interface Pipeline {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  graph: Record<string, unknown>;
  schedule: string | null;
  status: string;
  created_at: string;
}

export interface LineageGraph {
  dataset_id: string;
  upstream: LineageEdge[];
  downstream: LineageEdge[];
}

export interface LineageEdge {
  id: string;
  source_dataset_id: string;
  target_dataset_id: string;
  source_column: string | null;
  target_column: string | null;
  transformation_type: string | null;
  job_name: string | null;
  created_at: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  status: string;
}

export const api = {
  health: () => apiFetch<{ status: string; service: string; version: string }>("/health"),

  projects: {
    list: () => apiFetch<Project[]>("/api/v1/projects"),
    get: (id: string) => apiFetch<Project>(`/api/v1/projects/${id}`),
    create: (data: { name: string; description?: string }) =>
      apiFetch<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
  },

  datasets: {
    list: (projectId: string, zone?: string) => {
      const params = zone ? `?zone=${zone}` : "";
      return apiFetch<Dataset[]>(`/api/v1/projects/${projectId}/datasets${params}`);
    },
    get: (projectId: string, id: string) =>
      apiFetch<Dataset>(`/api/v1/projects/${projectId}/datasets/${id}`),
    create: (projectId: string, data: Record<string, unknown>) =>
      apiFetch<Dataset>(`/api/v1/projects/${projectId}/datasets`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  connectors: {
    list: (projectId: string) =>
      apiFetch<Connector[]>(`/api/v1/projects/${projectId}/connectors`),
    create: (projectId: string, data: Record<string, unknown>) =>
      apiFetch<Connector>(`/api/v1/projects/${projectId}/connectors`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  pipelines: {
    list: (projectId: string) =>
      apiFetch<Pipeline[]>(`/api/v1/projects/${projectId}/pipelines`),
    get: (projectId: string, id: string) =>
      apiFetch<Pipeline>(`/api/v1/projects/${projectId}/pipelines/${id}`),
    create: (projectId: string, data: Record<string, unknown>) =>
      apiFetch<Pipeline>(`/api/v1/projects/${projectId}/pipelines`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  lineage: {
    getGraph: (datasetId: string) =>
      apiFetch<LineageGraph>(`/api/v1/lineage/datasets/${datasetId}`),
    createEdge: (data: Record<string, unknown>) =>
      apiFetch<LineageEdge>("/api/v1/lineage/edges", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  ai: {
    skills: () => apiFetch<Skill[]>("/api/v1/ai/skills"),
  },
};
