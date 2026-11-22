# Research-Programs reproducibility. `make all` rebuilds every table, chart and
# the brief from a fresh clone (needs python3.13, node >= 20, git, network for
# the first pip / EasyOCR / model download). No API key is needed: live model
# runs are a separate, opt-in target (`make live`).

PY      := research/.venv/bin/python
WT      := $(shell mktemp -d 2>/dev/null)
.PHONY: all venv data models eval baselines live test clean-results

all: venv data models eval baselines test

venv: research/.venv/.ok
research/.venv/.ok: requirements-research.txt ml-service/requirements.txt
	python3.13 -m venv research/.venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements-research.txt
	cd backend && npm ci --silent
	touch $@

data: venv
	$(PY) dataset/gulf_synthetic/generate.py

# v1.0-fyp binaries from the GitHub release into research/artifacts/fetched,
# then the multi-currency experiments.
models: venv
	$(PY) -c "import sys, pathlib; sys.path.insert(0, 'ml-service'); import fetch_models as f; \
	f.MODELS_DIR = pathlib.Path('research/artifacts/fetched').resolve(); sys.exit(f.main())"
	SKIP_MODEL_FETCH=1 $(PY) research/models/multicurrency.py

# BEFORE = the v1.0-fyp tag and main just before the currency fix, each checked
# out into a temporary worktree (the tag is only read, never moved). AFTER = this tree.
eval: data
	git worktree add --detach $(WT)/v1.0-fyp v1.0-fyp
	git worktree add --detach $(WT)/pre-v1.1 ed232ab
	$(PY) research/eval/run_eval.py --dry-run --code-root $(WT)/v1.0-fyp --name before_v1.0_dryrun
	$(PY) research/eval/run_eval.py --dry-run --code-root $(WT)/pre-v1.1 --name pre_v1.1_main_dryrun
	$(PY) research/eval/run_eval.py --dry-run --name after_dryrun
	git worktree remove --force $(WT)/v1.0-fyp
	git worktree remove --force $(WT)/pre-v1.1

baselines: data
	$(PY) research/eval/run_eval.py --extractor easyocr --name baseline_easyocr
	$(PY) research/eval/run_eval.py compare before_v1.0_dryrun pre_v1.1_main_dryrun after_dryrun \
		baseline_easyocr gemini_schema_currency_live

# Opt-in, billed: needs GEMINI_API_KEY exported in the shell. Runs the four
# prompt ablations on the current code.
live: data
	@test -n "$$GEMINI_API_KEY" || (echo "export GEMINI_API_KEY first"; exit 1)
	for p in no_schema schema_no_currency schema_currency arabic_hints; do \
		$(PY) research/eval/run_eval.py --extractor gemini --prompt $$p --name gemini_$${p}_live; done
	$(PY) research/eval/run_eval.py compare before_v1.0_dryrun after_dryrun baseline_easyocr \
		gemini_no_schema_live gemini_schema_no_currency_live gemini_schema_currency_live gemini_arabic_hints_live


test: venv
	$(PY) -m pytest research/tests ml-service/tests -q
	cd backend && npm test --silent
