import { useQuery } from "@tanstack/react-query";
import { FileUp, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Empty, ErrorState, Loading, StatusBadge } from "../components/UI";
import type { DocumentItem, ListResponse } from "../types";
export function DocumentsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const query = useQuery({
    queryKey: ["documents", search, status],
    queryFn: () =>
      api<ListResponse<DocumentItem>>(
        `/documents?search=${encodeURIComponent(search)}&status=${status}`,
      ),
  });
  return (
    <div className="page-shell space-y-7">
      <div className="page-header">
        <div>
          <h1 className="page-title">Documents</h1>
        </div>
        <Link className="btn-primary" to="/documents/new">
          <FileUp size={15} />
          Upload document
        </Link>
      </div>
      <div className="page-toolbar">
        <div className="relative min-w-64 flex-1">
          <Search size={16} className="absolute left-3 top-3 text-ink-soft" />
          <input
            aria-label="Search documents"
            className="input border-transparent bg-paper pl-9 shadow-none"
            placeholder="Search by filename…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          aria-label="Filter status"
          className="input w-48 border-transparent bg-paper shadow-none"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          {[
            "queued",
            "parsing",
            "extracting",
            "review_required",
            "completed",
            "failed",
          ].map((value) => (
            <option key={value} value={value}>
              {value.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>
      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : !query.data?.items.length ? (
        <Empty
          title="No documents"
          description="Upload a document to begin."
          action={
            <Link to="/documents/new" className="btn-primary">
              Upload document
            </Link>
          }
        />
      ) : (
        <div className="card overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Pages</th>
                <th>Status</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link
                      className="font-medium hover:text-brand-strong"
                      to={`/documents/${item.id}`}
                    >
                      {item.original_filename}
                    </Link>
                    <div className="mt-1 text-xs text-ink-soft">
                      {(item.file_size / 1024).toFixed(1)} KB
                    </div>
                  </td>
                  <td className="text-ink-soft">{item.page_count ?? "—"}</td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="text-ink-soft">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
