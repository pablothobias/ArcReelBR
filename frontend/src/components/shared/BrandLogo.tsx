import { BRAND } from "@/branding";
import { cn } from "cn";

/** The approved logo includes its wordmark; custom brand overrides keep their own name. */
export function BrandLogo({ className }: { className?: string }) {
  if (BRAND.name !== "RafaCena") {
    return (
      <span className={cn("inline-flex shrink-0 items-center gap-2", className)}>
        <img src="/rafacena-icon-64.png" alt="" className="size-9 rounded-lg" />
        <span className="font-display text-base font-bold">{BRAND.name}</span>
      </span>
    );
  }

  return (
    <picture className="shrink-0">
      <source srcSet="/rafacena-logo-optimized.webp" type="image/webp" />
      <img src="/rafacena-logo.png" alt={BRAND.name} className={cn("h-10 w-auto shrink-0 rounded-lg", className)} />
    </picture>
  );
}
