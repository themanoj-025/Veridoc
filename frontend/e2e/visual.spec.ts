/**
 * G8: Visual regression tests — Playwright screenshot comparison.
 *
 * Tests capture full-page screenshots of key views and compare them
 * against stored baselines. A visual diff fails the test, preventing
 * unintentional UI regressions (like the duplicate-declaration bug
 * that slipped through review in P0-2).
 *
 * Run:
 *   npx playwright test --grep @visual  (run visual tests only)
 *   npx playwright test --update-snapshots  (update baselines)
 *
 * Baselines are stored in frontend/e2e/snapshots/ and should be
 * committed to version control.
 */

import { test, expect } from "@playwright/test";

const TEST_EMAIL = `visual-test-${Date.now()}@example.com`;
const TEST_PASSWORD = "VisualTest123!";

test.describe("@visual Visual Regression Tests", () => {
  // Register a test user and store auth tokens
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await page.goto("/register");
    await page.waitForURL(/\/register/);

    await page.fill("#name", "Visual Test User");
    await page.fill("#email", TEST_EMAIL);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    await page.context().storageState({ path: "e2e/.auth/visual-user.json" });
    await page.close();
  });

  // ── Login page ──────────────────────────────────────────
  test("login page matches baseline", async ({ page }) => {
    await page.goto("/login");
    await page.waitForURL(/\/login/);

    // Wait for the page to fully render and fonts to load
    await page.waitForSelector("h1");
    await page.waitForTimeout(1000); // Allow animations to complete

    await expect(page).toHaveScreenshot("login-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.02, // Allow 2% diff for antialiasing
    });
  });

  // ── Register page ───────────────────────────────────────
  test("register page matches baseline", async ({ page }) => {
    await page.goto("/register");
    await page.waitForURL(/\/register/);
    await page.waitForSelector("h2");
    await page.waitForTimeout(1000);

    await expect(page).toHaveScreenshot("register-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
    });
  });

  // ── Dashboard (authenticated) ───────────────────────────
  test("dashboard page matches baseline", async ({ browser }) => {
    // Use authenticated context from stored state
    const context = await browser.newContext({
      storageState: "e2e/.auth/visual-user.json",
    });
    const page = await context.newPage();
    await page.goto("/dashboard");
    await page.waitForURL(/\/dashboard/);

    // Wait for the header to render
    await page.waitForSelector("text=Veridoc");
    await page.waitForTimeout(1500); // Allow skeletons to potentially resolve

    // Focus on the desktop layout (hide mobile-only elements)
    await page.setViewportSize({ width: 1280, height: 800 });

    await expect(page).toHaveScreenshot("dashboard-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.03, // Allow slightly more for dynamic content
    });
  });

  // ── Admin analytics page ────────────────────────────────
  test("admin page matches baseline", async ({ browser }) => {
    const context = await browser.newContext({
      storageState: "e2e/.auth/visual-user.json",
    });
    const page = await context.newPage();
    await page.goto("/admin");
    await page.waitForTimeout(2000); // Allow analytics to load

    await expect(page).toHaveScreenshot("admin-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.03,
    });
  });

  // ── Dark mode dashboard ────────────────────────────────
  test("dark mode dashboard matches baseline", async ({ browser }) => {
    const context = await browser.newContext({
      storageState: "e2e/.auth/visual-user.json",
    });
    const page = await context.newPage();
    await page.goto("/dashboard");
    await page.waitForSelector("text=Veridoc");

    // Toggle dark mode via localStorage
    await page.evaluate(() => {
      localStorage.setItem("theme", "dark");
      document.documentElement.classList.add("dark");
    });
    await page.waitForTimeout(500);

    await expect(page).toHaveScreenshot("dashboard-dark.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.03,
    });
  });
});
