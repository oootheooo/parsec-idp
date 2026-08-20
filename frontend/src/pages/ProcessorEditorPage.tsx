import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Code2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState, Loading } from "../components/UI";
import type { Processor, ProcessorVersion } from "../types";
type Template = {
  id: string;
  key: string;
  name: string;
  description: string;
  schema_json: Record<string, unknown>;
  instructions: string;
};
const blank = JSON.stringify(
  { type: "object", additionalProperties: false, properties: {}, required: [] },
  null,
  2,
);
export function ProcessorEditorPage() {
  const { id } = useParams();
  const create = !id;
  const navigate = useNavigate();
  const detail = useQuery({
    queryKey: ["processor", id],
    queryFn: () => api<Processor>(`/processors/${id}`),
    enabled: !create,
  });
  const templates = useQuery({
    queryKey: ["templates"],
    queryFn: () => api<Template[]>("/processor-templates"),
    enabled: create,
  });
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [schema, setSchema] = useState(blank);
  const [instructions, setInstructions] = useState("");
  const [templateKey, setTemplateKey] = useState("blank");
  const [tab, setTab] = useState("schema");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (detail.data) {
      setName(detail.data.name);
      setDescription(detail.data.description);
      const draft =
        detail.data.versions?.find((v) => v.state === "draft") ||
        detail.data.versions?.[0];
      if (draft) {
        setSchema(JSON.stringify(draft.schema_json, null, 2));
        setInstructions(draft.instructions);
      }
    }
  }, [detail.data]);
  const applyTemplate = (key: string) => {
    setTemplateKey(key);
    const template = templates.data?.find((item) => item.key === key);
    if (!template) return;
    setSchema(JSON.stringify(template.schema_json, null, 2));
    setInstructions(template.key === "blank" ? "" : template.instructions);
    if (!name) setName(template.key === "blank" ? "" : template.name);
    if (!description)
      setDescription(template.key === "blank" ? "" : template.description);
    setMessage(
      template.key === "blank"
        ? "Blank processor selected"
        : `${template.name} preset loaded`,
    );
    setError("");
  };
  const persistDraft = async () => {
    setError("");
    const parsed = JSON.parse(schema);
    if (create)
      return api<Processor>("/processors", {
        method: "POST",
        body: JSON.stringify({
          name,
          description,
          template_key: templateKey,
          schema_json: parsed,
          instructions,
        }),
      });
    await api(`/processors/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name, description }),
    });
    let fresh = await api<Processor>(`/processors/${id}`);
    let draft = fresh.versions?.find((v) => v.state === "draft");
    if (!draft)
      draft = await api<ProcessorVersion>(`/processors/${id}/versions`, {
        method: "POST",
        body: JSON.stringify({}),
      });
    await api(`/processors/${id}/versions/${draft.id}`, {
      method: "PATCH",
      body: JSON.stringify({ schema_json: parsed, instructions }),
    });
    fresh = await api<Processor>(`/processors/${id}`);
    return fresh;
  };
  const save = useMutation({
    mutationFn: persistDraft,
    onSuccess: (result) => {
      setMessage("Draft saved");
      if (create) navigate(`/processors/${result.id}/edit`);
      else void detail.refetch();
    },
    onError: (e) => setError((e as Error).message),
  });
  const publish = useMutation({
    mutationFn: async () => {
      const fresh = await persistDraft();
      const draft = fresh.versions?.find((v) => v.state === "draft");
      if (!draft) throw new Error("No draft to publish");
      return api(`/processors/${id}/versions/${draft.id}/publish`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      setMessage("Processor published");
      void detail.refetch();
    },
    onError: (e) => setError((e as Error).message),
  });
  const assist = async () => {
    if (!instructions.trim()) {
      setError("Describe the fields in Instructions first.");
      return;
    }
    try {
      const result = await api<{ schema: Record<string, unknown> }>(
        "/processors/schema-assist",
        { method: "POST", body: JSON.stringify({ description: instructions }) },
      );
      setSchema(JSON.stringify(result.schema, null, 2));
      setMessage("Generated schema — review before publishing");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  if (detail.isLoading) return <Loading />;
  if (detail.error) return <ErrorState error={detail.error} />;
  return (
    <div className="page-shell max-w-6xl space-y-7">
      <div>
        <Link
          to="/processors"
          className="mb-5 inline-flex items-center gap-1.5 text-xs font-medium text-ink-soft hover:text-brand-strong"
        >
          <ArrowLeft size={14} />
          Processors
        </Link>
        <div className="page-header">
          <div>
            <h1 className="page-title">
              {create ? "New processor" : name || "Edit processor"}
            </h1>
          </div>
          <div className="flex gap-2">
            <button
              className="btn-secondary"
              disabled={save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Saving…" : "Save draft"}
            </button>
            {!create && (
              <button
                className="btn-primary"
                disabled={publish.isPending}
                onClick={() => publish.mutate()}
              >
                <Check size={15} />
                Publish
              </button>
            )}
          </div>
        </div>
      </div>
      {message && <div className="notice-success">{message}</div>}
      {error && (
        <div role="alert" className="notice-danger">
          {error}
        </div>
      )}
      <div className="card overflow-hidden">
        <div className="grid border-b border-line md:grid-cols-2">
          <div className="p-5 md:p-6">
            <label className="label" htmlFor="name">
              Name
            </label>
            <input
              id="name"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="border-t border-line p-5 md:border-l md:border-t-0 md:p-6">
            <label className="label" htmlFor="description">
              Description
            </label>
            <input
              id="description"
              className="input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
        {create && (
          <div className="border-b border-line p-5 md:p-6">
            <label className="label" htmlFor="template">
              Start from a preset
            </label>
            <select
              id="template"
              className="input"
              value={templateKey}
              onChange={(e) => applyTemplate(e.target.value)}
            >
              {templates.data?.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name} — {item.description}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="tabs px-5">
          <button
            className={`tab ${tab === "schema" ? "tab-active" : ""}`}
            onClick={() => setTab("schema")}
          >
            Schema
          </button>
          <button
            className={`tab ${tab === "instructions" ? "tab-active" : ""}`}
            onClick={() => setTab("instructions")}
          >
            Instructions
          </button>
        </div>
        <div className="p-5 md:p-6">
          {tab === "schema" ? (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Code2 size={16} />
                    JSON Schema
                  </div>
                  <p className="help-text">
                    Object roots, nested fields, arrays, constraints, and enums
                    are supported.
                  </p>
                </div>
                <button className="btn-secondary" onClick={() => void assist()}>
                  <Sparkles size={15} />
                  Generate fields
                </button>
              </div>
              <textarea
                aria-label="JSON Schema"
                spellCheck={false}
                className="input min-h-[430px] bg-[#fbfcfb] font-mono text-xs leading-5"
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
              />
            </>
          ) : (
            <>
              <label className="label" htmlFor="instructions">
                Extraction instructions
              </label>
              <textarea
                id="instructions"
                className="input min-h-64"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Extract supplier name, invoice number, line items, tax and total. Preserve identifiers exactly…"
              />
              <p className="help-text">
                The model is separately instructed to treat document content as
                untrusted data.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
