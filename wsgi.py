from app import app
from waitress import serve
from schema_creation import create_schema

if __name__ == "__main__":
    # Create database tables on startup
    create_schema()
    serve(app, host='0.0.0.0', port=10000) 