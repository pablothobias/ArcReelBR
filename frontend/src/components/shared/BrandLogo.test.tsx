import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BrandLogo } from "./BrandLogo";

const brand = vi.hoisted(() => ({ name: "RafaCena" }));
vi.mock("@/branding", () => ({ BRAND: brand }));

afterEach(() => { brand.name = "RafaCena"; });

describe("BrandLogo", () => {
  it("exposes the approved logo as the product name", () => {
    render(<BrandLogo />);
    expect(screen.getByRole("img", { name: "RafaCena" })).toHaveAttribute("src", "/rafacena-logo.png");
  });

  it("keeps a configured brand name instead of displaying the RafaCena wordmark", () => {
    brand.name = "Studio";
    render(<BrandLogo />);
    expect(screen.getByText("Studio")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "RafaCena" })).not.toBeInTheDocument();
  });
});
