.DEFAULT_GOAL := help

PYTHON ?= python3.14
UV ?= uv
NPM ?= npm
VENV_PYTHON := .venv/bin/python

.PHONY: help doctor install app-requirements web-requirements build-web app web verify \
	tests test-python test-web sound-test check-model check-python-source \
	check-node check-app-deps check-web-deps

help:
	@printf '%s\n' \
		'Air Rhythm — run these commands from the repository root:' \
		'  make install            Set up Python and web dependencies; build the shared UI' \
		'  make app                Start the desktop app' \
		'  make web                Start the local web version' \
		'  make tests              Run Python and web unit tests (no camera needed)' \
		'  make verify             Build the shared UI and run both unit test suites' \
		'  make doctor             Check the required tools and local hand model' \
		'  make app-requirements   Install only Python dependencies' \
		'  make web-requirements   Install only web dependencies from the lockfile' \
		'  make build-web          Build the shared desktop/web interface' \
		'  make test-python        Run only Python unit tests' \
		'  make test-web           Run only web unit tests' \
		'  make sound-test         Play the melody without opening the camera'

check-model:
	@test -s models/hand_landmarker.task || { echo 'Missing models/hand_landmarker.task. Restore the complete repository checkout.' >&2; exit 1; }

check-python-source:
	@command -v "$(UV)" >/dev/null 2>&1 || command -v "$(PYTHON)" >/dev/null 2>&1 || { echo 'Install uv or Python 3.14, then retry.' >&2; exit 1; }

check-node:
	@command -v node >/dev/null 2>&1 || { echo 'Install Node.js 20.19.x or 22.12+.' >&2; exit 1; }
	@command -v "$(NPM)" >/dev/null 2>&1 || { echo 'Install npm with Node.js.' >&2; exit 1; }
	@node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (!((major === 20 && minor >= 19) || (major === 22 && minor >= 12) || major > 22)) { console.error("Node.js 20.19.x or 22.12+ is required; found " + process.version); process.exit(1) }'

doctor: check-model check-python-source check-node
	@echo 'Required tools and hand model: OK. Desktop gameplay is currently validated on macOS.'

# Run the setup steps in order, even if someone invokes make with -j.
install: doctor
	@$(MAKE) app-requirements
	@$(MAKE) web-requirements
	@$(MAKE) build-web
	@echo 'Setup complete. Run make app or make web.'

app-requirements: check-model check-python-source
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		if command -v "$(UV)" >/dev/null 2>&1; then \
			"$(UV)" venv .venv --python 3.14 --allow-existing; \
		else \
			"$(PYTHON)" -m venv .venv; \
		fi; \
	fi
	@$(MAKE) check-app-deps
	@if command -v "$(UV)" >/dev/null 2>&1; then \
		"$(UV)" pip install --python "$(VENV_PYTHON)" -r requirements.txt; \
	else \
		"$(VENV_PYTHON)" -m pip install -r requirements.txt; \
	fi

web-requirements: check-node
	@cd web && "$(NPM)" ci

check-app-deps:
	@test -x "$(VENV_PYTHON)" || { echo 'Python environment missing. Run make install or make app-requirements.' >&2; exit 1; }
	@"$(VENV_PYTHON)" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 14) else 1)' || { echo 'The existing .venv must use Python 3.14. Move it aside, then run make install.' >&2; exit 1; }

check-web-deps:
	@test -d web/node_modules || { echo 'Web dependencies missing. Run make install or make web-requirements.' >&2; exit 1; }

build-web: check-model check-node check-web-deps
	@cd web && "$(NPM)" run build

app: check-model check-app-deps check-node check-web-deps
	@"$(VENV_PYTHON)" app.py

web: check-model check-node check-web-deps
	@cd web && "$(NPM)" run dev

tests: test-python test-web

verify: build-web tests

test-python: check-app-deps
	@"$(VENV_PYTHON)" -m unittest discover -s tests

test-web: check-node check-web-deps
	@cd web && "$(NPM)" test

sound-test: check-app-deps check-model
	@"$(VENV_PYTHON)" app.py --sound-test
