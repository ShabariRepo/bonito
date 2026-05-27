import { test, expect } from "@playwright/test";

test.describe("Settings Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/settings");
  });

  test("settings page loads with title", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Settings");
  });

  test("shows subscription tier badge", async ({ page }) => {
    // The tier card should show a Crown icon and tier label
    await expect(
      page.getByText(/Free|Pro|Enterprise|Scale/).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows Gateway API Keys section", async ({ page }) => {
    await expect(page.getByText("Gateway API Keys")).toBeVisible();
    // Should have the info banner about bn- keys
    await expect(
      page.getByText(/Gateway keys.*bn-/i).first()
    ).toBeVisible();
  });

  test("shows Personal Access Tokens section", async ({ page }) => {
    await expect(page.getByText("Personal Access Tokens")).toBeVisible();
    // Should have the info banner about bp- tokens
    await expect(
      page.getByText(/Personal access tokens.*bp-/i).first()
    ).toBeVisible();
  });

  test("gateway key create input exists", async ({ page }) => {
    const keyInput = page.getByPlaceholder("Key name...");
    await expect(keyInput).toBeVisible();
    const generateBtn = page.getByRole("button", { name: /Generate Key/i });
    await expect(generateBtn).toBeVisible();
  });

  test("PAT create input exists", async ({ page }) => {
    const tokenInput = page.getByPlaceholder("Token name...");
    await expect(tokenInput).toBeVisible();
    const generateBtn = page.getByRole("button", { name: /Generate Token/i });
    await expect(generateBtn).toBeVisible();
  });

  test("notifications section exists", async ({ page }) => {
    await expect(page.getByText("Notifications")).toBeVisible();
  });

  test("security section exists", async ({ page }) => {
    await expect(page.getByText("Security")).toBeVisible();
  });
});
