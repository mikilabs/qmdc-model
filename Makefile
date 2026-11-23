.PHONY: test lint-test build bump bump-patch bump-minor bump-major

# Full test run.
test:
	uv run pytest -q

# Run the data-driven metamodel linter suite only.
lint-test:
	uv run pytest tests/test_lint.py -q

# Build sdist + wheel into dist/.
build:
	rm -rf dist && uv build

# Bump the version in pyproject.toml and refresh uv.lock.
# Release = bump -> commit -> push tag v<version> (see README, "Releasing").
bump: bump-patch

bump-patch bump-minor bump-major: bump-%:
	python3 scripts/bump_version.py $*
	uv lock
