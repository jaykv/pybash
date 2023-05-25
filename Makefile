check: lint test

SOURCE_FILES=pybash test_pybash.py

install:
	pip install -e .

test:
	pytest test_pybash.py -vv -rs

dev:
	python run.py

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

shell:
	source $(poetry env info --path)/bin/activate

debug:
	python -m ideas examples.demo -a pybash.hook -s

.PHONY: test clean