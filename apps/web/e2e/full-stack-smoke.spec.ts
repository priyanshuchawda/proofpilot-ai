import { expect, test } from "@playwright/test";

test.skip(
  process.env.RUN_FULL_STACK_SMOKE !== "1",
  "Docker-backed full-stack smoke is opt-in only.",
);

test("runs upload through worker indexing and returns a real cited answer", async ({ page }) => {
  test.setTimeout(120_000);
  const runId = Date.now().toString();
  const workspaceName = `Full-stack smoke ${runId}`;
  const filename = `public-smoke-${runId}.md`;

  await page.goto("/");

  await expect(page.getByText("Use public demo documents only.")).toBeVisible();
  await expect(page.getByText("API healthy")).toBeVisible({ timeout: 30_000 });

  await page.getByLabel("Workspace name").fill(workspaceName);
  await page.getByLabel("Workspace description").fill("Opt-in local smoke workspace");
  await page.getByRole("button", { name: "Create workspace" }).click();

  await expect(page.getByRole("button", { name: workspaceName })).toBeVisible({
    timeout: 15_000,
  });

  await page.getByLabel("Upload document").setInputFiles({
    buffer: Buffer.from(
      [
        "# Approval",
        "The rollout requires documented public evidence before approval.",
        "The launch owner is ProofPilot QA.",
      ].join("\n"),
    ),
    mimeType: "text/markdown",
    name: filename,
  });

  const documentCard = page.locator("article").filter({ hasText: filename });
  await expect(documentCard).toContainText("ready", { timeout: 75_000 });
  await expect(documentCard).toContainText("chunks");

  await page.getByRole("button", { name: "Verified Mode" }).click();
  await page
    .getByLabel("Question")
    .fill("What does the rollout require before approval?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(
    page.getByText("The rollout requires documented public evidence before approval.").first(),
  ).toBeVisible({ timeout: 45_000 });
  await expect(page.getByRole("region", { name: "Retrieval trace" })).toContainText(
    "route_document_verified",
  );
  await expect(page.getByRole("region", { name: "Retrieval trace" })).toContainText(
    "Query run",
  );
  await expect(page.getByRole("region", { name: "Retrieval trace" })).toContainText(
    "retrieval_ms",
  );
});
