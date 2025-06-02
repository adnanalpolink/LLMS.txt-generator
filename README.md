# LLMS.txt Generator

Generate standardized llms.txt files for any website according to the [AnswerDotAI specification](https://github.com/AnswerDotAI/llms-txt).

![image](https://github.com/user-attachments/assets/5dfe08cd-3674-4ac8-b7f3-b084fabc9722)


## Features

### Core Features
- **Multiple URL Sources**: Process XML sitemaps or CSV files containing URLs
- **Intelligent Categorization**: Automatically organizes URLs into documentation, API reference, examples, and guides
- **Content Extraction**: Pulls titles and descriptions from web pages to enhance the llms.txt file
- **Real-time Progress Tracking**: Visual feedback during processing
- **One-click Download**: Easily save the generated llms.txt file
- **Responsive UI**: Works on desktop and mobile devices

### 🚀 Enhanced Features (NEW!)
- **JavaScript Rendering**: Use Puppeteer to render JavaScript-heavy pages that require browser execution
- **AI-Generated Descriptions**: Integrate with OpenRouter API to generate intelligent, context-aware descriptions
- **Main Content Extraction**: Focus on primary article content while excluding headers, footers, and navigation
- **Enhanced Processing**: Better handling of modern web applications and dynamic content
- **Multiple LLM Models**: Choose from various AI models including Claude, GPT-4, Llama, and more

## Installation

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

## Usage

### Basic Usage
1. Enter your website name and description
2. Choose between sitemap URL or CSV upload
3. Submit the form to generate your llms.txt file
4. Review the generated content
5. Download the file

### Enhanced Features Setup

#### JavaScript Rendering (Puppeteer)
- Enable "Use Puppeteer for JavaScript-heavy pages" checkbox
- Useful for Single Page Applications (SPAs) and dynamic content
- Note: This will be slower but more accurate for JavaScript-dependent sites

#### AI-Generated Descriptions (OpenRouter)
1. Get an API key from [OpenRouter](https://openrouter.ai/keys)
2. Enable "Generate descriptions using AI" checkbox
3. Enter your OpenRouter API key
4. Choose your preferred LLM model
5. The system will generate intelligent descriptions based on page content

#### Environment Variables (Optional)
Create a `.env` file in the project root:
```bash
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
```

## Docker Deployment

```bash
# Build the Docker image
docker build -t llms-txt-generator .

# Run the container
docker run -p 8501:8501 llms-txt-generator
```

## Cloud Deployment

The app can be easily deployed to:
- Streamlit Cloud
- Heroku
- AWS
- Google Cloud Run

See [Deployment Instructions](DEPLOYMENT.md) for detailed steps.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Adnan Akram: [LinkedIn](http://linkedin.com/in/adnanakram1/) Profile
Project Link: [https://github.com/adnanalpolink/llms-txt-generator](https://github.com/adnanalpolink/llms-txt-generator)
