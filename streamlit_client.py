#!/usr/bin/env python
import asyncio
import sys
import json
import argparse
from client import MCPClient

async def main():
    """Main function to run the MCP client with a single query."""
    parser = argparse.ArgumentParser(description='Run MCP client with a single query')
    parser.add_argument('server_script', help='Path to the server script')
    parser.add_argument('query', help='Query to process')
    parser.add_argument('--history', help='JSON string of conversation history', default=None)
    
    args = parser.parse_args()
    
    client = MCPClient()
    try:
        # Connect to the MCP server
        await client.connect_to_server(args.server_script)
        
        # If history is provided, load it
        if args.history:
            try:
                history_data = json.loads(args.history)
                for entry in history_data:
                    if entry['role'] == 'user':
                        # Create a user message
                        from google.genai import types
                        user_content = types.Content(
                            role='user',
                            parts=[types.Part.from_text(text=entry['content'])]
                        )
                        client.conversation_history.append(user_content)
                    elif entry['role'] == 'assistant':
                        # Create an assistant message
                        from google.genai import types
                        assistant_content = types.Content(
                            role='assistant',
                            parts=[types.Part.from_text(text=entry['content'])]
                        )
                        client.conversation_history.append(assistant_content)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse conversation history: {args.history}")
        
        # Process the query and get the response
        response = await client.process_query(args.query)
        
        # Output the response for the main app to capture
        print(f"\nResponse: {response}")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Ensure resources are cleaned up
        await client.cleanup()

if __name__ == "__main__":
    # Run the main function within the asyncio event loop
    asyncio.run(main())
