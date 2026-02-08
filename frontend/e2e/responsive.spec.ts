import { test, expect } from "@playwright/test";

test.describe("Responsive Design", () => {
  test("mobile viewport (375px) renders correctly", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await context.newPage();
    await page.goto("/dashboard");
    await expect(page.locator("h1")).toContainText("Dashboard");
    // Content should still be visible
    await expect(page.getByText("Connected Providers")).toBeVisible();
    await context.close();
  });

  test("tablet viewport (768px) renders correctly", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 768, height: 1024 } });
    const page = await context.newPage();
    await page.goto("/dashboard");
    await expect(page.locator("h1")).toContainText("Dashboard");
    await expect(page.getByText("Connected Providers")).toBeVisible();
    await context.close();
  });

  test("desktop viewport (1440px) renders correctly", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto("/dashboard");
    await expect(page.locator("h1")).toContainText("Dashboard");
    // Sidebar should be visible on desktop
    await expect(page.getByText("Bonito")).toBeVisible();
    await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
    await context.close();
  });

  test("sidebar behavior on mobile vs desktop", async ({ browser }) => {
    // Desktop: sidebar visible
    const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const desktopPage = await desktop.newPage();
    await desktopPage.goto("/dashboard");
    const sidebar = desktopPage.locator("aside");
    await expect(sidebar).toBeVisible();
    await desktop.close();

    // Mobile: sidebar may be hidden or collapsed
    const mobile = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const mobilePage = await mobile.newPage();
    await mobilePage.goto("/dashboard");
    // Content should still be accessible
    await expect(mobilePage.locator("h1")).toContainText("Dashboard");
    await mobile.close();
  });

  test("providers page responsive grid", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await context.newPage();
    await page.goto("/providers");
    await expect(page.locator("h1")).toContainText("Cloud Providers");
    await context.close();
  });
});
