.PHONY: up down test backend frontend

up:        ## Start the full stack (db, api, web, worker)
	docker compose up --build

down:
	docker compose down

test:      ## Run the backend test suite
	cd backend && pytest

backend:   ## Run the API locally (SQLite)
	cd backend && uvicorn app.main:app --reload

frontend:  ## Run the web app locally
	cd frontend && npm run dev
