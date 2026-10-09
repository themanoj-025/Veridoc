.PHONY: help up down build fetch-data gold-qa squad eval test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start the full stack
	docker compose up --build -d

down: ## Stop the stack
	docker compose down

logs: ## View logs
	docker compose logs -f

build: ## Build all Docker images
	docker compose build

fetch-data: ## Download/generate evaluation data (Phase 0)
	python scripts/fetch_eval_data.py

gold-qa: ## Generate gold Q&A pairs
	python scripts/build_gold_qa.py

squad: ## Download SQuAD 2.0 dev split
	python scripts/download_squad.py

eval: ## Run evaluation harness
	python scripts/run_eval.py

eval-compare: ## Run naive vs hybrid comparison
	python scripts/run_eval.py --compare

test-backend: ## Run backend tests
	cd backend && python -m pytest tests/ -v

lint-backend: ## Lint backend code
	cd backend && python -m flake8 app/ tests/ --max-line-length=100

lint-frontend: ## Lint frontend code
	cd frontend && npm run lint

clean: ## Clean up
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	rm -rf data/pgdata data/chroma data/minio data/ollama 2>/dev/null || true
