import chainlit as cl
import asyncio
import os
import json
import glob
from client import MCPClient, types

# Global variables
conversation_history = []
mcp_client = None
current_server = "server.py"  # Default server

def get_available_servers():
    """
    Get a list of available MCP server scripts.
    """
    # Look for Python files that might be MCP servers
    server_files = glob.glob("*.py")
    # Filter known server files or files with 'server' in the name
    servers = [f for f in server_files if f == "server.py" or "server" in f.lower()]
    # Add any JavaScript servers if they exist
    js_servers = glob.glob("*.js")
    servers.extend([f for f in js_servers if "server" in f.lower()])
    return servers

@cl.on_chat_start
async def on_chat_start():
    """
    Initialize the chat session and MCP client.
    """
    # Set the title for the chat interface
    welcome_msg = await cl.Message(content="# MCP Client Interface\nType a query to get started.").send()
    
    # Initialize conversation history
    global conversation_history, mcp_client, current_server
    conversation_history = []
    
    # Get available servers
    servers = get_available_servers()
    
    # Create server selection buttons - one for each server
    for server in servers:
        await cl.Action(
            name="server_action",
            label=f"Connect to {server}",
            description=f"Switch to {server} MCP server",
            payload={"server": server}
        ).send(for_id=welcome_msg.id)
    
    # Initialize MCP client
    try:
        mcp_client = MCPClient()
        # Connect to default server
        await mcp_client.connect_to_server(current_server)
        await cl.Message(content=f"Connected to MCP server: {current_server}").send()
    except Exception as e:
        error_msg = f"Error initializing MCP client: {str(e)}"
        await cl.Message(content=error_msg).send()
        return
    
    # Add a button to clear conversation history in the sidebar
    await cl.Action(
        name="clear_history",
        label="Clear History",
        description="Clear the conversation history",
        payload={}
    ).send(for_id=welcome_msg.id)

@cl.on_message
async def on_message(message: cl.Message):
    """
    Handle incoming messages from the user.
    """
    global conversation_history, mcp_client
    
    # Get user query
    query = message.content
    
    # Show thinking indicator while processing
    thinking_msg = await cl.Message(content="Processing query...").send()
    
    # Check if MCP client is initialized
    if mcp_client is None:
        await thinking_msg.remove()
        await cl.Message(content="Error: MCP client not connected. Please try reconnecting to a server.").send()
        return
    
    try:
        # Process the query using MCP client
        response = await mcp_client.process_query(query)
        
        # Add user query to conversation history (for Chainlit tracking)
        conversation_history.append({
            'role': 'user',
            'content': query
        })
        
        # Add the response to conversation history (for Chainlit tracking)
        conversation_history.append({
            'role': 'assistant',
            'content': response
        })
        
        # Update or remove the thinking message
        await thinking_msg.remove()
        
        # Send the response back to the user
        await cl.Message(content=response).send()
        
    except Exception as e:
        # Remove the thinking message and send an error message instead
        await thinking_msg.remove()
        await cl.Message(content=f"Error: {str(e)}").send()

@cl.action_callback("clear_history")
async def clear_history(action):
    """
    Clear the conversation history.
    """
    global conversation_history, mcp_client
    
    # Clear local conversation history
    conversation_history = []
    
    # Clear MCP client conversation history
    if mcp_client:
        mcp_client.conversation_history = []
        
    await cl.Message(content="Conversation history cleared!").send()

# Action handler for server connections
@cl.action_callback("server_action")
async def handle_server_connection(action):
    """
    Handle server connection requests.
    """
    global mcp_client, current_server, conversation_history
    
    # Extract server name from the payload
    server = action.payload.get("server")
    if server:
        current_server = server
        
        # Clean up existing client if needed
        if mcp_client:
            await mcp_client.cleanup()
        
        # Connect to the new server
        try:
            mcp_client = MCPClient()
            await mcp_client.connect_to_server(server)
            await cl.Message(content=f"Connected to MCP server: {server}").send()
            
            # Clear conversation history for new server
            conversation_history.clear()
            if mcp_client:
                mcp_client.conversation_history = []
            
        except Exception as e:
            await cl.Message(content=f"Error connecting to {server}: {str(e)}").send()

@cl.on_chat_end
async def on_chat_end():
    """
    Clean up resources when the chat session ends.
    """
    global mcp_client
    if mcp_client:
        await mcp_client.cleanup()
        mcp_client = None
