import type { ComponentPropsWithoutRef, ReactNode } from "react";

type Variant = "default" | "ghost" | "accent";

const base =
  "inline-flex h-(--dt-control-h) min-w-6 cursor-default items-center justify-center gap-1.5 " +
  "rounded-(--radius-control) border px-2.5 text-sm font-medium select-none " +
  "transition-colors duration-(--sys-dur-fast)";

const variants: Record<Variant, string> = {
  default:
    "border-border bg-layer-panel text-text-primary hover:bg-(--sys-state-hover) active:bg-(--sys-state-active)",
  ghost: "border-transparent bg-transparent text-text-secondary hover:bg-(--sys-state-hover)",
  accent: "border-accent bg-accent text-text-inverse hover:bg-accent-hover",
};

export function Button({
  variant = "default",
  className = "",
  type = "button",
  ...props
}: ComponentPropsWithoutRef<"button"> & { variant?: Variant }) {
  return (
    <button type={type} className={`${base} ${variants[variant]} ${className}`} {...props} />
  );
}

/** Icon-only button with an enforced ≥24×24 hit area and required accessible name. */
export function IconButton({
  label,
  children,
  className = "",
  ...props
}: Omit<ComponentPropsWithoutRef<"button">, "aria-label" | "children"> & {
  label: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      className={
        "inline-flex size-7 min-h-6 min-w-6 cursor-default items-center justify-center " +
        "rounded-(--radius-control) border border-transparent text-text-secondary " +
        "transition-colors duration-(--sys-dur-fast) hover:bg-(--sys-state-hover) hover:text-text-primary " +
        className
      }
      {...props}
    >
      {children}
    </button>
  );
}
