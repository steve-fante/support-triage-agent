.PHONY: install demo test lint eval eval-llm compare clean

install:
	pip install -e ".[dev,llm]"

demo:
	python -m support_triage demo

test:
	pytest -q

lint:
	ruff check .

eval:
	python evals/run_eval.py --regles

eval-llm:
	python evals/run_eval.py

compare:
	python evals/run_eval.py --comparer --json metrics.json

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ metrics.json
