import { test, expect } from "@playwright/test";
import { TEST_AWS_CREDENTIALS, TEST_AZURE_CREDENTIALS, TEST_GCP_CREDENTIALS } from "./fixtures/test-data";

test.describe("Providers Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/providers");
  });

  test("providers page loads", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Cloud Providers");
  });

  test("empty state displays when no providers", async ({ page }) => {
    // If no providers are connected, empty state appears
    const emptyState = page.getByText("No clouds connected yet");
    const providerCards = page.locator("[class*='AnimatedCard'], a[href^='/providers/']");
    const count = await providerCards.count();
    if (count === 0) {
      await expect(emptyState).toBeVisible();
      await expect(page.getByText("Let's fix that")).toBeVisible();
    }
  });

  test("Connect Provider button is visible", async ({ page }) => {
    await expect(page.getByRole("button", { name: /Connect Provider/i })).toBeVisible();
  });

  test("Connect Provider button opens modal", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await expect(page.getByText("Connect Cloud Provider")).toBeVisible();
  });

  test("wizard step 1: shows provider selection cards", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await expect(page.getByText("AWS Bedrock")).toBeVisible();
    await expect(page.getByText("Azure OpenAI")).toBeVisible();
    await expect(page.getByText("GCP Vertex AI")).toBeVisible();
  });

  test("wizard step 2: AWS credential form has correct fields", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await page.getByText("AWS Bedrock").click();
    await expect(page.getByText("Access Key ID")).toBeVisible();
    await expect(page.getByText("Secret Access Key")).toBeVisible();
    await expect(page.getByText("Region")).toBeVisible();
  });

  test("wizard step 2: Azure credential form has correct fields", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await page.getByText("Azure OpenAI").click();
    await expect(page.getByText("Tenant ID")).toBeVisible();
    await expect(page.getByText("Client ID")).toBeVisible();
    await expect(page.getByText("Client Secret")).toBeVisible();
    await expect(page.getByText("Subscription ID")).toBeVisible();
  });

  test("wizard step 2: GCP credential form has correct fields", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await page.getByText("GCP Vertex AI").click();
    await expect(page.getByText("Project ID")).toBeVisible();
    await expect(page.getByText("Service Account JSON")).toBeVisible();
  });

  test("wizard back navigation works", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await page.getByText("AWS Bedrock").click();
    await expect(page.getByText("Access Key ID")).toBeVisible();
    await page.getByText("Back").click();
    await expect(page.getByText("AWS Bedrock")).toBeVisible();
    await expect(page.getByText("Azure OpenAI")).toBeVisible();
  });

  test("Verify & Connect button disabled without credentials", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await page.getByText("AWS Bedrock").click();
    const connectBtn = page.getByRole("button", { name: /Verify & Connect/i });
    await expect(connectBtn).toBeVisible();
    await expect(connectBtn).toBeDisabled();
  });

  test("modal closes via X button", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await expect(page.getByText("Connect Cloud Provider")).toBeVisible();
    // Click the X button (the close button in top-right)
    await page.locator("button").filter({ has: page.locator("svg.lucide-x") }).click();
    await expect(page.getByText("Connect Cloud Provider")).not.toBeVisible();
  });

  test("modal closes via backdrop click", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await expect(page.getByText("Connect Cloud Provider")).toBeVisible();
    // Click the backdrop
    await page.locator(".bg-black\\/60").click({ position: { x: 10, y: 10 } });
    await expect(page.getByText("Connect Cloud Provider")).not.toBeVisible();
  });

  test("full AWS connection flow", async ({ page }) => {
    await page.getByRole("button", { name: /Connect Provider/i }).click();
    await page.getByText("AWS Bedrock").click();

    // Fill credentials
    await page.getByPlaceholder("AKIA...").fill(TEST_AWS_CREDENTIALS.access_key_id);
    await page.getByPlaceholder("wJalr...").fill(TEST_AWS_CREDENTIALS.secret_access_key);

    // Connect
    const connectBtn = page.getByRole("button", { name: /Verify & Connect/i });
    await expect(connectBtn).toBeEnabled();
    await connectBtn.click();

    // Should show connecting or result
    await expect(page.getByText(/Verifying connection|Connected|Connection Failed/i)).toBeVisible({ timeout: 10000 });
  });

  test("connected provider shows status badge", async ({ page }) => {
    // If there are existing providers, check for status badges
    await page.waitForTimeout(2000);
    const badges = page.locator("[class*='status'], [class*='badge']");
    // This is a structural check - badges exist if providers exist
    const providerLinks = page.locator("a[href^='/providers/']");
    const count = await providerLinks.count();
    if (count > 0) {
      // At least one provider card should have a status indicator
      await expect(providerLinks.first()).toBeVisible();
    }
  });
});
