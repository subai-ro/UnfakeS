from app import app
from waitress import serve
from schema_creation import create_tables

if __name__ == "__main__":
    # Create database tables on startup
    create_tables()
    serve(app, host='0.0.0.0', port=10000) 