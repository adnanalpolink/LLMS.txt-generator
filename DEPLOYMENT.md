# Deployment Guide

## Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/llms-txt-generator.git
cd llms-txt-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

## Streamlit Cloud Deployment

1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Sign in with GitHub
4. Click "New app"
5. Select your repository, branch, and main file path (`app.py`)
6. Click "Deploy"

## Heroku Deployment

```bash
# Login to Heroku
heroku login

# Create a new Heroku app
heroku create llms-txt-generator

# Add a Procfile (if not already present)
echo "web: streamlit run app.py --server.port=\$PORT" > Procfile

# Add runtime.txt for Python version
echo "python-3.9.16" > runtime.txt

# Commit changes
git add .
git commit -m "Add Heroku deployment files"

# Deploy to Heroku
git push heroku main

# Open the deployed app
heroku open
```

## Docker Deployment

### Local Docker Deployment

```bash
# Build the Docker image
docker build -t llms-txt-generator .

# Run the container
docker run -p 8501:8501 llms-txt-generator

# Access the application at http://localhost:8501
```

### AWS ECS Deployment

1. Push your Docker image to Amazon ECR:

```bash
# Install AWS CLI and configure credentials
aws configure

# Create ECR repository
aws ecr create-repository --repository-name llms-txt-generator

# Get the repository URI
ECR_REPO=$(aws ecr describe-repositories --repository-names llms-txt-generator --query 'repositories[0].repositoryUri' --output text)

# Login to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO

# Tag and push image
docker tag llms-txt-generator:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
```

2. Create an ECS cluster and service using AWS Console or CLI

### Google Cloud Run Deployment

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/llms-txt-generator

# Deploy to Cloud Run
gcloud run deploy llms-txt-generator \
  --image gcr.io/YOUR_PROJECT_ID/llms-txt-generator \
  --platform managed \
  --allow-unauthenticated \
  --region us-central1 \
  --memory 1Gi
```

## Environment Variables

The application supports the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REQUEST_TIMEOUT` | Timeout for URL fetching requests (seconds) | 10 |
| `MAX_URLS_PER_SECTION` | Maximum URLs to display per section | 10 |
| `MAX_WORKERS` | Maximum parallel workers for URL processing | 5 |

## Performance Optimization

For large websites with many URLs:

1. Increase memory allocation (especially for cloud deployments)
2. Adjust the `MAX_WORKERS` environment variable
3. Implement URL filtering to prioritize important content
4. Consider implementing a caching layer for repeated runs
