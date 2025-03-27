.PHONY: setup run test lint format clean build docker docker-run

# Default target
all: setup

# Setup environment
setup:
	pip install -r requirements.txt

# Run the application
run:
	streamlit run app.py

# Run tests
test:
	python -m unittest discover -s tests

# Lint code
lint:
	flake8 --count --select=E9,F63,F7,F82 --show-source --statistics .

# Format code
format:
	black .

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +

# Build Docker image
build:
	docker build -t llms-txt-generator .

# Run Docker container
docker-run:
	docker run -p 8501:8501 llms-txt-generator

# Start using docker-compose
docker-compose-up:
	docker-compose up -d

# Stop using docker-compose
docker-compose-down:
	docker-compose down

# Deploy to Heroku
heroku-deploy:
	git push heroku main

# Initialize Heroku app
heroku-init:
	heroku create llms-txt-generator
	git push heroku main
	heroku open
