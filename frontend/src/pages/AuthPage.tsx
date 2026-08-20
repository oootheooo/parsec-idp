import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { useAuth } from "../auth";
import { ParseLogo } from "../components/UI";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(10, "Use at least 10 characters"),
});
const registerSchema = loginSchema.extend({
  display_name: z.string().min(1, "Your name is required"),
  workspace_name: z.string().min(1, "Workspace name is required"),
});
type FormData = z.infer<typeof registerSchema>;

export function AuthPage() {
  const register = useLocation().pathname === "/register";
  const auth = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState("");
  const {
    register: field,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(register ? registerSchema : loginSchema),
  });
  const submit = async (data: FormData) => {
    setServerError("");
    try {
      if (register) await auth.register(data);
      else await auth.login(data.email, data.password);
      navigate("/");
    } catch (error) {
      setServerError((error as Error).message);
    }
  };
  return (
    <div className="min-h-screen bg-paper">
      <header className="mx-auto flex h-16 max-w-[1280px] items-center border-b border-line px-5 md:px-8">
        <ParseLogo />
      </header>
      <main className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-[1280px] place-items-center px-5 py-12 md:px-8">
        <section className="w-full max-w-md">
          <h1 className="display-title text-4xl">
            {register ? "Create workspace" : "Sign in"}
          </h1>
          <form
            noValidate
            className="mt-8 space-y-5"
            onSubmit={handleSubmit(submit)}
          >
            {register && (
              <>
                <div>
                  <label className="label" htmlFor="display_name">
                    Your name
                  </label>
                  <input
                    id="display_name"
                    className="input"
                    autoComplete="name"
                    {...field("display_name")}
                  />
                  <p className="mt-1 text-xs text-red-600">
                    {errors.display_name?.message}
                  </p>
                </div>
                <div>
                  <label className="label" htmlFor="workspace_name">
                    Workspace name
                  </label>
                  <input
                    id="workspace_name"
                    className="input"
                    {...field("workspace_name")}
                  />
                  <p className="mt-1 text-xs text-red-600">
                    {errors.workspace_name?.message}
                  </p>
                </div>
              </>
            )}
            <div>
              <label className="label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                className="input"
                autoComplete="email"
                {...field("email")}
              />
              <p className="mt-1 text-xs text-red-600">
                {errors.email?.message}
              </p>
            </div>
            <div>
              <label className="label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                className="input"
                autoComplete={register ? "new-password" : "current-password"}
                {...field("password")}
              />
              <p className="mt-1 text-xs text-red-600">
                {errors.password?.message}
              </p>
            </div>
            {serverError && (
              <div role="alert" className="notice-danger">
                {serverError}
              </div>
            )}
            <button className="btn-primary w-full py-3" disabled={isSubmitting}>
              {isSubmitting
                ? "Please wait…"
                : register
                  ? "Create workspace"
                  : "Sign in"}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-ink-soft">
            <Link
              className="font-medium text-brand-strong hover:underline"
              to={register ? "/login" : "/register"}
            >
              {register ? "Sign in instead" : "Create workspace"}
            </Link>
          </p>
        </section>
      </main>
    </div>
  );
}
