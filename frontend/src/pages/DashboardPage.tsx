import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ProductIcon } from "../components/ProductIcons";
import { ErrorState, Loading, StatusBadge } from "../components/UI";
import type { DocumentItem } from "../types";
type Summary = {
  documents_processed: number;
  review_queue: number;
  success_rate: number;
  average_processing_ms: number;
  pages_processed: number;
  status_counts: Record<string, number>;
  recent_documents: DocumentItem[];
};

export function DashboardPage() {
  const query = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<Summary>("/dashboard/summary?range=30d"),
  });
  if (query.isLoading) return <Loading />;
  if (query.error) return <ErrorState error={query.error} />;
  const data = query.data!;
  const cards = [
    ["Documents", data.documents_processed],
    ["Needs review", data.review_queue],
    ["Success rate", `${data.success_rate}%`],
    ["Avg. extraction", `${(data.average_processing_ms / 1000).toFixed(1)}s`],
    ["Pages parsed", data.pages_processed],
  ] as const;
  return (
    <div className="page-shell space-y-8">
      <div className="page-header">
        <div>
          <h1 className="page-title">Overview</h1>
          <p className="page-description">Last 30 days</p>
        </div>
        <Link to="/documents/new" className="btn-primary">
          <ProductIcon name="upload" size={15} />
          New document
        </Link>
      </div>
      <div className="grid overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 xl:grid-cols-5">
        {cards.map(([label, value], index) => (
          <div
            className="group bg-white p-5 transition hover:bg-brand-mist/50"
            key={label}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-[.08em] text-ink-soft">
                {label}
              </span>
              <span className="font-mono text-[10px] text-brand">
                0{index + 1}
              </span>
            </div>
            <div className="mt-5 text-3xl font-medium tracking-[-.04em]">
              {value}
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[.82fr_1.7fr]">
        <section className="card p-5">
          <div className="flex items-center justify-between">
            <h2 className="section-title">Status overview</h2>
            <span className="text-[11px] text-ink-soft">
              {data.documents_processed} total
            </span>
          </div>
          <div className="mt-7 space-y-5">
            {Object.entries(data.status_counts).map(([key, value]) => (
              <div key={key}>
                <div className="mb-2 flex justify-between text-xs">
                  <span className="capitalize text-ink-soft">
                    {key.replaceAll("_", " ")}
                  </span>
                  <strong className="font-medium text-ink">{value}</strong>
                </div>
                <div className="h-1 overflow-hidden rounded-full bg-paper">
                  <div
                    className="h-full rounded-full bg-brand transition-all duration-700"
                    style={{
                      width: `${Math.max(4, (value / Math.max(1, data.documents_processed)) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
            {!Object.keys(data.status_counts).length && (
              <p className="muted">No activity</p>
            )}
          </div>
        </section>
        <section className="card overflow-hidden">
          <div className="section-header">
            <h2 className="section-title">Recent documents</h2>
            <Link
              className="flex items-center gap-1 text-xs font-medium text-brand-strong hover:underline"
              to="/documents"
            >
              View all <span aria-hidden="true">↗</span>
            </Link>
          </div>
          <div className="divide-y divide-line">
            {data.recent_documents.map((item) => (
              <Link
                key={item.id}
                to={`/documents/${item.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-brand-mist/50"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">
                    {item.original_filename}
                  </div>
                  <div className="mt-1 text-xs text-ink-soft">
                    {new Date(item.created_at).toLocaleString()}
                  </div>
                </div>
                <StatusBadge status={item.status} />
              </Link>
            ))}
            {!data.recent_documents.length && (
              <div className="p-12 text-center text-sm text-ink-soft">
                No documents
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
