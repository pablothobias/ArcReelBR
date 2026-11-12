import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Router } from "wouter";
import { memoryLocation } from "wouter/memory-location";
import { API, type AssetRenameResult } from "@/api";
import { LeaveGuardProvider } from "@/components/shared/edit-unit/LeaveGuard";
import i18n from "@/i18n";
import { useAppStore } from "@/stores/app-store";
import { useConfigStatusStore } from "@/stores/config-status-store";
import { useProjectsStore } from "@/stores/projects-store";
import { useTasksStore } from "@/stores/tasks-store";
import { createDeferred } from "@/test/deferred";
import { makeTask } from "@/test/factories";
import type { AssetSheetStatusRow, AssetSheetType, ProjectData } from "@/types";
import { AssetGallery } from "./AssetGallery";
import type { GalleryAssetSource } from "./gallery-model";

const BUCKET = { character: "characters", scene: "scenes", prop: "props", product: "products" } as const;

function makeProject(overrides: Partial<ProjectData> = {}): ProjectData {
  return {
    title: "Demo",
    content_mode: "drama",
    style: "Anime",
    episodes: [],
    characters: {
      Lena: { description: "Girl in white", voice_style: "Cool", character_sheet: "characters/Lena.png" },
      Silas: { description: "Swordsman in black" },
    },
    scenes: { Courtyard: { description: "" } },
    props: { "Jade Pendant": { description: "Smooth white jade" } },
    products: { Thermos: { description: "Stainless steel", brand: "Warm", selling_points: ["Keeps hot for 12 hours"] } },
    ...overrides,
  };
}

function row(type: AssetSheetType, name: string): AssetSheetStatusRow {
  return {
    unit_id: `${type}/${name}`,
    asset_type: type,
    name,
    derivative: null,
    status: "current",
    description_missing: false,
    image_to_image: false,
  };
}

let server: ProjectData;

function Harness({
  assetType,
  readOnly,
  onGenerate,
}: {
  assetType: AssetSheetType;
  readOnly: boolean;
  onGenerate: (name: string) => unknown;
}) {
  const project = useProjectsStore((s) => s.currentProjectData);
  const assets = (project?.[BUCKET[assetType]] ?? {}) as Record<string, GalleryAssetSource>;
  return (
    <AssetGallery
      projectName="demo"
      assetType={assetType}
      title="Assets"
      assets={assets}
      readOnly={readOnly}
      onGenerate={onGenerate as (name: string) => void}
    />
  );
}

function renderGallery(assetType: AssetSheetType = "character", { readOnly = false } = {}) {
  const onGenerate = vi.fn();
  const location = memoryLocation({ path: "/", record: true });
  const wrap = (children: ReactNode) => (
    <Router hook={location.hook}>
      <LeaveGuardProvider>{children}</LeaveGuardProvider>
    </Router>
  );
  render(wrap(<Harness assetType={assetType} readOnly={readOnly} onGenerate={onGenerate} />));
  return { onGenerate };
}

async function openAsset(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(screen.getByRole("button", { name }));
  return screen.findByRole("dialog", { name });
}

/** Replace server data; subsequent refreshes receive this value. */
function patchServer(type: AssetSheetType, name: string, patch: Record<string, unknown>) {
  const bucket = server[BUCKET[type]] as unknown as Record<string, Record<string, unknown>>;
  bucket[name] = { ...bucket[name], ...patch };
  return Promise.resolve({ success: true });
}

describe("Asset detail sheet", () => {
  // The global setup seeds the zh locale; this file asserts English UI copy and restores zh afterwards.
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    server = makeProject();
    useAppStore.setState(useAppStore.getInitialState(), true);
    useProjectsStore.setState({ currentProjectName: "demo", currentProjectData: structuredClone(server) });
    vi.spyOn(API, "getProject").mockImplementation(() =>
      Promise.resolve({ project: structuredClone(server), scripts: {} }),
    );
    vi.spyOn(API, "getAssetSheetStatus").mockResolvedValue({
      assets: [row("character", "Lena"), row("character", "Silas")],
    });
    vi.spyOn(API, "updateCharacter").mockImplementation((_p, name, patch) => patchServer("character", name, patch));
    vi.spyOn(API, "updateProjectScene").mockImplementation((_p, name, patch) => patchServer("scene", name, patch));
    vi.spyOn(API, "updateProjectProp").mockImplementation((_p, name, patch) => patchServer("prop", name, patch));
    vi.spyOn(API, "updateProjectProduct").mockImplementation((_p, name, patch) => patchServer("product", name, patch));
  });

  afterEach(async () => {
    await i18n.changeLanguage("zh");
    vi.restoreAllMocks();
    useTasksStore.setState({ tasks: [], optimisticActive: new Set() });
    useConfigStatusStore.setState({ availableMediaTypes: [] });
    useProjectsStore.setState(useProjectsStore.getInitialState(), true);
  });

  it("disables sheet mutations while a card upload is still writing", async () => {
    const user = userEvent.setup();
    const pending = createDeferred<{ success: boolean }>();
    vi.spyOn(API, "uploadFile").mockReturnValue(pending.promise);
    renderGallery();
    const card = screen.getByRole("article", { name: "Lena" });
    const file = new File(["image"], "sheet.png", { type: "image/png" });
    fireEvent.change(within(card).getByLabelText("Upload Asset Sheet", { selector: "input" }), { target: { files: [file] } });

    const sheet = await openAsset(user, "Lena");
    expect(within(sheet).getByRole("button", { name: "Rename" })).toBeDisabled();
    expect(within(sheet).getByRole("button", { name: "Regenerate Asset Sheet" })).toBeDisabled();
    expect(within(sheet).getByRole("button", { name: "Upload reference image", hidden: true })).toBeDisabled();
    await act(() => pending.resolve({ success: true }));
    expect(within(sheet).getByRole("button", { name: "Rename" })).toBeEnabled();
  });

  it("keeps sibling writes disabled while the rename is in flight", async () => {
    const user = userEvent.setup();
    const pending = createDeferred<AssetRenameResult>();
    const result: AssetRenameResult = { success: true, dry_run: false, old_name: "Lena", new_name: "Lina", episodes: 0, references: 0, files: 1 };
    vi.spyOn(API, "renameProjectAsset").mockResolvedValueOnce({ ...result, dry_run: true }).mockReturnValueOnce(pending.promise);
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.click(within(sheet).getByRole("button", { name: "Rename" }));
    const input = within(sheet).getByRole("textbox", { name: "Rename" });
    await user.clear(input);
    await user.type(input, "Lina{Enter}");
    const confirm = await screen.findByRole("alertdialog", { name: 'Rename "Lena"?' });
    await user.click(within(confirm).getByRole("button", { name: "Rename" }));

    expect(within(sheet).getByRole("button", { name: "Regenerate Asset Sheet", hidden: true })).toBeDisabled();
    expect(within(sheet).getByRole("button", { name: "Upload reference image", hidden: true })).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("alertdialog", { name: 'Rename "Lena"?' })).toBeInTheDocument();
    await act(() => pending.resolve(result));
    expect(await screen.findByRole("dialog", { name: "Lina" })).toBeInTheDocument();
  });

  it("protects the character's mutations while a derivative task is occupying its files", async () => {
    const user = userEvent.setup();
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    act(() => useTasksStore.setState({ tasks: [makeTask({ project_name: "demo", task_type: "character_derivative", resource_id: "Lena/Battle Armor", status: "running" })] }));
    expect(within(sheet).getByRole("button", { name: "Rename" })).toBeDisabled();
    expect(within(sheet).getByRole("button", { name: "Regenerate Asset Sheet" })).toBeDisabled();
    expect(within(sheet).getByRole("button", { name: "Upload reference image", hidden: true })).toBeDisabled();
  });

  it("rechecks occupancy before confirming a TTS sample and shares the confirmation write with the sheet", async () => {
    const user = userEvent.setup();
    const pending = createDeferred<{ success: boolean; path: string; url: string }>();
    useConfigStatusStore.setState({ availableMediaTypes: ["audio"] });
    vi.spyOn(API, "getAudioBackendVoices").mockResolvedValue({ configured: true, provider_id: "dashscope", model: "tts", voices: [{ id: "Cherry", label: "Sunny" }] });
    vi.spyOn(API, "generateCharacterVoiceSample").mockResolvedValue({ success: true, task_id: "sample-1", deduped: false, message: "" });
    const confirmSample = vi.spyOn(API, "confirmCharacterVoiceSample").mockReturnValue(pending.promise);
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.click(within(sheet).getByRole("button", { name: "Optional: reference audio" }));
    await user.click(within(sheet).getByRole("button", { name: "Generate with TTS" }));
    const dialog = await screen.findByRole("dialog", { name: "Generate voice reference sample" });
    await waitFor(() => expect(within(dialog).getByRole("combobox", { name: "Voice" })).toHaveTextContent("Sunny"));
    await user.click(within(dialog).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(API.generateCharacterVoiceSample).toHaveBeenCalled());
    const succeeded = makeTask({ task_id: "sample-1", project_name: "demo", task_type: "voice_sample", resource_id: "Lena", status: "succeeded", result: { file_path: "audio/sample.wav" } });
    act(() => useTasksStore.getState().setTasks([succeeded]));
    const confirm = await within(dialog).findByRole("button", { name: "Confirm & save" });
    const running = makeTask({ project_name: "demo", task_type: "character", resource_id: "Lena", status: "running" });
    act(() => useTasksStore.getState().setTasks([succeeded, running]));
    expect(confirm).toBeDisabled();
    await user.click(confirm);
    expect(confirmSample).not.toHaveBeenCalled();
    act(() => useTasksStore.getState().setTasks([succeeded]));
    await user.click(confirm);
    expect(within(sheet).getByRole("button", { name: "Rename", hidden: true })).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Generate voice reference sample" })).toBeInTheDocument();
    await act(() => pending.resolve({ success: true, path: "characters/refs_audio/Lena.wav", url: "/audio.wav" }));
    expect(within(sheet).getByRole("button", { name: "Rename" })).toBeEnabled();
  });

  it("asks before switching to the next asset with unsaved changes, then saves and switches", async () => {
    const user = userEvent.setup();
    renderGallery();
    const sheet = await openAsset(user, "Lena");

    const description = within(sheet).getByRole("textbox", { name: "Description" });
    await user.clear(description);
    await user.type(description, "Girl in red");
    await user.click(within(sheet).getByRole("button", { name: "Next" }));

    const leave = await screen.findByRole("alertdialog", { name: '"Lena" has unsaved changes' });
    expect(API.updateCharacter).not.toHaveBeenCalled();
    await user.click(within(leave).getByRole("button", { name: "Save and switch" }));

    expect(await screen.findByRole("dialog", { name: "Silas" })).toBeInTheDocument();
    expect(API.updateCharacter).toHaveBeenCalledWith("demo", "Lena", { description: "Girl in red" });
  });

  it("asks before closing with unsaved changes and keeps nothing after discarding", async () => {
    const user = userEvent.setup();
    renderGallery();
    const sheet = await openAsset(user, "Lena");

    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");
    await user.click(within(sheet).getByRole("button", { name: "Close" }));
    const leave = await screen.findByRole("alertdialog", { name: '"Lena" has unsaved changes' });
    await user.click(within(leave).getByRole("button", { name: "Discard changes" }));

    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Lena" })).not.toBeInTheDocument());
    expect(API.updateCharacter).not.toHaveBeenCalled();
  });

  it("confirms the knock-on impact before saving and generating, and saves nothing when cancelled", async () => {
    const user = userEvent.setup();
    // Server still considers the sheet current; editing its description makes it outdated after saving.
    vi.spyOn(API, "getAssetRegenerationImpact").mockResolvedValue({
      stale: false,
      storyboards: 2,
      videos: 1,
      derivatives: 0,
    });
    const { onGenerate } = renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");

    await user.click(within(sheet).getByRole("button", { name: "Save and generate" }));
    let confirm = await screen.findByRole("alertdialog", { name: "Regenerate this sheet?" });
    expect(await within(confirm).findByText("Once regenerated, 2 storyboard images and 1 videos that use it become stale.")).toBeInTheDocument();
    await user.click(within(confirm).getByRole("button", { name: "Cancel" }));
    expect(API.updateCharacter).not.toHaveBeenCalled();
    expect(onGenerate).not.toHaveBeenCalled();

    await user.click(within(sheet).getByRole("button", { name: "Save and generate" }));
    confirm = await screen.findByRole("alertdialog", { name: "Regenerate this sheet?" });
    await user.click(await within(confirm).findByRole("button", { name: "Regenerate" }));

    await waitFor(() => expect(onGenerate).toHaveBeenCalledWith("Lena"));
    expect(API.updateCharacter).toHaveBeenCalledWith("demo", "Lena", { description: "Girl in white, with sword" });
    expect(vi.mocked(API.updateCharacter).mock.invocationCallOrder[0]).toBeLessThan(
      onGenerate.mock.invocationCallOrder[0],
    );
  });

  it("rechecks generation occupancy after the description finishes saving", async () => {
    const user = userEvent.setup();
    const saving = createDeferred<{ success: boolean }>();
    vi.mocked(API.updateCharacter).mockReturnValue(saving.promise);
    vi.spyOn(API, "getAssetRegenerationImpact").mockResolvedValue({ stale: false, storyboards: 0, videos: 0, derivatives: 0 });
    const { onGenerate } = renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");
    await user.click(within(sheet).getByRole("button", { name: "Save and generate" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Regenerate this sheet?" });
    await user.click(await within(confirm).findByRole("button", { name: "Regenerate" }));
    await waitFor(() => expect(API.updateCharacter).toHaveBeenCalled());
    act(() => useTasksStore.getState().setTasks([
      makeTask({ project_name: "demo", task_type: "character", resource_id: "Lena", status: "running" }),
    ]));
    await act(() => saving.resolve({ success: true }));
    expect(await within(sheet).findByText("Saved")).toBeInTheDocument();
    expect(onGenerate).not.toHaveBeenCalled();
    expect(useAppStore.getState().toast?.text).toBe("The asset image is being generated or edited. Try again when it finishes.");
  });

  it("aborts the impact check when the confirmation is cancelled before it answers", async () => {
    const user = userEvent.setup();
    let signal: AbortSignal | undefined;
    vi.spyOn(API, "getAssetRegenerationImpact").mockImplementation((_project, _type, _name, _derivative, options) => {
      signal = options?.signal;
      return new Promise(() => {});
    });
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");

    await user.click(within(sheet).getByRole("button", { name: "Save and generate" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Regenerate this sheet?" });
    expect(signal?.aborted).toBe(false);
    await user.click(within(confirm).getByRole("button", { name: "Cancel" }));

    expect(signal?.aborted).toBe(true);
    expect(API.updateCharacter).not.toHaveBeenCalled();
  });

  it("keeps save-and-preview unavailable while a save is still in flight", async () => {
    const user = userEvent.setup();
    const saving = createDeferred<{ success: boolean }>();
    vi.mocked(API.updateCharacter).mockReturnValue(saving.promise);
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");

    await user.click(within(sheet).getByRole("button", { name: "Save" }));
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with cloak");

    expect(within(sheet).getByRole("button", { name: "Save and preview" })).toBeDisabled();
    await act(() => saving.resolve({ success: true }));
  });

  it("warns that the fields were saved when refreshing the project afterwards fails", async () => {
    const user = userEvent.setup();
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");
    vi.mocked(API.getProject).mockRejectedValue(new Error("Network error"));

    await user.click(within(sheet).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(useAppStore.getState().toast).toMatchObject({
        text: "Done, but the page could not be refreshed. Reload to see the latest state",
        tone: "warning",
      }),
    );
  });

  it("saves the unsaved description before previewing the prompt", async () => {
    const user = userEvent.setup();
    const preview = vi.spyOn(API, "previewAssetPrompt").mockResolvedValue({
      text: "Style: Anime\nGirl in white, with sword",
      unavailable: null,
      is_text_form: true,
      warnings: [],
    });
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");

    await user.click(within(sheet).getByRole("button", { name: "Save and preview" }));

    expect(await screen.findByText(/Girl in white, with sword/, { selector: "pre" })).toBeInTheDocument();
    expect(API.updateCharacter).toHaveBeenCalledWith("demo", "Lena", { description: "Girl in white, with sword" });
    expect(preview).toHaveBeenCalledWith("demo", "character", "Lena", "Girl in white, with sword", expect.anything());
  });

  it("saves an unsaved scene occupancy toggle before previewing, so the preview renders the new choice", async () => {
    const user = userEvent.setup();
    const preview = vi.spyOn(API, "previewAssetPrompt").mockResolvedValue({
      text: "This sheet is an occupied environment reference",
      unavailable: null,
      is_text_form: true,
      warnings: [],
    });
    renderGallery("scene");
    const sheet = await openAsset(user, "Courtyard");
    await user.click(within(sheet).getByRole("switch", { name: "People in asset sheet" }));

    await user.click(within(sheet).getByRole("button", { name: "Save and preview" }));

    expect(await screen.findByText(/occupied environment reference/, { selector: "pre" })).toBeInTheDocument();
    const saved = vi.mocked(API.updateProjectScene).mock.invocationCallOrder[0];
    expect(API.updateProjectScene).toHaveBeenCalledWith("demo", "Courtyard", { occupancy: "occupied" });
    expect(saved).toBeLessThan(preview.mock.invocationCallOrder[0]);
  });

  it.each([
    {
      type: "character" as const,
      name: "Lena",
      edit: async (user: ReturnType<typeof userEvent.setup>, sheet: HTMLElement) => {
        await user.type(within(sheet).getByRole("textbox", { name: "Voice Style" }), " and firm");
      },
      call: () => expect(API.updateCharacter).toHaveBeenCalledWith("demo", "Lena", { voice_style: "Cool and firm" }),
    },
    {
      type: "scene" as const,
      name: "Courtyard",
      edit: async (user: ReturnType<typeof userEvent.setup>, sheet: HTMLElement) => {
        await user.type(within(sheet).getByRole("textbox", { name: "Description" }), "Moonlit courtyard");
      },
      call: () => expect(API.updateProjectScene).toHaveBeenCalledWith("demo", "Courtyard", { description: "Moonlit courtyard" }),
    },
    {
      type: "scene" as const,
      name: "Courtyard",
      edit: async (user: ReturnType<typeof userEvent.setup>, sheet: HTMLElement) => {
        await user.click(within(sheet).getByRole("switch", { name: "People in asset sheet" }));
      },
      call: () => expect(API.updateProjectScene).toHaveBeenCalledWith("demo", "Courtyard", { occupancy: "occupied" }),
    },
    {
      type: "prop" as const,
      name: "Jade Pendant",
      edit: async (user: ReturnType<typeof userEvent.setup>, sheet: HTMLElement) => {
        await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", carved with clouds");
      },
      call: () =>
        expect(API.updateProjectProp).toHaveBeenCalledWith("demo", "Jade Pendant", { description: "Smooth white jade, carved with clouds" }),
    },
    {
      type: "product" as const,
      name: "Thermos",
      edit: async (user: ReturnType<typeof userEvent.setup>, sheet: HTMLElement) => {
        await user.type(within(sheet).getByRole("textbox", { name: "Brand" }), "th");
        await user.type(within(sheet).getByRole("textbox", { name: "Selling Points" }), "{Enter}{Enter}One-tap lid");
      },
      call: () =>
        expect(API.updateProjectProduct).toHaveBeenCalledWith("demo", "Thermos", {
          brand: "Warmth",
          selling_points: ["Keeps hot for 12 hours", "One-tap lid"],
        }),
    },
  ])("edits a $type in the same editor and saves only the changed fields", async ({ type, name, edit, call }) => {
    const user = userEvent.setup();
    renderGallery(type);
    const sheet = await openAsset(user, name);

    await edit(user, sheet);
    await user.click(within(sheet).getByRole("button", { name: "Save" }));

    await waitFor(call);
    expect(await within(sheet).findByText("Saved")).toBeInTheDocument();
  });

  it("creates an asset from the blank editor and switches to its details", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "addCharacter").mockImplementation((_p, name, description, voiceStyle) => {
      server.characters[name] = { description, voice_style: voiceStyle };
      return Promise.resolve({ success: true });
    });
    renderGallery();

    await user.click(screen.getByRole("button", { name: "Add character" }));
    const form = await screen.findByRole("dialog", { name: "Add character" });
    expect(within(form).getByRole("button", { name: "Create" })).toBeDisabled();
    await user.type(within(form).getByRole("textbox", { name: "Name" }), " Ash ");
    await user.type(within(form).getByRole("textbox", { name: "Description" }), "Boy in blue");
    await user.click(within(form).getByRole("button", { name: "Create" }));

    const sheet = await screen.findByRole("dialog", { name: "Ash" });
    expect(API.addCharacter).toHaveBeenCalledWith("demo", "Ash", "Boy in blue", "");
    expect(within(sheet).getByRole("textbox", { name: "Description" })).toHaveValue("Boy in blue");
  });

  it("offers to restore a same-named asset from the project trash after creating it", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "addCharacter").mockImplementation((_p, name, description, voiceStyle) => {
      server.characters[name] = { description, voice_style: voiceStyle };
      return Promise.resolve({ success: true, trash_record_id: "rec-1" });
    });
    const restore = vi.spyOn(API, "restoreTrashRecord").mockResolvedValue({
      object: { kind: "asset", asset_type: "character", name: "Ash (1)" },
      restored: [],
      degraded: false,
      download_only: [],
    });
    renderGallery();

    await user.click(screen.getByRole("button", { name: "Add character" }));
    const form = await screen.findByRole("dialog", { name: "Add character" });
    await user.type(within(form).getByRole("textbox", { name: "Name" }), "Ash");
    await user.click(within(form).getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(useAppStore.getState().toast?.text).toBe('The project trash has a previously deleted "Ash". Restore it to get back its sheet and version history.'),
    );
    useAppStore.getState().toast?.action?.onClick();

    expect(restore).toHaveBeenCalledWith("demo", "rec-1");
    await waitFor(() =>
      expect(useAppStore.getState().toast).toMatchObject({
        text: 'Restored from the project trash as "Ash (1)". You can merge it into the existing asset.',
        tone: "success",
      }),
    );
  });

  it("only warns about the refresh when it fails after restoring the same-named asset", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "addCharacter").mockImplementation((_p, name, description, voiceStyle) => {
      server.characters[name] = { description, voice_style: voiceStyle };
      return Promise.resolve({ success: true, trash_record_id: "rec-1" });
    });
    vi.spyOn(API, "restoreTrashRecord").mockResolvedValue({
      object: { kind: "asset", asset_type: "character", name: "Ash (1)" },
      restored: [],
      degraded: false,
      download_only: [],
    });
    renderGallery();

    await user.click(screen.getByRole("button", { name: "Add character" }));
    const form = await screen.findByRole("dialog", { name: "Add character" });
    await user.type(within(form).getByRole("textbox", { name: "Name" }), "Ash");
    await user.click(within(form).getByRole("button", { name: "Create" }));
    await waitFor(() => expect(useAppStore.getState().toast?.action).toBeDefined());
    vi.mocked(API.getProject).mockRejectedValue(new Error("Network error"));
    useAppStore.getState().toast?.action?.onClick();

    await waitFor(() =>
      expect(useAppStore.getState().toast).toMatchObject({
        text: "Done, but the page could not be refreshed. Reload to see the latest state",
        tone: "warning",
      }),
    );
  });

  it("says the asset was created when refreshing the project afterwards fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "addCharacter").mockResolvedValue({ success: true });
    vi.mocked(API.getProject).mockRejectedValue(new Error("Network error"));
    renderGallery();

    await user.click(screen.getByRole("button", { name: "Add character" }));
    const form = await screen.findByRole("dialog", { name: "Add character" });
    await user.type(within(form).getByRole("textbox", { name: "Name" }), "Ash");
    await user.click(within(form).getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(useAppStore.getState().toast).toMatchObject({
        text: "Done, but the page could not be refreshed. Reload to see the latest state",
        tone: "warning",
      }),
    );
  });

  it("opens the created asset under its stored NFC name when the name was typed decomposed", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "addCharacter").mockImplementation((_p, name, description, voiceStyle) => {
      server.characters[name.trim().normalize("NFC")] = { description, voice_style: voiceStyle };
      return Promise.resolve({ success: true });
    });
    renderGallery();

    await user.click(screen.getByRole("button", { name: "Add character" }));
    const form = await screen.findByRole("dialog", { name: "Add character" });
    await user.type(within(form).getByRole("textbox", { name: "Name" }), "Gia\u0301p");
    await user.click(within(form).getByRole("button", { name: "Create" }));

    expect(await screen.findByRole("dialog", { name: "Giáp" })).toBeInTheDocument();
  });

  it("ignores closing while the create request is in flight and accepts it again once the request fails", async () => {
    const user = userEvent.setup();
    const creating = createDeferred<{ success: boolean }>();
    vi.spyOn(API, "addCharacter").mockReturnValue(creating.promise);
    renderGallery();

    await user.click(screen.getByRole("button", { name: "Add character" }));
    const form = await screen.findByRole("dialog", { name: "Add character" });
    await user.type(within(form).getByRole("textbox", { name: "Name" }), "Ash");
    await user.click(within(form).getByRole("button", { name: "Create" }));

    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Add character" })).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();

    await act(async () => creating.reject(new Error("Network error")));
    expect(await within(form).findByRole("alert")).toHaveTextContent("Network error");
    // Closing works again after request settlement: unsaved form content triggers the leave guard.
    await user.keyboard("{Escape}");
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
  });

  it("keeps the create form open and explains why when creating fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "addProjectProduct").mockRejectedValue(new Error('Product "Thermos" already exists'));
    renderGallery("product");

    await user.click(screen.getByRole("button", { name: "Add product" }));
    const form = await screen.findByRole("dialog", { name: "Add product" });
    await user.type(within(form).getByRole("textbox", { name: "Name" }), "Thermos");
    await user.click(within(form).getByRole("button", { name: "Create" }));

    expect(await within(form).findByRole("alert")).toHaveTextContent('Couldn\'t create the asset: Product "Thermos" already exists');
    expect(screen.getByRole("dialog", { name: "Add product" })).toBeInTheDocument();
  });

  it("keeps unsaved edits visible when the asset is removed elsewhere, and closes once they are discarded", async () => {
    const user = userEvent.setup();
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");

    // Agent deleted this character; pushed project data no longer contains it.
    const { Lena: _removed, ...rest } = server.characters;
    server.characters = rest;
    act(() => useProjectsStore.setState({ currentProjectData: structuredClone(server) }));

    expect(screen.getByRole("dialog", { name: "Lena" })).toBeInTheDocument();
    expect(within(sheet).getByRole("textbox", { name: "Description" })).toHaveValue("Girl in white, with sword");
    expect(within(sheet).getByText(/This asset was deleted or renamed/)).toBeInTheDocument();

    await user.click(within(sheet).getByRole("button", { name: "Discard changes" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Lena" })).not.toBeInTheDocument());
  });

  it("stays on the asset with its unsaved edits after renaming it", async () => {
    const user = userEvent.setup();
    const result = (dryRun: boolean): AssetRenameResult => ({
      success: true,
      dry_run: dryRun,
      old_name: "Lena",
      new_name: "Lina",
      episodes: 0,
      references: 0,
      files: 1,
    });
    vi.spyOn(API, "renameProjectAsset")
      .mockResolvedValueOnce(result(true))
      .mockImplementationOnce(() => {
        const { Lena: renamed, ...rest } = server.characters;
        server.characters = { ...rest, Lina: renamed };
        return Promise.resolve(result(false));
      });
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), ", with sword");

    await user.click(within(sheet).getByRole("button", { name: "Rename" }));
    const input = within(sheet).getByRole("textbox", { name: "Rename" });
    await user.clear(input);
    await user.type(input, "Lina{Enter}");
    const confirm = await screen.findByRole("alertdialog", { name: 'Rename "Lena"?' });
    await user.click(within(confirm).getByRole("button", { name: "Rename" }));

    const renamed = await screen.findByRole("dialog", { name: "Lina" });
    expect(within(renamed).getByRole("textbox", { name: "Description" })).toHaveValue("Girl in white, with sword");
    expect(useAppStore.getState().toast).toBeNull();
  });

  it("closes the renamed asset once it is removed, instead of falling back to a new asset under the old name", async () => {
    const user = userEvent.setup();
    const result = (dryRun: boolean): AssetRenameResult => ({
      success: true,
      dry_run: dryRun,
      old_name: "Lena",
      new_name: "Lina",
      episodes: 0,
      references: 0,
      files: 1,
    });
    vi.spyOn(API, "renameProjectAsset")
      .mockResolvedValueOnce(result(true))
      .mockImplementationOnce(() => {
        const { Lena: renamed, ...rest } = server.characters;
        server.characters = { ...rest, Lina: renamed };
        return Promise.resolve(result(false));
      });
    renderGallery();
    const sheet = await openAsset(user, "Lena");
    await user.click(within(sheet).getByRole("button", { name: "Rename" }));
    const input = within(sheet).getByRole("textbox", { name: "Rename" });
    await user.clear(input);
    await user.type(input, "Lina{Enter}");
    const confirm = await screen.findByRole("alertdialog", { name: 'Rename "Lena"?' });
    await user.click(within(confirm).getByRole("button", { name: "Rename" }));
    await screen.findByRole("dialog", { name: "Lina" });
    await waitFor(() => expect(useProjectsStore.getState().currentProjectData?.characters).toHaveProperty("Lina"));

    // Agent later deleted Lina and created an unrelated character with the old name Lena; it is not the viewed Lina.
    const { Lina: _removed, ...rest } = server.characters;
    server.characters = { ...rest, Lena: { description: "A new storyteller" } };
    act(() => useProjectsStore.setState({ currentProjectData: structuredClone(server) }));

    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Lina" })).not.toBeInTheDocument());
    expect(screen.queryByDisplayValue("A new storyteller")).not.toBeInTheDocument();
  });

  it("cancels only the rename when Escape is pressed in the name input", async () => {
    const user = userEvent.setup();
    renderGallery();
    const sheet = await openAsset(user, "Lena");

    await user.click(within(sheet).getByRole("button", { name: "Rename" }));
    await user.keyboard("{Escape}");

    expect(within(sheet).queryByRole("textbox", { name: "Rename" })).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Lena" })).toBeInTheDocument();
  });

  it("uploads a character's reference image right away", async () => {
    const user = userEvent.setup();
    const upload = vi.spyOn(API, "uploadFile").mockImplementation(() => {
      server.characters.Silas = { ...server.characters.Silas, reference_image: "characters/refs/Silas.png" };
      return Promise.resolve({ success: true });
    });
    renderGallery();
    const sheet = await openAsset(user, "Silas");

    const file = new File(["png"], "ref.png", { type: "image/png" });
    await user.upload(within(sheet).getByLabelText("Upload reference image"), file);

    await waitFor(() => expect(upload).toHaveBeenCalledWith("demo", "character_ref", file, "Silas"));
    expect(await within(sheet).findByRole("button", { name: 'View full size: Reference image of "Silas"' })).toBeInTheDocument();
    expect(within(sheet).queryByText("Unsaved changes")).not.toBeInTheDocument();
  });

  it("warns that the upload went through when refreshing the project afterwards fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "uploadFile").mockResolvedValue({ success: true });
    renderGallery();
    const sheet = await openAsset(user, "Silas");
    vi.mocked(API.getProject).mockRejectedValue(new Error("Network error"));

    await user.upload(within(sheet).getByLabelText("Upload reference image"), new File(["png"], "ref.png", { type: "image/png" }));

    await waitFor(() => expect(useAppStore.getState().toast).toMatchObject({ text: "Done, but the page could not be refreshed. Reload to see the latest state", tone: "warning" }));
  });

  it("reports the upload error without refreshing when no image went through", async () => {
    const user = userEvent.setup();
    vi.spyOn(API, "uploadFile").mockRejectedValue(new Error("File too large"));
    renderGallery();
    const sheet = await openAsset(user, "Silas");
    vi.mocked(API.getProject).mockClear();

    await user.upload(within(sheet).getByLabelText("Upload reference image"), new File(["png"], "ref.png", { type: "image/png" }));

    await waitFor(() => expect(useAppStore.getState().toast).toMatchObject({ text: "File too large", tone: "error" }));
    expect(API.getProject).not.toHaveBeenCalled();
  });

  it("collapses reference audio while the project binds voices by prompt", async () => {
    const user = userEvent.setup();
    renderGallery();
    const sheet = await openAsset(user, "Lena");

    const toggle = within(sheet).getByRole("button", { name: "Optional: reference audio" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(within(sheet).getByText(/reference audio has no effect/)).toBeInTheDocument();
  });

  it("confirms before deleting reference audio and disables the deletion once the character became busy", async () => {
    const user = userEvent.setup();
    server = makeProject({ character_voice_binding: "reference_audio" });
    server.characters.Lena.reference_audio = "characters/refs_audio/Lena.wav";
    useProjectsStore.setState({ currentProjectData: structuredClone(server) });
    const remove = vi.spyOn(API, "deleteCharacterReferenceAudio").mockResolvedValue({ success: true } as never);
    renderGallery();
    const sheet = await openAsset(user, "Lena");

    await user.click(within(sheet).getByRole("button", { name: "Delete audio sample" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Delete reference audio?" });
    // After confirmation opens, an Agent queues a task occupying the character.
    act(() =>
      useTasksStore.setState({
        tasks: [makeTask({ project_name: "demo", task_type: "character", media_type: "image", resource_id: "Lena", status: "running" })],
      }),
    );
    expect(within(confirm).getByRole("button", { name: "Delete" })).toBeDisabled();
    expect(remove).not.toHaveBeenCalled();

    act(() => useTasksStore.setState({ tasks: [] }));
    await user.click(within(confirm).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("demo", "Lena"));
  });

  it("disables generation until the asset has a description", async () => {
    const user = userEvent.setup();
    renderGallery("scene");
    const sheet = await openAsset(user, "Courtyard");

    expect(within(sheet).getByRole("button", { name: "Generate Asset Sheet" })).toBeDisabled();
    expect(within(sheet).getByText("Fill in the description first")).toBeInTheDocument();

    await user.type(within(sheet).getByRole("textbox", { name: "Description" }), "Moonlit courtyard");
    expect(within(sheet).getByRole("button", { name: "Save and generate" })).toBeEnabled();
  });

  it("shows the content without any write entry when read-only", async () => {
    const user = userEvent.setup();
    renderGallery("character", { readOnly: true });
    const sheet = await openAsset(user, "Lena");

    expect(within(sheet).getByRole("textbox", { name: "Description" })).toHaveAttribute("readonly");
    expect(within(sheet).getByRole("textbox", { name: "Voice Style" })).toHaveAttribute("readonly");
    expect(within(sheet).queryByRole("button", { name: /generat|upload|rename|save|preview|add|derivative/i })).not.toBeInTheDocument();
  });
});
