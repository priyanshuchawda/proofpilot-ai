import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const cssRoot = join(process.cwd(), ".next", "static");

function cssFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return cssFiles(path);
    }
    return entry.name.endsWith(".css") ? [path] : [];
  });
}

const compiledCss = cssFiles(cssRoot)
  .map((path) => readFileSync(path, "utf8"))
  .join("\n");

const expectedUtilities = [".rounded-lg", ".p-5", ".grid"];
const missingUtilities = expectedUtilities.filter((utility) => !compiledCss.includes(utility));

if (missingUtilities.length > 0) {
  throw new Error(
    `Tailwind utility CSS was not generated: ${missingUtilities.join(", ")}. Check the Tailwind build integration.`,
  );
}

console.log("PASS: Tailwind utility CSS is present in the production build.");
