import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  XCircle,
} from "lucide-react";
import { ProductIcon } from "./ProductIcons";

export function ParseLogo() {
  return (
    <div className="flex items-baseline gap-1.5" aria-label="Parse by Handl">
      <span className="text-[18px] font-semibold tracking-[-.04em]">Parse</span>
      <span className="hidden text-[10px] text-ink-soft sm:inline">
        by Handl
      </span>
    </div>
  );
}
export function StatusBadge({ status }: { status: string }) {
  const success = ["completed", "active", "published", "approved"].includes(
    status,
  );
  const failed = ["failed", "rejected"].includes(status);
  const review = status === "review_required";
  const style = success
    ? "border-brand/15 bg-brand-mist text-brand-strong"
    : failed
      ? "border-red-200 bg-red-50 text-red-700"
      : review
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-line bg-paper text-ink-soft";
  const Icon = success
    ? CheckCircle2
    : failed
      ? XCircle
      : review
        ? AlertCircle
        : Clock3;
  return (
    <span key={status} className={`badge status-change gap-1.5 ${style}`}>
      <Icon size={12} />
      {status.replaceAll("_", " ")}
    </span>
  );
}
export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="grid min-h-64 place-items-center">
      <div className="flex flex-col items-center gap-3 text-sm text-ink-soft">
        <div className="grid h-10 w-10 place-items-center rounded-full border border-line bg-white shadow-sm">
          <LoaderCircle size={18} className="animate-spin text-brand" />
        </div>
        {label}
      </div>
    </div>
  );
}
export function ErrorState({ error }: { error: Error }) {
  return (
    <div className="notice-danger">
      <div className="font-medium">Something went wrong</div>
      <p className="mt-1 text-sm opacity-80">{error.message}</p>
    </div>
  );
}
export function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card flex min-h-52 flex-col justify-between gap-8 p-7 sm:flex-row sm:items-center sm:p-9">
      <div className="flex max-w-xl items-start gap-5">
        <ProductIcon
          name="documents"
          size={24}
          className="mt-0.5 shrink-0 text-brand"
        />
        <div>
          <div className="text-base font-semibold">{title}</div>
          <p className="mt-2 max-w-md text-sm leading-6 text-ink-soft">
            {description}
          </p>
        </div>
      </div>
      {action && <div className="shrink-0 sm:pr-2">{action}</div>}
    </div>
  );
}
export function Confidence({ value }: { value: number }) {
  const level = value >= 0.9 ? "High" : value >= 0.7 ? "Medium" : "Low";
  const color =
    value >= 0.9
      ? "text-brand-strong"
      : value >= 0.7
        ? "text-amber-700"
        : "text-red-700";
  return (
    <span className={`text-xs font-medium ${color}`}>
      {Math.round(value * 100)}% · {level}
    </span>
  );
}
