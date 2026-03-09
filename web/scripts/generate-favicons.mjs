import sharp from "sharp";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const dir = dirname(fileURLToPath(import.meta.url));
const svgPath = resolve(dir, "../src/app/icon.svg");
const svg = readFileSync(svgPath);

// Apple touch icon at 180x180
await sharp(svg, { density: 450 })
  .resize(180, 180)
  .png()
  .toFile(resolve(dir, "../src/app/apple-icon.png"));

console.log("Done: apple-icon.png (180x180)");

// Favicon intermediate at 32x32
await sharp(svg, { density: 450 })
  .resize(32, 32)
  .png()
  .toFile(resolve(dir, "../src/app/favicon-32.png"));

console.log("Done: favicon-32.png (32x32)");
