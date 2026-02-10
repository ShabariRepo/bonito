import { test, expect } from "@playwright/test";

test.describe("Governance Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/governance");
  });

  test("governance page loads", async ({ page }) => {
    // Should show governance/policy heading
    await expect(
      page.getByText(/governance|policies/i).first()
    ).toBeVisible();
  });

  test("create policy button exists", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /create|add|new/i }).first();
    await expect(createBtn).toBeVisible();
  });

  test("policy creation form opens", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /create|add|new/i }).first();
    await createBtn.click();

    // Should show a form/modal for creating a policy
    await expect(
      page.getByText(/policy name|name/i).first()
    ).toBeVisible({ timeout: 5000 });
  });

  test("policy types are available", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /create|add|new/i }).first();
    await createBtn.click();

    // Look for policy type selector
    await page.waitForTimeout(1000);
    const typeSelector = page.getByText(/spend|model|access|type/i).first();
    await expect(typeSelector).toBeVisible();
  });
});

test.describe("Governance - Policy Deletion", () => {
  test("delete requires confirmation", async ({ page }) => {
    await page.goto("/governance");

    // Check if there are existing policies with delete buttons
    const deleteBtn = page.getByRole("button", { name: /delete|remove/i }).first();
    if (await deleteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Set up dialog handler
      let dialogMessage = "";
      page.on("dialog", async (dialog) => {
        dialogMessage = dialog.message();
        await dialog.dismiss(); // Cancel to not actually delete
      });

      await deleteBtn.click();

      // Either a dialog or a confirmation UI should appear
      await page.waitForTimeout(1000);
      const confirmUI = page.getByText(/confirm|are you sure|cancel/i).first();
      const hasDialog = dialogMessage.length > 0;
      const hasConfirmUI = await confirmUI.isVisible().catch(() => false);

      // At least one form of confirmation should exist
      expect(hasDialog || hasConfirmUI).toBeTruthy();
    }
  });
});
