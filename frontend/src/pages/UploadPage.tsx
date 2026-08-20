import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ProductIcon } from "../components/ProductIcons";
import type {
  ListResponse,
  ProcessingMode,
  Processor,
  VisualReader,
} from "../types";

const MODE_HELP: Record<ProcessingMode, string> = {
  smart:
    "Recommended. Inspects the PDF, uses visible-page processing for edits or scans, and Docling only for complex structure.",
  native: "Fastest. Uses embedded PDF text and form fields only.",
  visual: "Renders every page and extracts only what is visibly shown.",
  docling: "Runs enhanced whole-document layout and table processing.",
};

export function UploadPage() {
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [processorId, setProcessorId] = useState("");
  const [processingMode, setProcessingMode] = useState<ProcessingMode>("smart");
  const [visualReader, setVisualReader] = useState<VisualReader>("vision");
  const [drag, setDrag] = useState(false);
  const processors = useQuery({
    queryKey: ["processors", "active"],
    queryFn: () => api<ListResponse<Processor>>("/processors?status=active"),
  });
  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a file");
      const body = new FormData();
      body.append("file", file);
      const params = new URLSearchParams({
        processing_mode: processingMode,
        visual_reader: visualReader,
      });
      if (processorId) params.set("processor_id", processorId);
      return api<{ id: string }>(`/documents/upload?${params.toString()}`, {
        method: "POST",
        body,
      });
    },
    onSuccess: (data) => navigate(`/documents/${data.id}`),
  });
  const choose = (next?: File) => {
    if (next) setFile(next);
  };
  const usesRenderedPages =
    processingMode === "smart" || processingMode === "visual";
  return (
    <div className="page-shell max-w-4xl space-y-7">
      <div>
        <h1 className="page-title">Upload document</h1>
      </div>
      <div className="card p-5 md:p-7">
        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            choose(e.dataTransfer.files[0]);
          }}
          className={`group relative grid min-h-64 w-full place-items-center overflow-hidden rounded-lg border border-dashed p-8 transition-all ${drag ? "border-brand bg-brand-mist" : "border-line-strong bg-paper/60 hover:border-brand hover:bg-brand-mist/50"}`}
        >
          <div className="parse-grid pointer-events-none absolute inset-0 opacity-50" />
          {file ? (
            <div className="relative">
              <ProductIcon
                name="documents"
                size={24}
                className="mx-auto text-brand"
              />
              <div className="mt-5 font-medium">{file.name}</div>
              <div className="mt-1 text-sm text-ink-soft">
                {(file.size / 1024 / 1024).toFixed(2)} MB · Click to replace
              </div>
            </div>
          ) : (
            <div className="relative">
              <ProductIcon
                name="upload"
                size={24}
                className="mx-auto text-brand transition-transform group-hover:-translate-y-0.5"
              />
              <div className="mt-5 text-base font-medium">
                Drop a document here
              </div>
              <div className="mt-2 text-sm text-ink-soft">
                PDF, image, Office, HTML, CSV, or text
              </div>
            </div>
          )}
        </button>
        <input
          ref={input}
          className="hidden"
          type="file"
          onChange={(e) => choose(e.target.files?.[0])}
        />
        <div className="mt-7 grid gap-6 border-t border-line pt-7 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="processor">
              Processor
            </label>
            <select
              id="processor"
              className="input"
              value={processorId}
              onChange={(e) => setProcessorId(e.target.value)}
            >
              <option value="">Parse only — choose processor later</option>
              {processors.data?.items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <p className="help-text">Only published processors appear here.</p>
          </div>
          <div>
            <label className="label" htmlFor="processing-mode">
              PDF processing
            </label>
            <select
              id="processing-mode"
              className="input"
              value={processingMode}
              onChange={(e) =>
                setProcessingMode(e.target.value as ProcessingMode)
              }
            >
              <option value="smart">Smart — Recommended</option>
              <option value="native">Native — Fastest</option>
              <option value="visual">Visual — Visible content only</option>
              <option value="docling">Docling — Enhanced layout</option>
            </select>
            <p className="help-text">{MODE_HELP[processingMode]}</p>
          </div>
          {usesRenderedPages && (
            <div>
              <label className="label" htmlFor="visual-reader">
                Rendered-page reader
              </label>
              <select
                id="visual-reader"
                className="input"
                value={visualReader}
                onChange={(e) =>
                  setVisualReader(e.target.value as VisualReader)
                }
              >
                <option value="vision">
                  LLM Vision — Better for handwriting
                </option>
                <option value="ocr">OCR — Faster for typed text</option>
              </select>
              <p className="help-text">
                {visualReader === "ocr"
                  ? "Reads rendered pages locally, then sends the visible text to the extraction model."
                  : "Sends rendered pages directly to the vision model."}
              </p>
            </div>
          )}
        </div>
        {upload.error && (
          <div role="alert" className="notice-danger mt-5">
            {upload.error.message}
          </div>
        )}
        <div className="mt-7 flex justify-end border-t border-line pt-6">
          <button
            className="btn-primary"
            disabled={!file || upload.isPending}
            onClick={() => upload.mutate()}
          >
            {upload.isPending ? "Uploading…" : "Upload and process"}
          </button>
        </div>
      </div>
    </div>
  );
}
