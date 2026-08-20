import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  FileJson,
  RefreshCw,
  ScanSearch,
  Trash2,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, API_URL, session } from "../api/client";
import { ErrorState, Loading, StatusBadge } from "../components/UI";
import type { DocumentItem } from "../types";
export function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["document", id],
    queryFn: () => api<DocumentItem>(`/documents/${id}`),
    refetchInterval: (q) =>
      ["queued", "parsing", "parsed", "extracting", "validating"].includes(
        q.state.data?.status || "",
      )
        ? 2500
        : false,
  });
  const remove = useMutation({
    mutationFn: () => api(`/documents/${id}`, { method: "DELETE" }),
    onSuccess: () => navigate("/documents"),
  });
  if (query.isLoading) return <Loading label="Loading document" />;
  if (query.error) return <ErrorState error={query.error} />;
  const doc = query.data!;
  const download = async (path: string, filename: string) => {
    const r = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${session.token}`,
        "X-Workspace-ID": session.workspace || "",
      },
    });
    if (!r.ok) throw new Error(`Export failed (${r.status})`);
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };
  const exportName = `${doc.original_filename.replace(/\.[^.]+$/, "")}.json`;
  return (
    <div className="page-shell space-y-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-3">
            <StatusBadge status={doc.status} />
          </div>
          <h1 className="max-w-4xl text-2xl font-medium tracking-[-.035em] md:text-3xl">{doc.original_filename}</h1>
          <p className="page-description">
            {doc.page_count ?? "—"} pages · Uploaded{" "}
            {new Date(doc.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {doc.original_url && (
            <a className="btn-secondary" href={doc.original_url}>
              <Download size={16} />
              Original
            </a>
          )}
          {doc.latest_extraction_id && (
            <button
              className="btn-secondary"
              onClick={() =>
                void download(`/documents/${id}/export/json`, exportName)
              }
            >
              <FileJson size={16} />
              Export JSON
            </button>
          )}
          {doc.latest_extraction_id && (
            <Link className="btn-brand" to={`/documents/${id}/review`}>
              <ScanSearch size={16} />
              Review
            </Link>
          )}
          <button
            className="btn-icon text-red-600"
            onClick={() =>
              confirm("Delete this document and revoke access to its data?") &&
              remove.mutate()
            }
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      {doc.error_message_safe && (
        <div className="notice-danger">
          {doc.error_message_safe}
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="card p-6">
          <h2 className="section-title">Processing timeline</h2>
          <div className="mt-7 space-y-0">
            {doc.events?.map((event, index) => (
              <div className="relative flex gap-4 pb-7" key={event.id}>
                <div className="relative z-10 mt-1 h-2.5 w-2.5 rounded-full bg-brand ring-4 ring-brand-mist" />
                {index < (doc.events?.length || 0) - 1 && (
                  <div className="absolute left-[5px] top-4 h-full w-px bg-line" />
                )}
                <div>
                  <div className="text-sm font-medium capitalize">
                    {event.to_status.replaceAll("_", " ")}
                  </div>
                  <div className="mt-1 text-xs leading-5 text-ink-soft">
                    {event.message} ·{" "}
                    {new Date(event.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
        <section className="card p-6">
          <h2 className="section-title">Document details</h2>
          <dl className="mt-5 space-y-4 text-sm">
            <div>
              <dt className="text-ink-soft">Type</dt>
              <dd className="mt-1 font-medium">{doc.mime_type}</dd>
            </div>
            <div>
              <dt className="text-ink-soft">Size</dt>
              <dd className="mt-1 font-medium">
                {(doc.file_size / 1024).toFixed(1)} KB
              </dd>
            </div>
            <div>
              <dt className="text-ink-soft">Processor</dt>
              <dd className="mt-1 font-medium">
                {doc.selected_processor_id ? "Assigned" : "Not selected"}
              </dd>
            </div>
            <div>
              <dt className="text-ink-soft">Requested processing</dt>
              <dd className="mt-1 font-medium capitalize">
                {doc.processing_mode}
              </dd>
            </div>
            {(doc.processing_mode === "smart" ||
              doc.processing_mode === "visual") && (
              <div>
                <dt className="text-ink-soft">Rendered-page reader</dt>
                <dd className="mt-1 font-medium">
                  {doc.visual_reader === "ocr" ? "OCR" : "LLM Vision"}
                </dd>
              </div>
            )}
            {doc.processing_route?.route && (
              <div>
                <dt className="text-ink-soft">Actual route</dt>
                <dd className="mt-1 font-medium capitalize">
                  {doc.processing_route.route.replaceAll("-", " ")}
                </dd>
              </div>
            )}
          </dl>
          {doc.processing_route?.pages && (
            <div className="mt-5 border-t pt-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
                Pages
              </div>
              <div className="mt-3 space-y-2">
                {doc.processing_route.pages.map((item) => (
                  <div
                    key={item.page_number}
                    className="rounded-md border border-line bg-paper px-3 py-2.5 text-xs"
                  >
                    <div className="font-semibold">
                      Page {item.page_number} ·{" "}
                      <span className="capitalize">
                        {item.route.replaceAll("-", " ")}
                      </span>
                      {item.reader && (
                        <span>
                          {" "}· {item.reader === "vision" ? "LLM Vision" : item.reader.toUpperCase()}
                        </span>
                      )}
                    </div>
                    {item.reasons.length > 0 && (
                      <div className="mt-1 leading-5 text-ink-soft">
                        {item.reasons.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {doc.status === "failed" && (
            <button
              className="btn-secondary mt-6 w-full"
              onClick={() =>
                void client.invalidateQueries({ queryKey: ["document", id] })
              }
            >
              <RefreshCw size={16} />
              Refresh status
            </button>
          )}
        </section>
      </div>
    </div>
  );
}
