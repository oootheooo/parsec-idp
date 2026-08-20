import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { ProductIcon } from "../components/ProductIcons";
type KeyItem = {
  id: string;
  name: string;
  key_prefix: string;
  key?: string;
  created_at: string;
  revoked_at: string | null;
};
type Hook = {
  id: string;
  name: string;
  url: string;
  enabled: boolean;
  events: string[];
  secret?: string;
};
export function DeveloperPage() {
  const [tab, setTab] = useState<"keys" | "webhooks" | "examples">("keys");
  const [revealed, setRevealed] = useState("");
  const client = useQueryClient();
  const keys = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => api<KeyItem[]>("/api-keys"),
  });
  const hooks = useQuery({
    queryKey: ["webhooks"],
    queryFn: () => api<Hook[]>("/webhooks"),
  });
  const createKey = useMutation({
    mutationFn: () =>
      api<KeyItem>("/api-keys", {
        method: "POST",
        body: JSON.stringify({
          name: `Integration ${new Date().toLocaleDateString()}`,
        }),
      }),
    onSuccess: (item) => {
      setRevealed(item.key || "");
      void client.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api(`/api-keys/${id}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["api-keys"] }),
  });
  const addHook = useMutation({
    mutationFn: () =>
      api<Hook>("/webhooks", {
        method: "POST",
        body: JSON.stringify({
          name: "Processing results",
          url: "https://example.com/webhooks/parse",
          events: [
            "document.processing_completed",
            "document.processing_failed",
          ],
          enabled: true,
        }),
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["webhooks"] }),
  });
  return (
    <div className="page-shell max-w-6xl space-y-7">
      <div>
        <h1 className="page-title">API & Webhooks</h1>
      </div>
      <div className="tabs">
        {(["keys", "webhooks", "examples"] as const).map((item) => (
          <button
            key={item}
            className={`tab capitalize ${tab === item ? "tab-active" : ""}`}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </div>
      {tab === "keys" && (
        <div className="space-y-4">
          {revealed && (
            <div className="notice-warning">
              <div className="font-medium">Copy this API key now</div>
              <p className="mt-1 text-sm opacity-80">
                For security, it will not be shown again.
              </p>
              <div className="mt-3 flex items-center gap-2 rounded-md border bg-white p-3 font-mono text-sm">
                <span className="min-w-0 flex-1 truncate">{revealed}</span>
                <button
                  className="btn-icon"
                  aria-label="Copy key"
                  onClick={() => void navigator.clipboard.writeText(revealed)}
                >
                  <Copy size={15} />
                </button>
              </div>
            </div>
          )}
          <section className="card">
            <div className="section-header">
              <div>
                <h2 className="section-title">API keys</h2>
                <p className="help-text">
                  Keys inherit this workspace and are stored only as hashes.
                </p>
              </div>
              <button
                className="btn-primary"
                onClick={() => createKey.mutate()}
              >
                <Plus size={15} />
                Create key
              </button>
            </div>
            <div className="divide-y divide-line">
              {keys.data?.map((item) => (
                <div
                  className="flex items-center justify-between p-5"
                  key={item.id}
                >
                  <div className="flex items-center gap-3">
                    <ProductIcon name="api" size={20} className="text-brand" />
                    <div>
                      <div className="text-sm font-medium">{item.name}</div>
                      <div className="mt-1 font-mono text-xs text-ink-soft">
                        {item.key_prefix}••••••••
                      </div>
                    </div>
                  </div>
                  <button
                    aria-label={`Revoke ${item.name}`}
                    className="btn-icon text-red-600"
                    onClick={() =>
                      confirm(
                        "Revoke this key? Existing integrations will stop working.",
                      ) && revoke.mutate(item.id)
                    }
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
      {tab === "webhooks" && (
        <section className="card">
          <div className="section-header">
            <div>
              <h2 className="section-title">Webhook endpoints</h2>
              <p className="help-text">
                Signed HMAC notifications with retry history.
              </p>
            </div>
            <button className="btn-primary" onClick={() => addHook.mutate()}>
              <Plus size={15} />
              Add example endpoint
            </button>
          </div>
          <div className="divide-y divide-line">
            {hooks.data?.map((item) => (
              <div className="flex items-center gap-4 p-5" key={item.id}>
                <ProductIcon
                  name="workflows"
                  size={20}
                  className="text-brand"
                />
                <div className="min-w-0">
                  <div className="text-sm font-medium">{item.name}</div>
                  <div className="mt-1 truncate text-xs text-ink-soft">
                    {item.url}
                  </div>
                </div>
                <span
                  className={`badge ml-auto ${item.enabled ? "border-brand/15 bg-brand-mist text-brand-strong" : "border-line bg-paper text-ink-soft"}`}
                >
                  {item.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
      {tab === "examples" && (
        <section className="card overflow-hidden">
          <div className="section-header">
            <h2 className="section-title">Upload with the API</h2>
          </div>
          <pre className="m-4 overflow-auto rounded-md bg-ink p-5 text-sm leading-6 text-brand-soft">
            <code>{`curl -X POST http://localhost:8000/api/v1/documents/upload \\\n  -H "Authorization: Bearer hdl_live_…" \\\n  -F "file=@invoice.pdf" \\\n  -F "processor_id=<processor-uuid>"`}</code>
          </pre>
        </section>
      )}
    </div>
  );
}
