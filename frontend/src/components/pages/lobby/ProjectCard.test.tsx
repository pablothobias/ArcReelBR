import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ProjectSummary } from "@/types";
import { ProjectCard } from "./ProjectCard";

function project(thumbnail: string | null): ProjectSummary {
  return {
    name: "demo",
    title: "演示项目",
    style: "Anime",
    thumbnail,
    last_activity_at: null,
    status: {},
  };
}

function posterSrc(thumbnail: string): string | null {
  const { container } = render(<ProjectCard project={project(thumbnail)} readOnly />);
  return container.querySelector("img")?.getAttribute("src") ?? null;
}

describe("ProjectCard poster", () => {
  it("requests a 640px thumbnail for covers served from the project files route", () => {
    expect(posterSrc("/api/v1/files/demo/storyboards/E1S01.png?v=123")).toBe(
      "/api/v1/files/demo/storyboards/E1S01.png?v=123&w=640",
    );
    expect(posterSrc("/api/v1/files/demo/storyboards/E1S01.png")).toBe(
      "/api/v1/files/demo/storyboards/E1S01.png?w=640",
    );
  });

  it("leaves covers from other sources untouched", () => {
    const inline = "data:image/svg+xml;utf8,<svg/>";
    expect(posterSrc(inline)).toBe(inline);
  });
});

describe("ProjectCard episode progress", () => {
  it("reports completed and in-production episodes as text", () => {
    const item = project(null);
    item.status = {
      needs_repair: false,
      repair_reason: null,
      assets: {},
      episodes_summary: { total: 3, scripted: 3, in_production: 1, completed: 1 },
      source_remaining: false,
    };
    const { getByText } = render(<ProjectCard project={item} readOnly />);
    expect(getByText("已完成 1 / 3 集 · 制作中 1 集")).toBeInTheDocument();
  });
});
