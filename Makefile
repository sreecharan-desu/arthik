.PHONY: env migrate seed start test

env:
	@echo "Recommended .env template:"
	@cat .env.example || echo "DATABASE_URL=...\nSECRET_KEY=...\nPAYU_MERCHANT_KEY=...\nPAYU_MERCHANT_SALT=...\nPAYU_BASE_URL=https://sandbox.payu.in\nPAYU_SUCCESS_URL=...\nPAYU_FAILURE_URL=...\nPAYU_WEBHOOK_SECRET=...\nGOOGLE_CLIENT_ID=...\nGOOGLE_CLIENT_SECRET=...\nPDF_TEMP_PATH=./tmp/pdfs\nAPP_URL=..."

migrate:
	alembic upgrade head

seed:
	npm run seed

seed-py:
	export PYTHONPATH=. && python scripts/seed_db.py

start:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/

clean:
	rm -rf __pycache__ .pytest_cache .venv node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +

lint:
	flake8 app scripts tests

format:
	black app scripts tests
