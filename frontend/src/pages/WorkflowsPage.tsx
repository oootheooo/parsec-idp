import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { ProductIcon } from "../components/ProductIcons";
type Rule = {
  id: string;
  name: string;
  enabled: boolean;
  trigger: string;
  actions: { type: string }[];
};
export function WorkflowsPage() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["workflows"],
    queryFn: () => api<Rule[]>("/workflow-rules"),
  });
  const create = useMutation({
    mutationFn: () =>
      api("/workflow-rules", {
        method: "POST",
        body: JSON.stringify({
          name: "Review low-confidence documents",
          trigger: "extraction_completed",
          conditions: { op: "confidence_below", value: 0.7 },
          actions: [{ type: "mark_review_required" }],
          enabled: true,
        }),
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["workflows"] }),
  });
  const remove = useMutation({
    mutationFn: (id: string) =>
      api(`/workflow-rules/${id}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["workflows"] }),
  });
  return (
    <div className="page-shell max-w-5xl space-y-7">
      <div className="page-header">
        <div>
          <h1 className="page-title">Workflows</h1>
        </div>
        <button className="btn-primary" onClick={() => create.mutate()}>
          <Plus size={15} />
          New rule
        </button>
      </div>
      <div className="space-y-3">
        {query.data?.map((rule) => (
          <div
            className="card-interactive flex items-center gap-4 p-5"
            key={rule.id}
          >
            <ProductIcon name="workflows" size={20} className="text-brand" />
            <div className="min-w-0 flex-1">
              <div className="font-medium">{rule.name}</div>
              <div className="mt-1 text-sm text-ink-soft">
                When {rule.trigger.replaceAll("_", " ")} →{" "}
                {rule.actions
                  .map((a) => a.type.replaceAll("_", " "))
                  .join(", ")}
              </div>
            </div>
            <span
              className={`badge ${rule.enabled ? "border-brand/15 bg-brand-mist text-brand-strong" : "border-line bg-paper text-ink-soft"}`}
            >
              {rule.enabled ? "Enabled" : "Disabled"}
            </span>
            <button
              aria-label={`Delete ${rule.name}`}
              className="btn-icon text-red-600"
              onClick={() =>
                confirm("Delete this workflow rule?") && remove.mutate(rule.id)
              }
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        {query.data?.length === 0 && (
          <div className="card relative overflow-hidden p-14 text-center">
            <div className="parse-grid absolute inset-0" />
            <div className="relative">
              <ProductIcon
                name="workflows"
                size={24}
                className="mx-auto text-brand"
              />
              <h2 className="mt-5 font-semibold">No workflow rules</h2>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
