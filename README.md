# LLMS.txt Generator

Generate standardized llms.txt files for any website according to the [AnswerDotAI specification](https://github.com/AnswerDotAI/llms-txt).

![image](https://github.com/user-attachments/assets/5dfe08cd-3674-4ac8-b7f3-b084fabc9722)


## Features

- **Multiple URL Sources**: Process XML sitemaps or CSV files containing URLs
- **Intelligent Categorization**: Automatically organizes URLs into documentation, API reference, examples, and guides
- **Content Extraction**: Pulls titles and descriptions from web pages to enhance the llms.txt file
- **Real-time Progress Tracking**: Visual feedback during processing
- **One-click Download**: Easily save the generated llms.txt file
- **Responsive UI**: Works on desktop and mobile devices

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

1. Enter your website name and description
2. Choose between sitemap URL or CSV upload
3. Submit the form to generate your llms.txt file
4. Review the generated content
5. Download the file

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
