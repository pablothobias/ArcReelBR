import { describe, expect, it } from "vitest";
import { assetFieldsEqual, assetFieldsOf, assetFieldsPatch } from "./asset-editor-model";

describe("scene occupancy in the asset edit model", () => {
  it("reads an absent occupancy as empty", () => {
    expect(assetFieldsOf("scene", { description: "Classroom" }).occupied).toBe(false);
    expect(assetFieldsOf("scene", { description: "Classroom", occupancy: "occupied" }).occupied).toBe(true);
  });

  it("patches only a changed occupancy, as the stored value", () => {
    const saved = assetFieldsOf("scene", { description: "Classroom" });
    const occupied = { ...saved, occupied: true };

    expect(assetFieldsEqual(saved, occupied)).toBe(false);
    expect(assetFieldsPatch("scene", occupied, saved)).toEqual({ occupancy: "occupied" });
    expect(assetFieldsPatch("scene", saved, occupied)).toEqual({ occupancy: "empty" });
    expect(assetFieldsPatch("scene", saved, saved)).toEqual({});
  });

  it("never sends occupancy for other asset types", () => {
    const saved = assetFieldsOf("prop", { description: "Lamp" });
    expect(assetFieldsPatch("prop", { ...saved, occupied: true }, saved)).toEqual({});
  });
});
