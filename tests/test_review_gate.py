from webtest_agent.generation.review_gate import review_file

_VALID = """import { test, expect } from '@playwright/test';

test.describe('home', () => {
  test('loads', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Home/);
  });
});
"""

_BLOATED = """import { test, expect } from '@playwright/test';

class HomePageObject {
  constructor(page) { this.page = page; }
}

function customExpect(actual, expected) {
  if (actual !== expected) throw new Error('mismatch');
}

test.describe('home', () => {
  test('loads', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    while (true) {
      break;
    }
    expect(page).toBeTruthy();
  });
});
"""


def test_review_gate_accepts_idiomatic_file():
    result = review_file(_VALID, "home.spec.ts")
    assert result.passed
    assert result.violations == []


def test_review_gate_rejects_bloated_file():
    result = review_file(_BLOATED, "home.spec.ts")
    assert not result.passed
    assert len(result.violations) >= 3  # waitForTimeout, while(true), page-object class, custom assertion


def test_review_gate_flags_missing_required_pieces():
    result = review_file("const x = 1;", "empty.spec.ts")
    assert not result.passed
    assert any("must import" in v for v in result.violations)
