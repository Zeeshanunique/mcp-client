# MCP Web Client

A modern web interface alternative to the Streamlit MCP Client.

## Project Structure

- `src/` - React frontend code
- `public/` - Static files for the React app
- `server.py` - Flask API backend

## Setup Instructions

### Backend Setup

1. Install the Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Start the Flask backend server:
   ```
   python server.py
   ```
   The server will run on http://localhost:5000.

### Frontend Setup

1. Install Node.js dependencies:
   ```
   npm install
   ```

2. Start the React development server:
   ```
   npm start
   ```
   The React app will run on http://localhost:3000.

## Usage

1. Enter your query in the text area.
2. Click "Process Query" or press Enter to send your query.
3. View the conversation history in the top section.
4. Use "Clear History" to reset the conversation.

## Features

- Modern, responsive user interface
- Real-time processing of queries
- Conversation history tracking
- Compatible with the existing MCP backend 