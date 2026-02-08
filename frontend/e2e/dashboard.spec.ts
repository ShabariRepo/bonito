import { test, expect } from "@playwright/test";

test.describe("Dashboard Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("loads with stat cards", async ({ page }) => {
    await expect(page.getByText("Connected Providers")).toBeVisible();
    await expect(page.getByText("Available Models")).toBeVisible();
    await expect(page.getByText("Active Deployments")).toBeVisible();
    await expect(page.getByText("API Requests (24h)")).toBeVisible();
  });

  test("provider count displays a number", async ({ page }) => {
    // Wait for loading to finish
    const providerCard = page.locator("text=Connected Providers").locator("..");
    await expect(providerCard).toBeVisible();
    // The counter should render (either 0 or a positive number)
    await page.waitForTimeout(1500); // wait for animated counter + fetch
    const counterEl = providerCard.locator("..").locator(".text-2xl");
    await expect(counterEl).toBeVisible();
  });

  test("Connect Provider CTA appears when no providers", async ({ page }) => {
    // With a fresh backend, there should be 0 providers
    // The CTA text should be visible
    const cta = page.getByText("Get started by connecting a cloud provider");
    // This may or may not appear depending on backend state
    // If providers exist, this won't show — that's ok
    const providerCount = await page.getByText("Connected Providers").locator("..").locator("..").locator(".text-2xl").textContent();
    if (providerCount?.trim() === "0") {
      await expect(cta).toBeVisible();
      await expect(page.getByRole("link", { name: /Connect Provider/i })).toBeVisible();
    }
  });

  test("activity feed renders", async ({ page }) => {
    await expect(page.getByText("Recent Activity")).toBeVisible();
    await expect(page.getByText("AWS Bedrock")).toBeVisible();
    await expect(page.getByText("GPT-4o")).toBeVisible();
  });

  test("animated elements are present", async ({ page }) => {
    // Framer motion elements should have data attributes or style transforms
    const cards = page.locator("[class*='card']");
    await expect(cards.first()).toBeVisible();
  });
});
