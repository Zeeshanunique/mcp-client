import streamlit as st
import subprocess
import sys
import os
import shlex
import json

def run_command_with_query(query, conversation_history=None):
    try:
        # Set environment variables for proper encoding
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Pass Streamlit secrets as environment variables to the subprocess
        if hasattr(st, 'secrets'):
            for key, value in st.secrets.items():
                env[key] = str(value)
        
        # Use streamlit_client.py instead of client.py directly
        server_script_path = "server.py"
        
        # Prepare command arguments
        cmd = ['uv', 'run', 'streamlit_client.py', server_script_path, query]
        
        # Add conversation history if available
        if conversation_history:
            # Convert history to JSON string and pass as an argument
            history_json = json.dumps(conversation_history)
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
        
        return stdout
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    st.title("MCP Client Interface")
    
    # Initialize session state for conversation history and query input
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []
    
    if 'query_input' not in st.session_state:
        st.session_state.query_input = ""
    
    # Display conversation history
    if st.session_state.conversation:
        st.subheader("Conversation History")
        for i, entry in enumerate(st.session_state.conversation):
            if entry['role'] == 'user':
                st.markdown(f"**You:** {entry['content']}")
            else:
                st.markdown(f"**Assistant:** {entry['content']}")
            
            # Add a small divider between conversation entries
            if i < len(st.session_state.conversation) - 1:
                st.markdown("---")
    
    # Function to handle input changes
    def on_change():
        st.session_state.query_input = st.session_state.text_area
    
    # Input for query
    query = st.text_area(
        "Enter your query",
        value=st.session_state.query_input,
        key="text_area",
        on_change=on_change,
        help="Type your query to be processed by the MCP client"
    )
    
    # Add buttons for conversation management
    col1, col2 = st.columns([1, 1])
    with col1:
        process_button = st.button("Process Query")
    with col2:
        clear_button = st.button("Clear History")
    
    if clear_button:
        st.session_state.conversation = []
        st.success("Conversation history cleared!")
        st.rerun()
    
    # Process button
    if process_button:
        if not query:
            st.error("Please enter a query")
        else:
            # Save current query
            current_query = query
            
            # Clear the input field by updating the session state
            st.session_state.query_input = ""
            
            # Add user query to conversation history
            st.session_state.conversation.append({
                'role': 'user',
                'content': current_query
            })
            
            with st.spinner("Processing query..."):
                # Format history for the command
                history_for_command = [
                    {'role': entry['role'], 'content': entry['content']}
                    for entry in st.session_state.conversation[:-1]  # Exclude the current query
                ]
                
                # Run the command with the query and history
                response = run_command_with_query(current_query, history_for_command)
                
                # Extract just the response part if it follows our format
                if "\nResponse:" in response:
                    response = response.split("\nResponse:", 1)[1].strip()
                
                # Add the response to conversation history
                st.session_state.conversation.append({
                    'role': 'assistant',
                    'content': response
                })
                
                # Rerun to display the updated conversation
                st.rerun()

if __name__ == "__main__":
    main()
