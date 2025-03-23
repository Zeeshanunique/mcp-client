# MCP Client Streamlit Interface

A simple Streamlit interface for interacting with the MCP client.

## Setup

1. Make sure you have Python 3.13+ installed
2. Install the dependencies:
   ```
   pip install -e .
   ```
3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   SERPAPI_KEY=your_serpapi_key  # Optional for web search functionality
   ```

## Running the Streamlit Interface

Run the following command to start the Streamlit interface:

```
streamlit run main.py
```

Then open your browser to http://localhost:8501 to interact with the MCP client.

## Usage

1. Enter the path to the server script (default is `server.py`)
2. Type your query in the text area
3. Click "Process Query" to send the query to the MCP client
4. View the response from the MCP client
