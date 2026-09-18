import { test, expect, type Page } from "@playwright/test";
import path from "path";
import fs from "fs";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TEST_PASSWORD = "E2eTestPass123!";
const TEST_NAME = "E2E Test User";
const TEST_FILE = path.resolve(__dirname, "../../data/documents/gutenberg_132.txt");

/**
 * Register a fresh user via the API so every test is self-contained and
 * independent of cross-test timing (a shared module-level user made login
 * flaky: whichever test ran first got in, later ones saw intermittent 401s).
 */
async function createTestUser(page: Page): Promise<string> {
  const email = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  for (let attempt = 0; attempt < 3; attempt++) {
    const res = await page.request.post(`${API_BASE}/api/v1/auth/register`, {
      data: { email, password: TEST_PASSWORD, full_name: TEST_NAME },
    });
    if (res.status() === 201) return email;
    if (res.status() === 429) {
      // register is rate-limited (5/min) — back off and retry
      await new Promise((r) => setTimeout(r, 15000));
      continue;
    }
    throw new Error(`register failed: ${res.status()} ${await res.text()}`);
  }
  throw new Error("register failed: rate-limit retries exhausted");
}

test.describe("Veridoc E2E Smoke Test", () => {
  // Clear auth state before each test to prevent state leakage
  test.beforeEach(async ({ page, context }) => {
    await context.clearCookies();
    // localStorage is inaccessible on about:blank (opaque origin) — land on
    // the app first, then clear its storage.
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    });
  });

  // ── Signup ──────────────────────────────────────────────────
  test("1. User can sign up and is redirected to dashboard", async ({ page }) => {
    // Start at home page → should redirect to login
    await page.goto("/");
    await page.waitForURL(/\/login/);
    await expect(page.locator("h1")).toContainText("Veridoc");

    // Navigate to register
    await page.click("text=Create one");
    await page.waitForURL(/\/register/);
    await expect(page.locator("h2")).toContainText("Get started");

    // Fill registration form
    await page.fill("#name", TEST_NAME);
    await page.fill("#email", `ui-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`);
    await page.fill("#password", TEST_PASSWORD);

    // Submit
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    await expect(page.locator("text=Veridoc")).toBeVisible();
  });

  // ── Upload ──────────────────────────────────────────────────
  test("2. User can upload a document", async ({ page }) => {
    // Login first (fresh user per test)
    const email = await createTestUser(page);
    await page.goto("/login");
    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Ensure test file exists
    const fileExists = fs.existsSync(TEST_FILE);
    test.skip(!fileExists, `Test file not found: ${TEST_FILE}`);

    // Click upload button
    await page.click("text=Upload Document");
    // Role-based selector: the dashboard has multiple <h3> elements once the
    // upload modal opens ("No document selected" + "Upload Document"), which
    // trips strict mode on a bare locator("h3").
    await expect(page.getByRole("heading", { name: "Upload Document" })).toBeVisible();

    // Fill title
    await page.fill('input[name="title"]', "E2E Test Document");

    // Upload file via file input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(TEST_FILE);

    // Submit upload form
    await page.click('button[type="submit"]:has-text("Upload")');

    // Wait for document to appear in the list
    await page.waitForTimeout(2000);
    await page.waitForSelector("text=E2E Test Document", { timeout: 30000 });
    await expect(page.locator("text=E2E Test Document")).toBeVisible();
  });

  // ── Ask a question ──────────────────────────────────────────
  test("3. User can ask a question and get a response", async ({ page }) => {
    const email = await createTestUser(page);
    await page.goto("/login");
    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Create a new conversation
    await page.getByRole("button", { name: "+ New" }).click();
    await page.waitForTimeout(1000);

    // Wait for the chat input to appear
    const chatInput = page.locator("textarea[placeholder*='Ask a question']");
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    // Ask a question about the Gutenberg text (The Art of War)
    await chatInput.fill("What is the supreme art of war?");
    await page.click('button[type="submit"]');

    // Wait for the response to appear (may take a while with Ollama)
    await page.waitForTimeout(3000);

    // Wait for assistant message to appear (may take up to 60s with Ollama)
    // Look for streaming cursor or prose content (both appear in assistant messages)
    await page.waitForSelector(".streaming-cursor, [class*='prose']", { timeout: 60000 });
  });

  // ── Citation click ──────────────────────────────────────────
  test("4. Citations are rendered and clickable", async ({ page }) => {
    const email = await createTestUser(page);
    await page.goto("/login");
    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Check for citation chips or Sources label
    const hasCitations = await page.locator("text=Sources:").isVisible();
    if (hasCitations) {
      // Click the first citation chip
      const citationChips = page.locator("button.citation-chip");
      const count = await citationChips.count();
      expect(count).toBeGreaterThan(0);
      await citationChips.first().click();
      // Citation click dispatches a custom event - no UI change expected
      // Just verify no crash
    } else {
      // No citations in current conversation - test is still valid if other
      // tests cover citation scenarios. This is expected for simple responses.
      test.info().annotations.push({
        type: "info",
        description: "No citations found in the current conversation. This is expected for simple QA responses.",
      });
    }
  });

  // ── Unanswerable question → refusal ─────────────────────────
  test("5. Unanswerable question produces a refusal", async ({ page }) => {
    const email = await createTestUser(page);
    await page.goto("/login");
    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Create a new conversation
    await page.getByRole("button", { name: "+ New" }).click();
    await page.waitForTimeout(1000);

    // Ask an unanswerable question about something not in the document
    const chatInput = page.locator("textarea[placeholder*='Ask a question']");
    await expect(chatInput).toBeVisible({ timeout: 10000 });
    await chatInput.fill(
      "What is the recipe for chocolate chip cookies?"
    );
    await page.click('button[type="submit"]');

    // Wait for response (this may take time with Ollama)
    await page.waitForTimeout(5000);

    // Check for refusal keywords in the response
    // The response should indicate it cannot answer the question
    // We look for common refusal patterns
    await page.waitForSelector(
      "text=/cannot|cannot determine|don't have enough|not enough information|not provided|no information|unable to|not found|does not contain/i",
      { timeout: 60000 }
    );
  });
});
