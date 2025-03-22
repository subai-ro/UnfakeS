# Unfake - Article Credibility Assessment Platform

A web application designed to help users assess the credibility of articles and combat misinformation through both manual and automated verification methods.

## Features

- User authentication and profile management
- Article submission and management
- Automated credibility assessment using machine learning
- Manual fact-checking capabilities
- Admin dashboard for content moderation
- Search functionality
- User ratings and feedback system

## Tech Stack

- Backend: Flask (Python)
- Database: SQLite
- Frontend: HTML, Jinja2 Templates
- Machine Learning: scikit-learn
- Production Server: Waitress

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/unfake.git
cd unfake
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python schema_creation.py
```

5. Run the application:
```bash
python app.py
```

## Project Structure

- `app.py`: Main Flask application
- `db.py`: Database operations and models
- `schema_creation.py`: Database schema setup
- `ml_model.pkl`: Trained machine learning model
- `templates/`: HTML templates
- `static/`: Static files and uploads
- `requirements.txt`: Project dependencies

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 