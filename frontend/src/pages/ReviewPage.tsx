import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Edit3,
  ExternalLink,
  Save,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Document as PdfDocument, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Confidence, ErrorState, Loading, StatusBadge } from "../components/UI";
import type { DocumentItem, Extraction, ExtractionField } from "../types";
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();
type Pages = {
  pages: {
    page_number: number;
    width: number | null;
    height: number | null;
    text: string;
  }[];
  original_url: string;
  mime_type: string;
};
function display(value: unknown) {
  if (value === null || value === undefined) return "Not found";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
function fieldPathLabel(path: string) {
  const segments = path
    .replace(/^\$\.?/, "")
    .split(".")
    .filter(Boolean)
    .map((segment) => {
      const match = segment.match(/^(.+?)(?:\[(\d+)\])?$/);
      const name = (match?.[1] || segment)
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
      return match?.[2] === undefined
        ? name
        : `${name} ${Number(match[2]) + 1}`;
    });
  return segments.join(" › ");
}
export function ReviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const doc = useQuery({
    queryKey: ["document", id],
    queryFn: () => api<DocumentItem>(`/documents/${id}`),
  });
  const pages = useQuery({
    queryKey: ["pages", id],
    queryFn: () => api<Pages>(`/documents/${id}/pages`),
  });
  const extraction = useQuery({
    queryKey: ["extraction", id, doc.data?.latest_extraction_id],
    queryFn: () =>
      api<Extraction>(
        `/documents/${id}/extractions/${doc.data!.latest_extraction_id}`,
      ),
    enabled: !!doc.data?.latest_extraction_id,
  });
  const [selected, setSelected] = useState<ExtractionField | null>(null);
  const [page, setPage] = useState(1);
  const [scale, setScale] = useState(1);
  const [editing, setEditing] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  useEffect(() => {
    if (extraction.data && !selected)
      setSelected(extraction.data.fields[0] || null);
  }, [extraction.data, selected]);
  useEffect(() => {
    const evidence = selected?.evidence[0];
    if (evidence?.page_number) setPage(evidence.page_number);
  }, [selected]);
  const review = useMutation({
    mutationFn: (payload: {
      json_path: string;
      action: string;
      value?: unknown;
    }) =>
      api(`/documents/${id}/review/fields`, {
        method: "POST",
        body: JSON.stringify({
          extraction_run_id: extraction.data!.id,
          ...payload,
        }),
      }),
    onSuccess: () => {
      setEditing(null);
      void client.invalidateQueries({ queryKey: ["extraction", id] });
    },
  });
  const approve = useMutation({
    mutationFn: () =>
      api(`/documents/${id}/review/approve`, {
        method: "POST",
        body: JSON.stringify({ extraction_run_id: extraction.data!.id }),
      }),
    onSuccess: () => navigate(`/documents/${id}`),
  });
  const saveEdit = (field: ExtractionField) => {
    let value: unknown = editValue;
    if (typeof field.value_json === "number") {
      value = Number(editValue);
      if (Number.isNaN(value)) return;
    }
    if (typeof field.value_json === "boolean") value = editValue === "true";
    review.mutate({ json_path: field.json_path, action: "correct", value });
  };
  const grouped = useMemo(() => {
    const map = new Map<string, ExtractionField[]>();
    for (const field of extraction.data?.fields || []) {
      const key = field.json_path.split(".")[1]?.split("[")[0] || "Fields";
      map.set(key, [...(map.get(key) || []), field]);
    }
    return [...map.entries()];
  }, [extraction.data]);
  if (doc.isLoading || pages.isLoading || extraction.isLoading)
    return <Loading label="Preparing review workspace" />;
  if (doc.error) return <ErrorState error={doc.error} />;
  if (extraction.error) return <ErrorState error={extraction.error} />;
  if (!extraction.data)
    return <div className="card p-8">No extraction is ready for review.</div>;
  const data = extraction.data;
  const bbox = selected?.evidence[0]?.bbox;
  return (
    <div className="-mx-4 -my-7 flex h-[calc(100vh-4rem)] flex-col overflow-hidden bg-paper md:-mx-8 md:-my-10">
      <header className="flex h-16 shrink-0 items-center justify-between border-b bg-white px-5">
        <div className="flex min-w-0 items-center gap-4">
          <Link to={`/documents/${id}`} className="btn-ghost px-2">
            <ArrowLeft size={18} />
          </Link>
          <div className="min-w-0">
            <div className="truncate font-semibold">
              {doc.data!.original_filename}
            </div>
            <div className="mt-0.5 flex items-center gap-2 text-xs text-ink-soft">
              <StatusBadge status={doc.data!.status} />
              <span>
                {data.review_summary.reviewed} / {data.review_summary.total}{" "}
                reviewed
              </span>
            </div>
          </div>
        </div>
        <button
          className="btn-primary"
          disabled={approve.isPending}
          onClick={() => approve.mutate()}
        >
          <CheckCircle2 size={17} />
          {approve.isPending ? "Approving…" : "Approve document"}
        </button>
      </header>
      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1.15fr)_minmax(420px,.85fr)]">
        <section className="flex min-h-0 flex-col border-r bg-[#1d2521]">
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 px-4 text-white">
            <div className="text-sm font-semibold">Source document</div>
            <div className="flex items-center gap-1">
              <button
                aria-label="Previous page"
                className="review-control rounded p-1.5 hover:bg-white/10"
                onClick={() => setPage(Math.max(1, page - 1))}
              >
                <ChevronLeft size={17} />
              </button>
              <span className="min-w-20 text-center text-xs">
                Page {page} / {pages.data?.pages.length || 1}
              </span>
              <button
                aria-label="Next page"
                className="review-control rounded p-1.5 hover:bg-white/10"
                onClick={() =>
                  setPage(Math.min(pages.data?.pages.length || 1, page + 1))
                }
              >
                <ChevronRight size={17} />
              </button>
              <span className="mx-2 h-5 w-px bg-white/20" />
              <button
                aria-label="Zoom out"
                className="review-control rounded p-1.5 hover:bg-white/10"
                onClick={() => setScale(Math.max(0.6, scale - 0.15))}
              >
                <ZoomOut size={17} />
              </button>
              <span className="w-10 text-center text-xs">
                {Math.round(scale * 100)}%
              </span>
              <button
                aria-label="Zoom in"
                className="review-control rounded p-1.5 hover:bg-white/10"
                onClick={() => setScale(Math.min(1.8, scale + 0.15))}
              >
                <ZoomIn size={17} />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-auto p-6">
            <div className="relative mx-auto w-fit shadow-2xl">
              <div key={page} className="page-swap relative">
                {pages.data?.mime_type === "application/pdf" ? (
                  <PdfDocument
                    file={pages.data.original_url}
                    loading={
                      <div className="grid h-[700px] w-[520px] place-items-center bg-white">
                        Loading page…
                      </div>
                    }
                  >
                    <Page
                      pageNumber={page}
                      scale={scale}
                      renderAnnotationLayer
                      renderTextLayer
                    />
                  </PdfDocument>
                ) : (
                  <div className="min-h-[700px] w-[600px] max-w-full bg-white p-12 text-sm leading-7">
                    {pages.data?.pages[page - 1]?.text || (
                      <div className="text-center text-ink-soft">
                        Preview unavailable.{" "}
                        <a
                          className="text-brand"
                          href={pages.data?.original_url}
                        >
                          Open original{" "}
                          <ExternalLink className="inline" size={13} />
                        </a>
                      </div>
                    )}
                  </div>
                )}
                {bbox && selected?.evidence[0]?.page_number === page && (
                  <div
                    className="pointer-events-none absolute border-2 border-amber-400 bg-amber-300/25 shadow-[0_0_0_2px_rgba(255,255,255,.8)]"
                    style={{
                      left: `${bbox.x0 * 100}%`,
                      top: `${bbox.y0 * 100}%`,
                      width: `${(bbox.x1 - bbox.x0) * 100}%`,
                      height: `${(bbox.y1 - bbox.y0) * 100}%`,
                    }}
                  />
                )}
              </div>
            </div>
          </div>
        </section>
        <section className="min-h-0 overflow-y-auto bg-white">
          <div className="sticky top-0 z-10 border-b border-line bg-white/95 px-6 py-4 backdrop-blur">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold">Extracted data</h2>
                <p className="mt-1 text-xs text-ink-soft">
                  Select a field to inspect its source.
                </p>
              </div>
              {data.validation_summary.failed > 0 ? (
                <span className="badge bg-red-50 text-red-700">
                  {data.validation_summary.failed} validation issues
                </span>
              ) : (
                <span className="badge border-brand/15 bg-brand-mist text-brand-strong">
                  Valid
                </span>
              )}
            </div>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-paper">
              <div
                className="h-full bg-brand transition-all"
                style={{
                  width: `${data.review_summary.total ? (data.review_summary.reviewed / data.review_summary.total) * 100 : 0}%`,
                }}
              />
            </div>
          </div>
          <div className="divide-y divide-line">
            {grouped.map(([group, fields]) => (
              <div key={group} className="p-6">
                <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-ink-soft">
                  {group.replaceAll("_", " ")}
                </h3>
                <div className="space-y-3">
                  {fields.map((field) => (
                    <div
                      key={field.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelected(field)}
                      onKeyDown={(e) => e.key === "Enter" && setSelected(field)}
                      className={`field-row rounded-md border p-4 ${selected?.id === field.id ? "border-brand bg-brand-mist ring-1 ring-brand/20" : "hover:border-line-strong"}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-semibold">
                            {fieldPathLabel(field.json_path)}
                          </div>
                          {editing === field.id ? (
                            <div
                              className="mt-2 flex gap-2"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <input
                                autoFocus
                                className="input"
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onKeyDown={(e) =>
                                  e.key === "Enter" && saveEdit(field)
                                }
                              />
                              <button
                                aria-label="Save correction"
                                className="btn-primary px-2"
                                onClick={() => saveEdit(field)}
                              >
                                <Save size={15} />
                              </button>
                              <button
                                aria-label="Cancel edit"
                                className="btn-secondary px-2"
                                onClick={() => setEditing(null)}
                              >
                                <X size={15} />
                              </button>
                            </div>
                          ) : (
                            <div
                              className={`mt-1 break-words text-sm ${field.effective_value == null ? "italic text-ink-soft" : "text-ink"}`}
                            >
                              {display(field.effective_value)}
                            </div>
                          )}
                          <div className="mt-2 flex items-center gap-3">
                            <Confidence value={field.confidence} />
                            <span className="text-xs capitalize text-ink-soft">
                              {field.review_state}
                            </span>
                          </div>
                        </div>
                        <div
                          className="flex shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            title="Correct field"
                            className="btn-ghost px-2"
                            onClick={() => {
                              setEditing(field.id);
                              setEditValue(
                                field.effective_value == null
                                  ? ""
                                  : String(field.effective_value),
                              );
                            }}
                          >
                            <Edit3 size={15} />
                          </button>
                          <button
                            title="Approve field"
                            className="btn-ghost px-2 text-brand-strong"
                            onClick={() =>
                              review.mutate({
                                json_path: field.json_path,
                                action: "approve",
                              })
                            }
                          >
                            <Check size={16} />
                          </button>
                        </div>
                      </div>
                      {selected?.id === field.id &&
                        field.evidence[0]?.source_text && (
                          <div className="evidence-in mt-3 border-t pt-3">
                            <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-soft">
                              Source · Page {field.evidence[0].page_number}
                            </div>
                            <blockquote className="mt-1 border-l-2 border-amber-400 pl-3 text-xs leading-5 text-ink-soft">
                              {field.evidence[0].source_text}
                            </blockquote>
                          </div>
                        )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
