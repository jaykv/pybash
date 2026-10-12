check: format lint test

SOURCE_FILES=pybash tests

install:
	uv sync

test:
	uv run pytest -vv -rs

format:
	uv run ruff format ${SOURCE_FILES}
	uv run ruff check ${SOURCE_FILES} --fix

lint:
	uv run ruff format --check --diff ${SOURCE_FILES}
	uv run ruff check ${SOURCE_FILES}
	uv run mypy

demo:
	cd examples && uv run pybash demo.py

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	uv build

.PHONY: check install test format lint demo clean package
