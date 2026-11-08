import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

type Icon = { src: string; sizes: string; type: string; purpose: string };
const publicFile = (name: string) => resolve(process.cwd(), "public", name);

describe("installed app icons", () => {
  it("supplies correctly sized raster icons and maskable variants", () => {
    const manifest = JSON.parse(readFileSync(publicFile("site.webmanifest"), "utf8")) as { icons: Icon[] };
    for (const purpose of ["any", "maskable"]) {
      for (const size of [192, 512]) {
        const icon = manifest.icons.find((item) => item.purpose === purpose && item.sizes === `${size}x${size}`);
        expect(icon?.type).toBe("image/png");
        expect(icon?.src.startsWith("/rafacena-")).toBe(true);
        const png = readFileSync(publicFile(icon!.src.slice(1)));
        expect(png.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))).toBe(true);
        expect([png.readUInt32BE(16), png.readUInt32BE(20)]).toEqual([size, size]);
      }
    }
  });

  it("provides a square Apple touch icon", () => {
    const png = readFileSync(publicFile("rafacena-apple-touch-icon.png"));
    expect([png.readUInt32BE(16), png.readUInt32BE(20)]).toEqual([180, 180]);
  });
});
