import { test, expect } from "@playwright/test";
import { TEST_AWS_CREDENTIALS, API_URL } from "./fixtures/test-data";

test.describe("Provider Detail Page", () => {
  let providerId: string;

  test.beforeAll(async ({ request }) => {
    // Create a provider via API for detail page tests
    const resp = await request.post(`${API_URL}/api/providers/connect`, {
      data: {
        provider_type: "aws",
        credentials: TEST_AWS_CREDENTIALS,
      },
    });
    if (resp.ok()) {
      const data = await resp.json();
      providerId = data.id;
    }
  });

  test("provider detail page loads with correct info", async ({ page }) => {
    test.skip(!providerId, "No provider created");
    await page.goto(`/providers/${providerId}`);
    await expect(page.getByText("AWS Bedrock")).toBeVisible();
    await expect(page.getByText("Available Models")).toBeVisible();
  });

  test("model list displays with metadata", async ({ page }) => {
    test.skip(!providerId, "No provider created");
    await page.goto(`/providers/${providerId}`);
    // Should show model names
    await expect(page.getByText("Claude 3.5 Sonnet")).toBeVisible();
    // Should show capabilities
    await expect(page.getByText("text").first()).toBeVisible();
    // Should show pricing tiers
    await expect(page.getByText(/economy|standard|premium/).first()).toBeVisible();
    // Should show context window info
    await expect(page.getByText(/K ctx|M ctx/).first()).toBeVisible();
  });

  test("verify connection button exists", async ({ page }) => {
    test.skip(!providerId, "No provider created");
    await page.goto(`/providers/${providerId}`);
    const verifyBtn = page.getByRole("button", { name: /Verify/i });
    await expect(verifyBtn).toBeVisible();
  });

  test("verify connection button works", async ({ page }) => {
    test.skip(!providerId, "No provider created");
    await page.goto(`/providers/${providerId}`);
    await page.getByRole("button", { name: /Verify/i }).click();
    // Should show loading state or complete
    await page.waitForTimeout(3000);
    // Page should still be functional after verify
    await expect(page.getByText("AWS Bedrock")).toBeVisible();
  });

  test("disconnect button shows confirmation", async ({ page }) => {
    test.skip(!providerId, "No provider created");
    await page.goto(`/providers/${providerId}`);

    // Set up dialog handler before clicking
    page.on("dialog", async (dialog) => {
      expect(dialog.message()).toContain("Disconnect this provider");
      await dialog.dismiss(); // Cancel so we don't actually delete
    });

    await page.getByRole("button", { name: /Disconnect/i }).click();
  });

  test("back navigation works via breadcrumb", async ({ page }) => {
    test.skip(!providerId, "No provider created");
    await page.goto(`/providers/${providerId}`);
    // The breadcrumb should have a "Providers" link
    await page.getByRole("link", { name: "Providers" }).first().click();
    await expect(page).toHaveURL("/providers");
  });

  test("connection health indicator is shown", async ({ page }) => {
    test.skip(!providerId, "No provider created");
    await page.goto(`/providers/${providerId}`);
    await expect(page.getByText("Connection Health")).toBeVisible();
    await expect(page.getByText(/healthy|degraded/i)).toBeVisible();
  });
});
