# URL Shortener

A simple URL shortener built with Python and a small React/Vite frontend.

## Features
- Shorten long URLs
- Store shortened links in a local SQLite database
- View the frontend in a browser

## Project Structure
- `db.py` - database helper functions
- `main.py` - FastAPI application and URL shortening logic
- `frontend/` - React/Vite frontend
- `tests/` - backend tests

## Requirements
- Python 3.9+
- Node.js and npm

## Backend Setup
1. Create and activate a virtual environment
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn requests pytest
   ```
3. Run the backend:
   ```bash
   uvicorn main:app --reload
   ```

## Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## Testing
Run tests with:
```bash
pytest
```

## Notes
- The app uses a local SQLite database file named `urlshortener.db`.
- The frontend expects the backend to be running on the local server.
