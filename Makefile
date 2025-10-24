.PHONY: format
format:
	treefmt

.PHONY: shell
shell:
	devenv shell

.PHONY: test
test: check

check:
	black --check src
	isort -c src
	flake8 src
	mypy --show-error-codes --strict src
