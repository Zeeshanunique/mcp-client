#!/usr/bin/env python
import asyncio
import sys
import json
import argparse
from client import MCPClient, types

async def main():
    """
    Standalone script to process a single query with conversation history.
    Designed to be called from a Streamlit app.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process a query using the MCP client with conversation history.')
    parser.add_argument('server_script', help='Path to the MCP server script')
    parser.add_argument('query', help='Query to process')
    parser.add_argument('--history', help='JSON string containing conversation history')
    args = parser.parse_args()

    client = MCPClient()
    try:
        # Connect to the MCP server
        await client.connect_to_server(args.server_script)

        # Load conversation history if provided
        if args.history:
            try:
                history_data = json.loads(args.history)
                # Convert the plain dict history to Gemini Content objects
                for entry in history_data:
                    role = entry.get('role')
                    content = entry.get('content', '')
                    
                    if role == 'user':
                        client.conversation_history.append(types.Content(
                            role='user',
                            parts=[types.Part.from_text(text=content)]
                        ))
                    elif role == 'assistant':
                        client.conversation_history.append(types.Content(
                            role='assistant',
                            parts=[types.Part.from_text(text=content)]
                        ))
                
                print(f"Loaded {len(history_data)} conversation history entries")
            except json.JSONDecodeError as e:
                print(f"Error loading history: {e}")

        # Process the query
        response = await client.process_query(args.query)
        
        # Print the response with a marker for easy extraction
        print("\nResponse:", response)
    finally:
        # Clean up resources
        await client.cleanup()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
