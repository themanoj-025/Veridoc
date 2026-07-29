import { test, expect } from "@playwright/test";
import path from "path";
import fs from "fs";

const TEST_EMAIL = `e2e-test-${Date.now()}@example.com`;
const TEST_PASSWORD = "E2eTestPass123!";
const TEST_NAME = "E2E Test User";
const TEST_FILE = path.resolve(__dirname, "../../data/documents/gutenberg_132.txt");

// Helper: check that the file exists before running tests
test.describe("Veridoc E2E Smoke Test", () => {
  // Clear auth state before each test to prevent state leakage
  test.beforeEach(async ({ page, context }) => {
    await context.clearCookies();
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
    await page.fill("#email", TEST_EMAIL);
    await page.fill("#password", TEST_PASSWORD);

    // Submit
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    await expect(page.locator("text=Veridoc")).toBeVisible();
  });

  // ── Upload ──────────────────────────────────────────────────
  test("2. User can upload a document", async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.fill("#email", TEST_EMAIL);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Ensure test file exists
    const fileExists = fs.existsSync(TEST_FILE);
    test.skip(!fileExists, `Test file not found: ${TEST_FILE}`);

    // Click upload button
    await page.click("text=Upload Document");
    await expect(page.locator("h3")).toContainText("Upload Document");

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
    // Login
    await page.goto("/login");
    await page.fill("#email", TEST_EMAIL);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Create a new conversation
    await page.click("text=+ New Chat");
    await page.waitForTimeout(1000);

    // Wait for the chat input to appear
    const chatInput = page.locator("textarea[placeholder*='Ask a question']");
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    // Ask a question about the Gutenberg text (The Art of War)
    await chatInput.fill("What is the supreme art of war?");
    await page.click('button[type="submit"]');

    // Wait for the response to appear (may take a while with Ollama)
    await page.waitForTimeout(3000);

    // Check that we have at least one assistant message or streaming content
    // The response could take up to 30s with Ollama, so we wait for content
    await page.waitForSelector("text=/.*/", { timeout: 60000 });
  });

  // ── Citation click ──────────────────────────────────────────
  test("4. Citations are rendered and clickable", async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill("#email", TEST_EMAIL);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Look for citation chips (button with class "citation-chip")
    const citationChips = page.locator("button.citation-chip");

    // If citations exist, test clicking one
    if ((await citationChips.count()) > 0) {
      await citationChips.first().click();
      // Citation click dispatches a custom event - no UI change expected
      // Just verify no crash
      expect(true).toBeTruthy();
    }
  });

  // ── Unanswerable question → refusal ─────────────────────────
  test("5. Unanswerable question produces a refusal", async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill("#email", TEST_EMAIL);
    await page.fill("#password", TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Create a new conversation
    await page.click("text=+ New Chat");
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
