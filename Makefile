.PHONY: test lint-test

# Run the data-driven metamodel linter suite.
lint-test:
	uv run pytest tests/test_lint.py -q

# Full test run (currently just the linter suite; grows as more suites are added).
test: lint-test
