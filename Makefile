check: lint test

SOURCE_FILES=pybash.py test_pybash.py

install:
	pip install -e .

test:
	pytest test_pybash.py -vv -rs

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache
	find . -name '*.pyc' -type f -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	python -m build

publish: package
	twine upload dist/*

format:
	autoflake --in-place --recursive --remove-all-unused-imports --ignore-init-module-imports ${SOURCE_FILES}
	isort --project=pybash ${SOURCE_FILES}
	black ${SOURCE_FILES}

lint:
	isort --check --diff --project=pybash ${SOURCE_FILES}
	black --check --diff ${SOURCE_FILES}
	flake8 $(SOURCE_FILES) --count --show-source --statistics
	flake8 $(SOURCE_FILES) --count --exit-zero --statistics

.PHONY: test clean