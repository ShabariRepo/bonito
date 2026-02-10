import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveURL(/login/);
    // Should have email and password fields
    await expect(page.getByPlaceholder(/email/i).or(page.getByLabel(/email/i))).toBeVisible();
    await expect(page.getByPlaceholder(/password/i).or(page.getByLabel(/password/i))).toBeVisible();
  });

  test("login page has sign in button", async ({ page }) => {
    await page.goto("/login");
    const signInBtn = page.getByRole("button", { name: /sign in|log in/i });
    await expect(signInBtn).toBeVisible();
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/login");

    // Fill in invalid credentials
    const emailInput = page.getByPlaceholder(/email/i).or(page.getByLabel(/email/i));
    const passwordInput = page.getByPlaceholder(/password/i).or(page.getByLabel(/password/i));

    await emailInput.fill("invalid@test.com");
    await passwordInput.fill("WrongPassword123");

    // Submit
    const signInBtn = page.getByRole("button", { name: /sign in|log in/i });
    await signInBtn.click();

    // Should show error message (either toast, banner, or inline)
    await expect(
      page.getByText(/invalid|error|failed|incorrect/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("register page loads", async ({ page }) => {
    await page.goto("/register");
    await expect(page).toHaveURL(/register/);
    // Should have name, email, password fields
    await expect(page.getByPlaceholder(/name/i).or(page.getByLabel(/name/i))).toBeVisible();
    await expect(page.getByPlaceholder(/email/i).or(page.getByLabel(/email/i))).toBeVisible();
  });

  test("register page validates password strength", async ({ page }) => {
    await page.goto("/register");

    const nameInput = page.getByPlaceholder(/name/i).or(page.getByLabel(/name/i));
    const emailInput = page.getByPlaceholder(/email/i).or(page.getByLabel(/email/i));
    const passwordInput = page.getByPlaceholder(/password/i).or(page.getByLabel(/password/i));

    await nameInput.fill("Test User");
    await emailInput.fill("test@example.com");
    await passwordInput.fill("weak"); // Too short, no uppercase, no digit

    // Submit
    const submitBtn = page.getByRole("button", { name: /sign up|register|create/i });
    await submitBtn.click();

    // Should show password validation error
    await expect(
      page.getByText(/password|characters|uppercase|number/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("login page has link to register", async ({ page }) => {
    await page.goto("/login");
    const registerLink = page.getByRole("link", { name: /sign up|register|create account/i });
    await expect(registerLink).toBeVisible();
  });

  test("register page has link to login", async ({ page }) => {
    await page.goto("/register");
    const loginLink = page.getByRole("link", { name: /sign in|log in|already have/i });
    await expect(loginLink).toBeVisible();
  });
});
