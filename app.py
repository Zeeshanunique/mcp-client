import chainlit as cl
import subprocess
import os
import json

conversation_history = []

def run_command_with_query(query, history=None):
    try:
        # Set environment variables for proper encoding
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Use streamlit_client.py with server.py
        server_script_path = "server.py"
        
        # Prepare command arguments
        cmd = ['uv', 'run', 'streamlit_client.py', server_script_path, query]
        
        # Add conversation history if available
        if history:
            # Convert history to JSON string and pass as an argument
            history_json = json.dumps(history)
            cmd.append('--history')
            cmd.append(history_json)
        
        # Create a process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            encoding='utf-8',
            errors='replace'  # Replace characters that can't be decoded
        )
        
        # Get output
        stdout, stderr = process.communicate()
        
        # Check for errors
        if process.returncode != 0:
            return f"Error (code {process.returncode}):\n{stderr}"
        
        # Extract just the response part if it follows our format
        if "\nResponse:" in stdout:
            stdout = stdout.split("\nResponse:", 1)[1].strip()
            
        return stdout
    except Exception as e:
        return f"Error: {str(e)}"

@cl.on_chat_start
async def on_chat_start():
    """
    Initialize the chat session.
    """
    # Set the title for the chat interface
    welcome_msg = await cl.Message(content="# MCP Client Interface\nType a query to get started.").send()
    
    # Initialize conversation history
    global conversation_history
    conversation_history = []
    
    # Add a button to clear conversation history in the sidebar
    # The for_id parameter needs to be on the send() method, not in the Action constructor
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
    global conversation_history
    
    # Get user query
    query = message.content
    
    # Show thinking indicator while processing
    thinking_msg = await cl.Message(content="Processing query...").send()
    
    # Format history for the command (excluding the current query)
    history_for_command = conversation_history.copy()
    
    # Add user query to conversation history
    conversation_history.append({
        'role': 'user',
        'content': query
    })
    
    # Process the query
    response = run_command_with_query(query, history_for_command)
    
    # Add the response to conversation history
    conversation_history.append({
        'role': 'assistant',
        'content': response
    })
    
    # Update or remove the thinking message
    await thinking_msg.remove()
    
    # Send the response back to the user
    await cl.Message(content=response).send()

@cl.action_callback("clear_history")
async def clear_history(action):
    """
    Clear the conversation history.
    """
    global conversation_history
    conversation_history = []
    await cl.Message(content="Conversation history cleared!").send()
