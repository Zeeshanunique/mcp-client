import os
import subprocess
import sys
import platform
import requests
import re
from dotenv import load_dotenv, set_key
from mcp.server.fastmcp import FastMCP
from serpapi import GoogleSearch

# Load environment variables
load_dotenv()

mcp = FastMCP("terminal")

# Ensure the workspace path is correctly formatted for Windows
DEFAULT_WORKSPACE = os.path.join("C:/Users/dell/Desktop/mcp/workspace")

@mcp.tool()
async def run_command(command: str) -> str:
    """
    Run a terminal command inside the workspace directory.
    
    Args:
        command: The shell command to run.
    
    Returns:
        The command output or an error message.
    """
    try:
        # Adjust for Windows command syntax
        if command.startswith("cat "):
            command = command.replace("cat ", "type ")  # Replace 'cat' with 'type' for Windows

        result = subprocess.run(command, shell=True, cwd=DEFAULT_WORKSPACE, capture_output=True, text=True)
        return result.stdout or result.stderr
    except Exception as e:
        return str(e)

@mcp.tool()
def websearch(query: str) -> dict:
    """
    Perform a web search using SerpAPI.
    
    Args:
        query: The search query.
    
    Returns:
        A dictionary with search results or error information.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {
            "error": "SERPAPI_KEY environment variable not set",
            "suggestion": "Please add your SerpAPI key to the .env file"
        }
    
    # Set up the base parameters
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": 5  # Limit to 5 results
    }
    
    try:
        # Execute the search
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Get organic results
        organic_results = results.get("organic_results", [])
        
        # If no results were found
        if not organic_results:
            return {
                "error": "No results found for the query",
                "suggestion": "Try a different search query with more specific terms"
            }
        
        # Process and format the results for better readability
        formatted_results = []
        for result in organic_results:
            formatted_result = {
                "title": result.get("title", "No title"),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", "No description available")
            }
            formatted_results.append(formatted_result)
        
        return {
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except Exception as e:
        error_message = str(e)
        suggestion = ""
        
        # Provide helpful suggestions for common errors
        if "authentication" in error_message.lower() or "api key" in error_message.lower():
            suggestion = "Check that your SerpAPI key is valid and has sufficient credits"
        elif "connection" in error_message.lower():
            suggestion = "Check your internet connection and try again"
        
        return {
            "error": f"Search error: {error_message}",
            "suggestion": suggestion
        }

@mcp.tool()
def diagnose_websearch(dummy: str = "run") -> dict:
    """
    Diagnose issues with the web search functionality.
    
    Args:
        dummy: Optional parameter (not used) to satisfy API requirements
    
    Returns:
        A dictionary with diagnostic information.
    """
    diagnostics = {
        "environment": {},
        "connectivity": {},
        "serpapi": {},
        "system": {}
    }
    
    # Check environment variables
    api_key = os.getenv("SERPAPI_KEY")
    diagnostics["environment"]["SERPAPI_KEY"] = "Set" if api_key else "Not set"
    if api_key:
        # Mask the API key for security but show if it's provided
        diagnostics["environment"]["SERPAPI_KEY_LENGTH"] = len(api_key)
        diagnostics["environment"]["SERPAPI_KEY_PREVIEW"] = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "Too short"
    
    # Check system information
    diagnostics["system"]["python_version"] = sys.version
    diagnostics["system"]["platform"] = platform.platform()
    
    # Check network connectivity
    try:
        response = requests.get("https://serpapi.com", timeout=5)
        diagnostics["connectivity"]["serpapi_status"] = f"OK ({response.status_code})"
    except Exception as e:
        diagnostics["connectivity"]["serpapi_status"] = f"Error: {str(e)}"
    
    try:
        response = requests.get("https://google.com", timeout=5)
        diagnostics["connectivity"]["google_status"] = f"OK ({response.status_code})"
    except Exception as e:
        diagnostics["connectivity"]["google_status"] = f"Error: {str(e)}"
    
    # Check SerpAPI validity if key is available
    if api_key:
        try:
            params = {
                "q": "test query",
                "api_key": api_key,
                "engine": "google",
                "num": 1
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" in results:
                diagnostics["serpapi"]["test_query"] = f"Error: {results['error']}"
            else:
                diagnostics["serpapi"]["test_query"] = "Success"
                diagnostics["serpapi"]["result_count"] = len(results.get("organic_results", []))
        except Exception as e:
            diagnostics["serpapi"]["test_query"] = f"Exception: {str(e)}"
    else:
        diagnostics["serpapi"]["test_query"] = "Skipped (no API key)"
    
    # Build recommendation
    issues = []
    recommendations = []
    
    if not api_key:
        issues.append("Missing API key")
        recommendations.append("Add your SerpAPI key to the .env file as SERPAPI_KEY=your_key_here")
    
    if "Error" in diagnostics["connectivity"].get("serpapi_status", ""):
        issues.append("Cannot connect to SerpAPI")
        recommendations.append("Check your internet connection and firewall settings")
    
    if api_key and "Error" in diagnostics["serpapi"].get("test_query", ""):
        issues.append("API key may be invalid")
        recommendations.append("Verify your SerpAPI key is correct and has credits available")
    
    diagnostics["summary"] = {
        "issues_detected": issues,
        "recommendations": recommendations,
        "status": "OK" if not issues else "Problems detected"
    }
    
    return diagnostics

@mcp.tool()
def set_serpapi_key(api_key: str) -> dict:
    """
    Set or update the SerpAPI key in the .env file.
    
    Args:
        api_key: Your SerpAPI key from serpapi.com
    
    Returns:
        A status message about the operation
    """
    # Validate key format (basic check)
    if not re.match(r'^[a-zA-Z0-9]{32,}$', api_key):
        return {
            "error": "Invalid API key format",
            "suggestion": "SerpAPI keys are usually at least 32 characters long and contain only letters and numbers"
        }
    
    try:
        # Find .env file
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if not os.path.exists(env_path):
            # Try parent directory
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
            if not os.path.exists(env_path):
                # Create new .env file in current directory
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
                with open(env_path, 'w') as f:
                    f.write(f"SERPAPI_KEY={api_key}\n")
                return {
                    "status": "success",
                    "message": f"Created new .env file with SERPAPI_KEY at {env_path}"
                }
        
        # Update existing .env file
        set_key(env_path, "SERPAPI_KEY", api_key)
        
        # Update current environment
        os.environ["SERPAPI_KEY"] = api_key
        
        # Test the key
        try:
            params = {
                "q": "test query",
                "api_key": api_key,
                "engine": "google",
                "num": 1
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" in results:
                return {
                    "status": "warning",
                    "message": f"SerpAPI key saved to {env_path}, but test query failed with error: {results['error']}",
                    "suggestion": "The key may be invalid or have usage limitations"
                }
            
            return {
                "status": "success", 
                "message": f"SerpAPI key saved to {env_path} and verified working"
            }
            
        except Exception as e:
            return {
                "status": "warning",
                "message": f"SerpAPI key saved to {env_path}, but test query failed",
                "error": str(e)
            }
            
    except Exception as e:
        return {
            "error": f"Failed to update SerpAPI key: {str(e)}",
            "suggestion": "You may need to manually add SERPAPI_KEY=your_key_here to your .env file"
        }

@mcp.tool()
def read_file(file_path: str) -> dict:
    """
    Read the contents of a file.
    
    Args:
        file_path: Relative path to the file from the workspace
    
    Returns:
        Dictionary with file contents or error
    """
    try:
        full_path = os.path.join(DEFAULT_WORKSPACE, file_path)
        if not os.path.exists(full_path):
            return {
                "error": f"File not found: {file_path}",
                "suggestion": "Check the file path and try again"
            }
            
        with open(full_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        return {
            "content": content,
            "path": file_path,
            "size": len(content)
        }
    except Exception as e:
        return {
            "error": f"Failed to read file: {str(e)}",
            "suggestion": "Check file permissions or encoding"
        }

@mcp.tool()
def write_file(file_path: str, content: str) -> dict:
    """
    Write content to a file.
    
    Args:
        file_path: Relative path to the file from the workspace
        content: Text content to write to the file
    
    Returns:
        Status of the write operation
    """
    try:
        full_path = os.path.join(DEFAULT_WORKSPACE, file_path)
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        return {
            "status": "success",
            "message": f"Successfully wrote {len(content)} bytes to {file_path}"
        }
    except Exception as e:
        return {
            "error": f"Failed to write file: {str(e)}",
            "suggestion": "Check file permissions or path validity"
        }

@mcp.tool()
def list_files(directory: str = "") -> dict:
    """
    List files and directories in a specified directory.
    
    Args:
        directory: Relative path to the directory from the workspace (empty for root)
    
    Returns:
        List of files and directories in the specified path
    """
    try:
        full_path = os.path.join(DEFAULT_WORKSPACE, directory)
        if not os.path.exists(full_path):
            return {
                "error": f"Directory not found: {directory}",
                "suggestion": "Check the directory path and try again"
            }
            
        if not os.path.isdir(full_path):
            return {
                "error": f"Path is not a directory: {directory}",
                "suggestion": "Provide a directory path, not a file path"
            }
            
        items = os.listdir(full_path)
        files = []
        directories = []
        
        for item in items:
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                directories.append({"name": item, "type": "directory"})
            else:
                files.append({"name": item, "type": "file", "size": os.path.getsize(item_path)})
                
        return {
            "path": directory,
            "directories": directories,
            "files": files,
            "count": len(items)
        }
    except Exception as e:
        return {
            "error": f"Failed to list directory: {str(e)}",
            "suggestion": "Check directory permissions or path validity"
        }

@mcp.tool()
def get_system_info() -> dict:
    """
    Get information about the system.
    
    Returns:
        System information including OS, Python version, CPU, memory, etc.
    """
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "python_version": sys.version,
            "cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_used_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_used_percent": disk.percent
        }
    except ImportError:
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "python_version": sys.version,
            "note": "Install psutil for more detailed system information"
        }
    except Exception as e:
        return {
            "error": f"Failed to get system info: {str(e)}"
        }

@mcp.tool()
def fetch_webpage(url: str) -> dict:
    """
    Fetch content from a webpage.
    
    Args:
        url: URL of the webpage to fetch
    
    Returns:
        HTML content of the webpage or error information
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return {
            "status_code": response.status_code,
            "content": response.text,
            "headers": dict(response.headers),
            "url": response.url,
            "content_type": response.headers.get('Content-Type', 'unknown')
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to fetch webpage: {str(e)}",
            "suggestion": "Check the URL and your internet connection"
        }

@mcp.tool()
def search_text(file_path: str, search_term: str) -> dict:
    """
    Search for text in a file.
    
    Args:
        file_path: Relative path to the file from the workspace
        search_term: Text to search for
    
    Returns:
        Lines containing the search term with line numbers
    """
    try:
        full_path = os.path.join(DEFAULT_WORKSPACE, file_path)
        if not os.path.exists(full_path):
            return {
                "error": f"File not found: {file_path}",
                "suggestion": "Check the file path and try again"
            }
            
        results = []
        with open(full_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                if search_term in line:
                    results.append({
                        "line_number": line_num,
                        "content": line.strip()
                    })
                    
        return {
            "file": file_path,
            "search_term": search_term,
            "match_count": len(results),
            "matches": results
        }
    except Exception as e:
        return {
            "error": f"Failed to search file: {str(e)}",
            "suggestion": "Check file permissions or encoding"
        }

@mcp.tool()
def analyze_text(text: str) -> dict:
    """
    Analyze text to extract statistics and information.
    
    Args:
        text: The text to analyze
    
    Returns:
        Text statistics including word count, character count, etc.
    """
    try:
        import re
        
        # Remove excess whitespace
        cleaned_text = re.sub(r'\s+', ' ', text).strip()
        
        # Count words
        words = cleaned_text.split()
        word_count = len(words)
        
        # Count sentences (basic)
        sentences = re.split(r'[.!?]+', cleaned_text)
        sentence_count = sum(1 for s in sentences if s.strip())
        
        # Count paragraphs
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # Find most common words
        word_freq = {}
        for word in words:
            word_lower = word.lower()
            word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
            
        common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "character_count": len(text),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "average_word_length": sum(len(word) for word in words) / word_count if word_count else 0,
            "average_sentence_length": word_count / sentence_count if sentence_count else 0,
            "most_common_words": [{"word": word, "count": count} for word, count in common_words]
        }
    except Exception as e:
        return {
            "error": f"Failed to analyze text: {str(e)}"
        }

@mcp.tool()
def generate_password(length: int = 16, include_special: bool = True) -> dict:
    """
    Generate a strong random password.
    
    Args:
        length: Length of the password (default: 16)
        include_special: Whether to include special characters (default: True)
    
    Returns:
        Generated password and strength evaluation
    """
    try:
        import random
        import string
        
        if length < 8:
            return {
                "error": "Password length must be at least 8 characters",
                "suggestion": "Use a longer password for better security"
            }
            
        if length > 128:
            return {
                "error": "Password length cannot exceed 128 characters",
                "suggestion": "Use a shorter password for better usability"
            }
            
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = string.punctuation if include_special else ""
        
        # Ensure each character type is included
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits)
        ]
        
        if include_special:
            password.append(random.choice(special))
            
        # Fill the rest with random characters from all sets
        all_chars = lowercase + uppercase + digits + special
        password.extend(random.choice(all_chars) for _ in range(length - len(password)))
        
        # Shuffle the password
        random.shuffle(password)
        password = ''.join(password)
        
        # Evaluate strength
        strength = "strong"
        if length < 12:
            strength = "medium"
        if length < 10 or not include_special:
            strength = "weak"
            
        return {
            "password": password,
            "length": len(password),
            "strength": strength,
            "includes_special": include_special,
            "entropy_bits": len(password) * (4 if include_special else 3)  # Rough estimate
        }
    except Exception as e:
        return {
            "error": f"Failed to generate password: {str(e)}"
        }

@mcp.tool()
def convert_data_format(data: str, from_format: str, to_format: str) -> dict:
    """
    Convert data between different formats.
    
    Args:
        data: The data to convert
        from_format: Source format (json, csv, yaml, xml)
        to_format: Target format (json, csv, yaml, xml)
    
    Returns:
        Converted data in the target format
    """
    try:
        import json
        import csv
        import yaml
        import dicttoxml
        import xmltodict
        from io import StringIO
        
        # Validate formats
        valid_formats = ["json", "csv", "yaml", "xml"]
        if from_format not in valid_formats:
            return {
                "error": f"Invalid source format: {from_format}",
                "suggestion": f"Choose from: {', '.join(valid_formats)}"
            }
            
        if to_format not in valid_formats:
            return {
                "error": f"Invalid target format: {to_format}",
                "suggestion": f"Choose from: {', '.join(valid_formats)}"
            }
            
        if from_format == to_format:
            return {
                "result": data,
                "warning": "Source and target formats are the same, no conversion performed"
            }
            
        # Parse input data to Python object
        parsed_data = None
        
        if from_format == "json":
            parsed_data = json.loads(data)
        elif from_format == "yaml":
            parsed_data = yaml.safe_load(data)
        elif from_format == "xml":
            parsed_data = xmltodict.parse(data)
        elif from_format == "csv":
            csv_data = list(csv.reader(StringIO(data)))
            headers = csv_data[0] if csv_data else []
            rows = csv_data[1:] if len(csv_data) > 1 else []
            parsed_data = [dict(zip(headers, row)) for row in rows]
            
        # Convert to target format
        result = None
        
        if to_format == "json":
            result = json.dumps(parsed_data, indent=2)
        elif to_format == "yaml":
            result = yaml.dump(parsed_data)
        elif to_format == "xml":
            result = dicttoxml.dicttoxml(parsed_data).decode()
        elif to_format == "csv":
            if not isinstance(parsed_data, list):
                return {
                    "error": "Cannot convert to CSV: data is not a list of records",
                    "suggestion": "CSV conversion requires list of dictionaries"
                }
                
            output = StringIO()
            fields = set()
            for item in parsed_data:
                fields.update(item.keys())
                
            writer = csv.DictWriter(output, fieldnames=sorted(fields))
            writer.writeheader()
            writer.writerows(parsed_data)
            result = output.getvalue()
            
        return {
            "result": result,
            "from_format": from_format,
            "to_format": to_format
        }
    except ImportError as e:
        missing_package = str(e).split("'")[-2] if "'" in str(e) else "required package"
        return {
            "error": f"Missing package: {missing_package}",
            "suggestion": f"Install the required package with: pip install {missing_package}"
        }
    except Exception as e:
        return {
            "error": f"Conversion failed: {str(e)}",
            "suggestion": "Check that the input data matches the specified source format"
        }

@mcp.tool()
def image_info(image_url: str) -> dict:
    """
    Get information about an image from a URL.
    
    Args:
        image_url: URL of the image
    
    Returns:
        Information about the image including dimensions, format, size, etc.
    """
    try:
        from PIL import Image
        import io
        
        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Open image from memory
        img = Image.open(io.BytesIO(response.content))
        
        # Extract image information
        info = {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "size_bytes": len(response.content),
            "size_kb": round(len(response.content) / 1024, 2),
            "content_type": response.headers.get('Content-Type'),
            "url": image_url
        }
        
        # Additional information depending on image type
        if hasattr(img, 'info'):
            # Extract safe metadata (skip binary data)
            metadata = {}
            for k, v in img.info.items():
                if isinstance(v, (str, int, float, bool)):
                    metadata[k] = v
            info["metadata"] = metadata
            
        return info
    except ImportError:
        return {
            "error": "PIL (Pillow) package not installed",
            "suggestion": "Install Pillow with: pip install Pillow"
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to download image: {str(e)}",
            "suggestion": "Check the URL and your internet connection"
        }
    except Exception as e:
        return {
            "error": f"Failed to process image: {str(e)}",
            "suggestion": "Ensure the URL points to a valid image"
        }

@mcp.tool()
def calculate(expression: str) -> dict:
    """
    Perform basic arithmetic calculations.
    
    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 3 * 4")
    
    Returns:
        The calculation result and additional information
    """
    try:
        # Security check to prevent code execution
        if any(keyword in expression for keyword in ['import', 'eval', 'exec', 'getattr', '__']):
            return {
                "error": "Potentially unsafe expression",
                "suggestion": "Use only basic arithmetic operations and numbers"
            }
        
        # Clean the expression
        cleaned_expression = expression.strip()
        
        # Calculate the result
        # Using eval with strict filtering for basic arithmetic only
        result = eval(cleaned_expression, {"__builtins__": {}}, {})
        
        return {
            "expression": cleaned_expression,
            "result": result,
            "type": type(result).__name__
        }
    except SyntaxError:
        return {
            "error": "Invalid syntax in expression",
            "suggestion": "Check your expression for syntax errors"
        }
    except ZeroDivisionError:
        return {
            "error": "Division by zero",
            "suggestion": "Check your expression for division by zero"
        }
    except Exception as e:
        return {
            "error": f"Calculation error: {str(e)}",
            "suggestion": "Use only basic arithmetic operations (+, -, *, /, **, ())"
        }

@mcp.tool()
def generate_report(title: str = "", content: dict = None, format: str = "markdown", filename: str = "") -> dict:
    """
    Generate and save a formatted report. This tool can automatically generate content if not provided.
    
    Args:
        title: Report title (if empty, will generate a default title)
        content: Dictionary containing report content sections (if empty, will generate sample content)
        format: Output format (markdown, html, txt, json)
        filename: Optional filename (without extension), defaults to title_YYYYMMDD if empty
    
    Returns:
        Information about the saved report
    """
    try:
        import datetime
        import json
        import random
        
        # Generate default title if none provided
        if not title:
            topics = ["Status Report", "Project Overview", "Weekly Summary", "Monthly Analysis", 
                      "Performance Review", "System Health Check", "Progress Update"]
            title = f"Auto-generated {random.choice(topics)}"
            print(f"[Auto-generated title: {title}]")
        
        # Generate sample content if none provided
        if not content or not isinstance(content, dict):
            current_time = datetime.datetime.now()
            content = {
                "Summary": "This is an automatically generated report with sample content.",
                "Date Information": {
                    "Generation Date": current_time.strftime("%Y-%m-%d"),
                    "Generation Time": current_time.strftime("%H:%M:%S"),
                    "Day of Week": current_time.strftime("%A"),
                    "Month": current_time.strftime("%B")
                },
                "Sample Metrics": [
                    f"Metric A: {random.randint(75, 99)}%",
                    f"Metric B: {random.randint(50, 100)} units",
                    f"Metric C: {random.uniform(0.1, 0.9):.2f} ratio"
                ],
                "System Information": {
                    "OS": platform.system(),
                    "Python Version": platform.python_version(),
                    "Machine": platform.machine()
                },
                "Notes": "This content was automatically generated because no content was provided."
            }
            print("[Auto-generated sample content]")
            
        valid_formats = ["markdown", "html", "txt", "json"]
        if format.lower() not in valid_formats:
            format = "markdown"
            print(f"[Invalid format specified, defaulting to markdown]")
            
        # Generate default filename if none provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename:
            # Create safe filename from title
            safe_title = "".join(c if c.isalnum() else "_" for c in title).lower()
            filename = f"{safe_title}_{timestamp}"
            
        # Ensure filename doesn't have extension
        filename = filename.split('.')[0]
        
        # Add appropriate extension based on format
        format = format.lower()
        if format == "markdown":
            ext = "md"
        elif format == "html":
            ext = "html"
        elif format == "txt":
            ext = "txt"
        else:  # json
            ext = "json"
            
        full_filename = f"{filename}.{ext}"
        
        # Create report content
        report_text = ""
        
        if format == "markdown":
            report_text = f"# {title}\n\n"
            report_text += f"*Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            
            for section, section_content in content.items():
                report_text += f"## {section}\n\n"
                if isinstance(section_content, (list, tuple)):
                    for item in section_content:
                        report_text += f"- {item}\n"
                elif isinstance(section_content, dict):
                    for key, value in section_content.items():
                        report_text += f"**{key}**: {value}\n"
                else:
                    report_text += f"{section_content}\n"
                report_text += "\n"
                
        elif format == "html":
            report_text = f"<!DOCTYPE html>\n<html>\n<head>\n<title>{title}</title>\n"
            report_text += "<style>body{font-family:Arial,sans-serif;margin:40px;line-height:1.6}"
            report_text += "h1{color:#333}h2{color:#444;margin-top:30px}</style>\n</head>\n<body>\n"
            report_text += f"<h1>{title}</h1>\n"
            report_text += f"<p><em>Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>\n"
            
            for section, section_content in content.items():
                report_text += f"<h2>{section}</h2>\n"
                if isinstance(section_content, (list, tuple)):
                    report_text += "<ul>\n"
                    for item in section_content:
                        report_text += f"<li>{item}</li>\n"
                    report_text += "</ul>\n"
                elif isinstance(section_content, dict):
                    report_text += "<dl>\n"
                    for key, value in section_content.items():
                        report_text += f"<dt><strong>{key}</strong></dt>\n<dd>{value}</dd>\n"
                    report_text += "</dl>\n"
                else:
                    report_text += f"<p>{section_content}</p>\n"
                    
            report_text += "</body>\n</html>"
            
        elif format == "txt":
            report_text = f"{title.upper()}\n"
            report_text += "=" * len(title) + "\n\n"
            report_text += f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for section, section_content in content.items():
                report_text += f"{section}\n"
                report_text += "-" * len(section) + "\n"
                if isinstance(section_content, (list, tuple)):
                    for item in section_content:
                        report_text += f"* {item}\n"
                elif isinstance(section_content, dict):
                    for key, value in section_content.items():
                        report_text += f"{key}: {value}\n"
                else:
                    report_text += f"{section_content}\n"
                report_text += "\n"
                
        else:  # json
            # For JSON, we create a structured document
            report_data = {
                "title": title,
                "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content": content
            }
            report_text = json.dumps(report_data, indent=2)
            
        # Save the report
        reports_dir = os.path.join(DEFAULT_WORKSPACE, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        file_path = os.path.join(reports_dir, full_filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
            
        # Return success info
        rel_path = os.path.join("reports", full_filename)
        return {
            "status": "success",
            "title": title,
            "format": format,
            "filename": full_filename,
            "path": rel_path,
            "absolute_path": file_path,
            "size_bytes": len(report_text),
            "sections": list(content.keys()),
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "auto_generated": not bool(title) or not bool(content)
        }
    except Exception as e:
        return {
            "error": f"Failed to generate report: {str(e)}",
            "suggestion": "Check your input content and try again"
        }

@mcp.tool()
def smart_report(query: str, title: str = "", format: str = "markdown", filename: str = "") -> dict:
    """
    Automatically collect information from web search based on a query and generate a report.
    
    Args:
        query: The search query to collect information about
        title: Optional report title (if empty, will use the query as title)
        format: Output format (markdown, html, txt, json) - defaults to markdown
        filename: Optional filename (without extension)
    
    Returns:
        Information about the saved report
    """
    try:
        import datetime
        import re
        
        # Use query as title if none provided
        if not title:
            title = f"Report: {query}"
        
        # Step 1: Collect information using websearch
        search_results = None
        api_key = os.getenv("SERPAPI_KEY")
        
        if api_key:
            try:
                from serpapi import GoogleSearch
                
                # Execute search
                params = {
                    "q": query,
                    "api_key": api_key,
                    "engine": "google",
                    "num": 7  # Get more results for better content
                }
                search = GoogleSearch(params)
                results = search.get_dict()
                
                # Get organic results
                search_results = results.get("organic_results", [])
            except Exception as e:
                print(f"[Web search error: {str(e)}]")
                search_results = None
        
        # Step 2: Prepare report content
        content = {}
        
        # Add introduction section
        content["Introduction"] = f"This report was automatically generated based on the query: '{query}'."
        
        # Add search results if available
        if search_results and len(search_results) > 0:
            # Add summary section
            content["Summary"] = f"Found {len(search_results)} relevant sources of information about '{query}'."
            
            # Process and organize the search results
            sources = []
            key_information = []
            
            for i, result in enumerate(search_results):
                # Extract source information
                title = result.get("title", "Untitled Source")
                link = result.get("link", "")
                snippet = result.get("snippet", "No description available")
                
                # Add to sources list
                sources.append(f"{title} - {link}")
                
                # Extract key information from the snippet
                cleaned_snippet = re.sub(r'\s+', ' ', snippet).strip()
                if cleaned_snippet:
                    key_information.append(cleaned_snippet)
            
            # Add sources section
            content["Sources"] = sources
            
            # Add key information section
            if key_information:
                content["Key Information"] = key_information
        else:
            # If no search results, provide a message
            content["Note"] = "No search results were found or web search is not available. Please check your query or verify that your SerpAPI key is configured correctly."
        
        # Add metadata section
        content["Metadata"] = {
            "Generated On": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Query": query,
            "Sources Count": len(search_results) if search_results else 0
        }
        
        # Step 3: Generate the report using the collected content
        return generate_report(
            title=title,
            content=content,
            format=format,
            filename=filename
        )
    except Exception as e:
        return {
            "error": f"Failed to generate smart report: {str(e)}",
            "suggestion": "Check your query and try again"
        }

if __name__ == "__main__":
    mcp.run(transport='stdio')
