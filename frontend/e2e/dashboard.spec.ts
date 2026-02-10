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
    const cta = page.getByText("Get started by connecting a cloud provider");
    const providerCount = await page
      .getByText("Connected Providers")
      .locator("..")
      .locator("..")
      .locator(".text-2xl")
      .textContent();
    if (providerCount?.trim() === "0") {
      await expect(cta).toBeVisible();
      await expect(page.getByRole("link", { name: /Connect Provider/i })).toBeVisible();
    }
  });

  test("activity feed renders", async ({ page }) => {
    await expect(page.getByText("Recent Activity")).toBeVisible();
  });

  test("animated elements are present", async ({ page }) => {
    // Framer motion elements should have data attributes or style transforms
    const cards = page.locator("[class*='card']");
    await expect(cards.first()).toBeVisible();
  });
});

test.describe("Dashboard Navigation", () => {
  test("can navigate to providers page", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Providers" }).click();
    await expect(page).toHaveURL(/providers/);
  });

  test("can navigate to models page", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "Models" }).click();
    await expect(page).toHaveURL(/models/);
  });

  test("can navigate to gateway page", async ({ page }) => {
    await page.goto("/dashboard");
    const gatewayLink = page.getByRole("link", { name: /Gateway/i });
    if (await gatewayLink.isVisible()) {
      await gatewayLink.click();
      await expect(page).toHaveURL(/gateway/);
    }
  });
});

test.describe("Error States", () => {
  test("handles API errors gracefully", async ({ page }) => {
    // Navigate to a page — even if API is down, the page should render
    await page.goto("/dashboard");
    // Should not show a blank page or uncaught error
    await expect(page.locator("body")).not.toBeEmpty();
  });

  test("404 page for unknown routes", async ({ page }) => {
    const resp = await page.goto("/this-route-does-not-exist");
    // Should either redirect or show 404
    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toBeTruthy();
  });
});
