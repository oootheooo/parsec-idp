import { useAuth } from "../auth";
import { ProductIcon } from "../components/ProductIcons";
export function SettingsPage() {
  const { user, workspaceId } = useAuth();
  const workspace = user?.workspaces.find((item) => item.id === workspaceId);
  return (
    <div className="page-shell max-w-4xl space-y-7">
      <div>
        <h1 className="page-title">Settings</h1>
      </div>
      <section className="card">
        <div className="section-header">
          <h2 className="section-title">Workspace details</h2>
        </div>
        <dl className="grid gap-px bg-line sm:grid-cols-2">
          <div className="bg-white p-5">
            <dt className="text-[11px] font-medium uppercase tracking-[.08em] text-ink-soft">
              Name
            </dt>
            <dd className="mt-2 font-medium">{workspace?.name}</dd>
          </div>
          <div className="bg-white p-5">
            <dt className="text-[11px] font-medium uppercase tracking-[.08em] text-ink-soft">
              Your role
            </dt>
            <dd className="mt-2 capitalize font-medium">{workspace?.role}</dd>
          </div>
        </dl>
      </section>
      <section className="card flex gap-4 p-6">
        <ProductIcon
          name="settings"
          size={22}
          className="mt-0.5 shrink-0 text-brand"
        />
        <div>
          <h2 className="section-title">Data handling</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-soft">
            Every resource lookup is scoped through your active workspace.
            Originals stay private in object storage and downloads use
            short-lived signed links. External AI providers may receive document
            content when configured.
          </p>
        </div>
      </section>
    </div>
  );
}
