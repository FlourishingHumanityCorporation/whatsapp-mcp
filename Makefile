PYTHON ?= $(shell ls $(HOME)/.pyenv/versions/3.1[2-9]*/bin/python3 2>/dev/null | sort -r | head -1 || echo python3)

.PHONY: architecture-check architecture-contract-test check python-compile go-test help test-policy

help:
	@echo "make check - non-live Python syntax compile and Go package compile"


# Changed-file test policy gate. Runs in repo-native validation so marker,
# skip/xfail, and validation-lane policy drift cannot hide until a fleet scan.
test-policy:
	@repo=$$PWD; \
	files=$$(git -C "$$repo" ls-files -co --exclude-standard -- .); \
	if [ -z "$$files" ]; then \
		echo "test-policy: no repo files to scan"; \
	else \
		python3 "$$HOME/CodeProjects/.meta/scripts/test-policy-changed-files" --repo "$$repo" $$files; \
	fi

architecture-contract-test:
	$(PYTHON) -m unittest discover -s tests/architecture/unit -p 'test_*.py' -v 2>&1

# Read-path behavior. Non-live by contract: exercises whatsapp.py against a
# throwaway fixture store, never the operator's message store or the bridge.
behavior-test:
	$(PYTHON) -m unittest discover -s tests/behavior/unit -p 'test_*.py' -v 2>&1

architecture-check:
	APPCHECK_PROJECTS_JSON="$(CURDIR)/.appcheck/projects.json" \
	APPCHECK_CODEPROJECTS_ROOT="$(CURDIR)" \
	appcheck run whatsapp-mcp --category architecture

check: python-compile go-test test-policy architecture-contract-test architecture-check behavior-test
	@echo "whatsapp-mcp non-live checks passed"

python-compile:
	$(PYTHON) -c 'from pathlib import Path; [compile(p.read_text(), str(p), "exec") for p in sorted(Path("whatsapp-mcp-server").glob("*.py"))]'

go-test:
	cd whatsapp-bridge && go test ./...
