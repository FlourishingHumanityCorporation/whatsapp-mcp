PYTHON ?= python3

.PHONY: check python-compile go-test help test-policy

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
check: python-compile go-test test-policy
	@echo "whatsapp-mcp non-live checks passed"

python-compile:
	$(PYTHON) -c 'from pathlib import Path; [compile(p.read_text(), str(p), "exec") for p in sorted(Path("whatsapp-mcp-server").glob("*.py"))]'

go-test:
	cd whatsapp-bridge && go test ./...
