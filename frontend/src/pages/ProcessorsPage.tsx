import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Copy, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ProductIcon } from "../components/ProductIcons";
import { Empty, ErrorState, Loading, StatusBadge } from "../components/UI";
import type { ListResponse, Processor } from "../types";
export function ProcessorsPage() {
  const [search, setSearch] = useState("");
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["processors", search],
    queryFn: () =>
      api<ListResponse<Processor>>(
        `/processors?search=${encodeURIComponent(search)}`,
      ),
  });
  const duplicate = useMutation({
    mutationFn: (id: string) =>
      api(`/processors/${id}/duplicate`, { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["processors"] }),
  });
  const archive = useMutation({
    mutationFn: (id: string) =>
      api(`/processors/${id}/archive`, { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["processors"] }),
  });
  return (
    <div className="page-shell space-y-7">
      <div className="page-header">
        <div>
          <h1 className="page-title">Processors</h1>
        </div>
        <Link to="/processors/new" className="btn-primary">
          <Plus size={15} />
          New processor
        </Link>
      </div>
      <div className="page-toolbar">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-3 text-ink-soft" />
          <input
            className="input border-transparent bg-paper pl-9 shadow-none"
            aria-label="Search processors"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search processors…"
          />
        </div>
      </div>
      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : !query.data?.items.length ? (
        <Empty
          title="No processors"
          description="Create a processor to define an extraction schema."
          action={
            <Link className="btn-primary" to="/processors/new">
              Create processor
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {query.data.items.map((item) => (
            <article className="card-interactive p-5" key={item.id}>
              <div className="flex items-start justify-between">
                <ProductIcon
                  name="processors"
                  size={20}
                  className="text-brand"
                />
                <StatusBadge status={item.status} />
              </div>
              <Link
                to={`/processors/${item.id}/edit`}
                className="mt-6 block text-lg font-semibold tracking-[-.02em] hover:text-brand-strong"
              >
                {item.name}
              </Link>
              <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-ink-soft">
                {item.description || "No description provided."}
              </p>
              <div className="mt-5 flex items-center justify-between border-t border-line pt-4 text-xs text-ink-soft">
                <span>
                  Updated {new Date(item.updated_at).toLocaleDateString()}
                </span>
                <div className="flex">
                  <button
                    aria-label={`Duplicate ${item.name}`}
                    className="btn-icon"
                    onClick={() => duplicate.mutate(item.id)}
                  >
                    <Copy size={15} />
                  </button>
                  <button
                    aria-label={`Archive ${item.name}`}
                    className="btn-icon text-red-600"
                    onClick={() =>
                      confirm(`Archive ${item.name}?`) &&
                      archive.mutate(item.id)
                    }
                  >
                    <Archive size={15} />
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
