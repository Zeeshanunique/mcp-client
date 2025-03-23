"""
This script fixes the server.py file by replacing the problematic code with a standard tool implementation.
"""

with open('server.py', 'r') as f:
    content = f.read()

# Replace the problematic parts
start_marker = '# Define math operations with explicit schema'
end_marker = 'if __name__ == "__main__":'

if start_marker in content and end_marker in content:
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    # Get the content before and after the problematic section
    before = content[:start_pos]
    after = content[end_pos:]
    
    # Read the fixed implementation
    with open('math_operations_fix.py', 'r') as f:
        fixed_code = f.read()
    
    # Create the new content
    new_content = before + fixed_code + '\n\n' + after
    
    # Write the new content
    with open('server.py', 'w') as f:
        f.write(new_content)
    
    print("Server.py has been fixed!")
else:
    print("Could not find the markers in the file.") 