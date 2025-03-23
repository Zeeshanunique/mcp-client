import os
import subprocess
import sys
import platform
import requests
import re
import json
import datetime
import random
import httpx
import asyncio
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv, set_key
from mcp.server.fastmcp import FastMCP
from serpapi import GoogleSearch

# Load environment variables
load_dotenv()

mcp = FastMCP("terminal")

# Ensure the workspace path is correctly formatted for Windows
DEFAULT_WORKSPACE = os.path.join("C:/Users/dell/Desktop/mcp/workspace")

# Constants for NWS API
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

# Common utility functions
def get_full_path(relative_path: str) -> str:
    """Get the full path from a workspace-relative path."""
    return os.path.join(DEFAULT_WORKSPACE, relative_path)

def format_error_response(error_message: str, suggestion: str = "") -> Dict[str, str]:
    """Create a standardized error response."""
    response = {"error": error_message}
    if suggestion:
        response["suggestion"] = suggestion
    return response

# National Weather Service API utility functions
async def make_nws_request(url: str) -> Dict[str, Any]:
    """Make a request to the National Weather Service API."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return {}
    except httpx.RequestError as e:
        print(f"Request error: {str(e)}")
        return {}
    except Exception as e:
        print(f"Error during API request: {str(e)}")
        return {}

def format_alert(alert_feature: Dict[str, Any]) -> str:
    """Format a weather alert into a readable string."""
    props = alert_feature.get("properties", {})
    
    headline = props.get("headline", "Unknown Alert")
    severity = props.get("severity", "Unknown")
    urgency = props.get("urgency", "Unknown")
    description = props.get("description", "No description available")
    instruction = props.get("instruction", "No specific instructions provided")
    
    # Extract just date and time from the timestamps
    effective = props.get("effective", "")
    expires = props.get("expires", "")
    
    if effective:
        effective = effective.split('T')[0] + ' ' + effective.split('T')[1][:5]
    if expires:
        expires = expires.split('T')[0] + ' ' + expires.split('T')[1][:5]
    
    # Truncate description if it's too long
    if len(description) > 500:
        description = description[:500] + "..."
    
    # Format the alert
    alert_text = f"""
📢 {headline}
Severity: {severity.upper()}
Urgency: {urgency.capitalize()}
Effective: {effective}
Expires: {expires}

{description}

INSTRUCTIONS:
{instruction}
"""
    return alert_text.strip()

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
async def get_weather_alerts(state: str) -> Dict[str, Any]:
    """
    Get weather alerts for a US state from the National Weather Service.
    
    Args:
        state: Two-letter US state code (e.g., CA, NY, TX)
    
    Returns:
        Dictionary with alerts information or error details
    """
    if not isinstance(state, str) or len(state) != 2:
        return format_error_response(
            "Invalid state code format",
            "Please provide a valid two-letter US state code (e.g., CA, NY, TX)"
        )
    
    # Convert to uppercase
    state = state.upper()
    
    # Get alerts from NWS API
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    
    if not data or "features" not in data:
        return format_error_response(
            "Unable to fetch alerts or no alerts found",
            "The National Weather Service API may be experiencing issues"
        )
    
    # Process the alerts
    alerts_count = len(data["features"])
    
    if alerts_count == 0:
        return {
            "state": state,
            "count": 0,
            "message": "No active weather alerts for this state.",
            "alerts": []
        }
    
    # Format alerts for response
    formatted_alerts = []
    for feature in data["features"]:
        props = feature.get("properties", {})
        
        alert_data = {
            "headline": props.get("headline", "Unknown Alert"),
            "severity": props.get("severity", "Unknown"),
            "urgency": props.get("urgency", "Unknown"),
            "certainty": props.get("certainty", "Unknown"),
            "event": props.get("event", "Unknown Event"),
            "effective": props.get("effective", ""),
            "expires": props.get("expires", ""),
            "sender": props.get("senderName", "National Weather Service"),
            "description": props.get("description", "No description available"),
            "instruction": props.get("instruction", "No specific instructions provided"),
            "area": props.get("areaDesc", "Unknown area")
        }
        
        formatted_alerts.append(alert_data)
    
    # Create the response
    return {
        "state": state,
        "count": alerts_count,
        "message": f"Found {alerts_count} active weather alert{'s' if alerts_count != 1 else ''} for {state}.",
        "alerts": formatted_alerts
    }

@mcp.tool()
async def get_nws_forecast(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get detailed weather forecast for a US location from the National Weather Service.
    
    Args:
        latitude: Latitude of the location (decimal degrees)
        longitude: Longitude of the location (decimal degrees)
    
    Returns:
        Dictionary with forecast information or error details
    """
    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return format_error_response(
                "Invalid coordinates",
                "Latitude must be between -90 and 90, and longitude between -180 and 180"
            )
        
        # First get the forecast grid endpoint
        points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
        points_data = await make_nws_request(points_url)
        
        if not points_data or "properties" not in points_data:
            return format_error_response(
                "Unable to fetch forecast data for this location",
                "The location might be outside NWS coverage area (US only) or the API may be experiencing issues"
            )
        
        # Get location info
        location_props = points_data["properties"]
        location_info = {
            "city": location_props.get("relativeLocation", {}).get("properties", {}).get("city", "Unknown"),
            "state": location_props.get("relativeLocation", {}).get("properties", {}).get("state", "Unknown"),
            "grid_id": location_props.get("gridId", ""),
            "grid_x": location_props.get("gridX", ""),
            "grid_y": location_props.get("gridY", "")
        }
        
        # Get the forecast URL from the points response
        forecast_url = location_props.get("forecast")
        if not forecast_url:
            return format_error_response(
                "No forecast URL available for this location",
                "The location might be outside NWS coverage area (US only)"
            )
        
        hourly_forecast_url = location_props.get("forecastHourly")
        
        # Get the main forecast data
        forecast_data = await make_nws_request(forecast_url)
        
        if not forecast_data or "properties" not in forecast_data:
            return format_error_response(
                "Unable to fetch detailed forecast",
                "The National Weather Service API may be experiencing issues"
            )
        
        # Extract and format forecast periods
        periods = forecast_data["properties"]["periods"]
        
        # Process the forecast periods
        forecast_periods = []
        for period in periods:
            forecast_period = {
                "name": period.get("name", "Unknown"),
                "start_time": period.get("startTime", ""),
                "end_time": period.get("endTime", ""),
                "temperature": period.get("temperature"),
                "temperature_unit": period.get("temperatureUnit"),
                "temperature_trend": period.get("temperatureTrend"),
                "wind_speed": period.get("windSpeed"),
                "wind_direction": period.get("windDirection"),
                "icon": period.get("icon"),
                "short_forecast": period.get("shortForecast"),
                "detailed_forecast": period.get("detailedForecast")
            }
            forecast_periods.append(forecast_period)
        
        # Get hourly forecast if available
        hourly_periods = []
        if hourly_forecast_url:
            hourly_data = await make_nws_request(hourly_forecast_url)
            
            if hourly_data and "properties" in hourly_data and "periods" in hourly_data["properties"]:
                # Limit to next 24 hours
                hourly_periods_raw = hourly_data["properties"]["periods"][:24]
                
                for period in hourly_periods_raw:
                    hourly_period = {
                        "time": period.get("startTime", ""),
                        "temperature": period.get("temperature"),
                        "temperature_unit": period.get("temperatureUnit"),
                        "wind_speed": period.get("windSpeed"),
                        "wind_direction": period.get("windDirection"),
                        "icon": period.get("icon"),
                        "forecast": period.get("shortForecast")
                    }
                    hourly_periods.append(hourly_period)
        
        # Create the final response
        return {
            "location": location_info,
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude
            },
            "forecast": forecast_periods,
            "hourly_forecast": hourly_periods,
            "updated": forecast_data.get("properties", {}).get("updated", ""),
            "units": "us",  # NWS always uses US units
            "attribution": "Data from National Weather Service (weather.gov)"
        }
        
    except Exception as e:
        return format_error_response(
            f"Failed to get forecast: {str(e)}",
            "There was a problem fetching the forecast data"
        )

@mcp.tool()
def geocode_location(address: str) -> Dict[str, Any]:
    """
    Convert a location name or address to latitude and longitude coordinates.
    
    Args:
        address: Location name or address (e.g., "New York City", "1600 Pennsylvania Ave, Washington DC")
    
    Returns:
        Dictionary with location coordinates and details
    """
    try:
        # Check for OpenCage API key
        api_key = os.getenv("OPENCAGE_API_KEY")
        
        if not api_key:
            return format_error_response(
                "OPENCAGE_API_KEY environment variable not set",
                "Please add your OpenCage Geocoding API key to the .env file"
            )
        
        # Build the API request
        base_url = "https://api.opencagedata.com/geocode/v1/json"
        params = {
            "q": address,
            "key": api_key,
            "limit": 1
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for results
        if data.get("total_results", 0) == 0:
            return format_error_response(
                f"Could not find coordinates for '{address}'",
                "Check the spelling or try a different location"
            )
        
        # Extract location data
        result = data["results"][0]
        geometry = result["geometry"]
        components = result["components"]
        
        # Format the response
        location_info = {
            "coordinates": {
                "latitude": geometry["lat"],
                "longitude": geometry["lng"]
            },
            "formatted_address": result.get("formatted", ""),
            "components": {
                "country": components.get("country", ""),
                "country_code": components.get("country_code", "").upper(),
                "state": components.get("state", ""),
                "county": components.get("county", ""),
                "city": components.get("city", components.get("town", components.get("village", ""))),
                "postcode": components.get("postcode", "")
            },
            "confidence": result.get("confidence", 0),
            "attribution": "Geocoding provided by OpenCage"
        }
        
        return location_info
        
    except requests.exceptions.RequestException as e:
        return format_error_response(
            f"Geocoding request failed: {str(e)}",
            "Check your internet connection and try again"
        )
    except Exception as e:
        return format_error_response(
            f"Failed to geocode address: {str(e)}",
            "There was a problem processing the location"
        )

@mcp.tool()
def set_opencage_api_key(api_key: str) -> Dict[str, Any]:
    """
    Set or update the OpenCage Geocoding API key in the .env file.
    
    Args:
        api_key: Your OpenCage API key from opencagedata.com
    
    Returns:
        Status message about the operation
    """
    try:
        # Find .env file (reusing logic from set_serpapi_key)
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if not os.path.exists(env_path):
            # Try parent directory
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
            if not os.path.exists(env_path):
                # Create new .env file in current directory
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
                with open(env_path, 'w') as f:
                    f.write(f"OPENCAGE_API_KEY={api_key}\n")
                return {
                    "status": "success",
                    "message": f"Created new .env file with OPENCAGE_API_KEY at {env_path}"
                }
        
        # Update existing .env file
        set_key(env_path, "OPENCAGE_API_KEY", api_key)
        
        # Update current environment
        os.environ["OPENCAGE_API_KEY"] = api_key
        
        # Test the key with a simple API call
        test_url = "https://api.opencagedata.com/geocode/v1/json"
        test_params = {
            "q": "New York City",
            "key": api_key,
            "limit": 1
        }
        
        response = requests.get(test_url, params=test_params, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "message": f"OpenCage API key saved to {env_path} and verified working"
            }
        else:
            error_data = response.json()
            return {
                "status": "warning",
                "message": f"OpenCage API key saved to {env_path}, but test query failed",
                "error": str(error_data),
                "suggestion": "The API key may be invalid or have usage limitations"
            }
            
    except Exception as e:
        return format_error_response(
            f"Failed to update OpenCage API key: {str(e)}",
            "You may need to manually add OPENCAGE_API_KEY=your_key_here to your .env file"
        )

@mcp.tool()
def websearch(query: str) -> Dict[str, Any]:
    """
    Perform a web search using SerpAPI.
    
    Args:
        query: The search query.
    
    Returns:
        A dictionary with search results or error information.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return format_error_response(
            "SERPAPI_KEY environment variable not set",
            "Please add your SerpAPI key to the .env file"
        )
    
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
            return format_error_response(
                "No results found for the query",
                "Try a different search query with more specific terms"
            )
        
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
        
        return format_error_response(f"Search error: {error_message}", suggestion)

@mcp.tool()
def diagnose_websearch(dummy: str = "run") -> Dict[str, Any]:
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
def set_serpapi_key(api_key: str) -> Dict[str, Any]:
    """
    Set or update the SerpAPI key in the .env file.
    
    Args:
        api_key: Your SerpAPI key from serpapi.com
    
    Returns:
        A status message about the operation
    """
    # Validate key format (basic check)
    if not re.match(r'^[a-zA-Z0-9]{32,}$', api_key):
        return format_error_response(
            "Invalid API key format",
            "SerpAPI keys are usually at least 32 characters long and contain only letters and numbers"
        )
    
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
        return format_error_response(
            f"Failed to update SerpAPI key: {str(e)}", 
            "You may need to manually add SERPAPI_KEY=your_key_here to your .env file"
        )

@mcp.tool()
def read_file(file_path: str) -> Dict[str, Any]:
    """
    Read the contents of a file.
    
    Args:
        file_path: Relative path to the file from the workspace
    
    Returns:
        Dictionary with file contents or error
    """
    try:
        full_path = get_full_path(file_path)
        if not os.path.exists(full_path):
            return format_error_response(
                f"File not found: {file_path}", 
                "Check the file path and try again"
            )
            
        with open(full_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        return {
            "content": content,
            "path": file_path,
            "size": len(content)
        }
    except Exception as e:
        return format_error_response(
            f"Failed to read file: {str(e)}", 
            "Check file permissions or encoding"
        )

@mcp.tool()
def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Write content to a file.
    
    Args:
        file_path: Relative path to the file from the workspace
        content: Text content to write to the file
    
    Returns:
        Status of the write operation
    """
    try:
        full_path = get_full_path(file_path)
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        return {
            "status": "success",
            "message": f"Successfully wrote {len(content)} bytes to {file_path}"
        }
    except Exception as e:
        return format_error_response(
            f"Failed to write file: {str(e)}", 
            "Check file permissions or path validity"
        )

@mcp.tool()
def list_files(directory: str = "") -> Dict[str, Any]:
    """
    List files and directories in a specified directory.
    
    Args:
        directory: Relative path to the directory from the workspace (empty for root)
    
    Returns:
        List of files and directories in the specified path
    """
    try:
        full_path = get_full_path(directory)
        if not os.path.exists(full_path):
            return format_error_response(
                f"Directory not found: {directory}", 
                "Check the directory path and try again"
            )
            
        if not os.path.isdir(full_path):
            return format_error_response(
                f"Path is not a directory: {directory}", 
                "Provide a directory path, not a file path"
            )
            
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
        return format_error_response(
            f"Failed to list directory: {str(e)}", 
            "Check directory permissions or path validity"
        )

@mcp.tool()
def get_system_info() -> Dict[str, Any]:
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
        return format_error_response(f"Failed to get system info: {str(e)}")

@mcp.tool()
def fetch_webpage(url: str) -> Dict[str, Any]:
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
        return format_error_response(
            f"Failed to fetch webpage: {str(e)}", 
            "Check the URL and your internet connection"
        )

@mcp.tool()
def search_text(file_path: str, search_term: str) -> Dict[str, Any]:
    """
    Search for text in a file.
    
    Args:
        file_path: Relative path to the file from the workspace
        search_term: Text to search for
    
    Returns:
        Lines containing the search term with line numbers
    """
    try:
        full_path = get_full_path(file_path)
        if not os.path.exists(full_path):
            return format_error_response(
                f"File not found: {file_path}", 
                "Check the file path and try again"
            )
            
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
        return format_error_response(
            f"Failed to search file: {str(e)}", 
            "Check file permissions or encoding"
        )

@mcp.tool()
def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyze text to extract statistics and information.
    
    Args:
        text: The text to analyze
    
    Returns:
        Text statistics including word count, character count, etc.
    """
    try:
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
        return format_error_response(f"Failed to analyze text: {str(e)}")

@mcp.tool()
def calculate(expression: str) -> Dict[str, Any]:
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
            return format_error_response(
                "Potentially unsafe expression",
                "Use only basic arithmetic operations and numbers"
            )
        
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
        return format_error_response(
            "Invalid syntax in expression",
            "Check your expression for syntax errors"
        )
    except ZeroDivisionError:
        return format_error_response(
            "Division by zero",
            "Check your expression for division by zero"
        )
    except Exception as e:
        return format_error_response(
            f"Calculation error: {str(e)}",
            "Use only basic arithmetic operations (+, -, *, /, **, ())"
        )

@mcp.tool()
def image_info(image_url: str) -> Dict[str, Any]:
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
        return format_error_response(
            "PIL (Pillow) package not installed",
            "Install Pillow with: pip install Pillow"
        )
    except requests.exceptions.RequestException as e:
        return format_error_response(
            f"Failed to download image: {str(e)}",
            "Check the URL and your internet connection"
        )
    except Exception as e:
        return format_error_response(
            f"Failed to process image: {str(e)}",
            "Ensure the URL points to a valid image"
        )

@mcp.tool()
def generate_report(title: str = "", content: dict = None, format: str = "markdown", filename: str = "") -> Dict[str, Any]:
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
        ext_map = {
            "markdown": "md",
            "html": "html",
            "txt": "txt",
            "json": "json"
        }
        ext = ext_map.get(format, "md")
        full_filename = f"{filename}.{ext}"
        
        # Create report content based on format
        report_text = _format_report_content(title, content, format)
            
        # Save the report
        reports_dir = get_full_path("reports")
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
        return format_error_response(
            f"Failed to generate report: {str(e)}",
            "Check your input content and try again"
        )

def _format_report_content(title: str, content: Dict[str, Any], format: str) -> str:
    """Helper function to format report content based on the specified format."""
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if format == "markdown":
        report_text = f"# {title}\n\n"
        report_text += f"*Generated on {current_time}*\n\n"
        
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
        report_text += f"<p><em>Generated on {current_time}</em></p>\n"
        
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
        report_text += f"Generated on {current_time}\n\n"
        
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
            "generated_at": current_time,
            "content": content
        }
        report_text = json.dumps(report_data, indent=2)
    
    return report_text

@mcp.tool()
def smart_report(query: str, title: str = "", format: str = "markdown", filename: str = "") -> Dict[str, Any]:
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
        # Use query as title if none provided
        if not title:
            title = f"Report: {query}"
        
        # Step 1: Collect information using websearch
        search_results = _fetch_search_results(query)
        
        # Step 2: Prepare report content
        content = _prepare_report_content(query, search_results)
        
        # Step 3: Generate the report using the collected content
        return generate_report(
            title=title,
            content=content,
            format=format,
            filename=filename
        )
    except Exception as e:
        return format_error_response(
            f"Failed to generate smart report: {str(e)}",
            "Check your query and try again"
        )

def _fetch_search_results(query: str) -> Optional[List[Dict[str, Any]]]:
    """Helper function to fetch search results for a query."""
    search_results = None
    api_key = os.getenv("SERPAPI_KEY")
    
    if api_key:
        try:
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
    
    return search_results

def _prepare_report_content(query: str, search_results: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Helper function to prepare report content from search results."""
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
        
        for result in search_results:
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
    
    return content

@mcp.tool()
def get_weather(location: str, units: str = "metric") -> Dict[str, Any]:
    """
    Get current weather information for a location.
    
    Args:
        location: City name or location (e.g., "New York", "Paris, France")
        units: Temperature units - metric (Celsius) or imperial (Fahrenheit)
    
    Returns:
        Weather information including temperature, conditions, and forecast
    """
    try:
        # Check for OpenWeather API key
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return format_error_response(
                "OPENWEATHER_API_KEY environment variable not set",
                "Please add your OpenWeather API key to the .env file"
            )
        
        # Validate units parameter
        if units not in ["metric", "imperial"]:
            units = "metric"  # Default to metric if invalid
            
        # Format location for the API
        formatted_location = location.strip().replace(" ", "+")
        
        # Make API request to OpenWeather
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": formatted_location,
            "appid": api_key,
            "units": units
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        # Parse the response
        weather_data = response.json()
        
        # Check if the API returned an error
        if 'cod' in weather_data and weather_data['cod'] != 200:
            return format_error_response(
                f"Weather API error: {weather_data.get('message', 'Unknown error')}",
                "Check that the location name is correct"
            )
        
        # Extract relevant weather information
        temperature = weather_data.get('main', {}).get('temp')
        feels_like = weather_data.get('main', {}).get('feels_like')
        humidity = weather_data.get('main', {}).get('humidity')
        pressure = weather_data.get('main', {}).get('pressure')
        
        wind_speed = weather_data.get('wind', {}).get('speed')
        wind_direction = weather_data.get('wind', {}).get('deg')
        
        conditions = weather_data.get('weather', [{}])[0].get('main')
        description = weather_data.get('weather', [{}])[0].get('description')
        
        country = weather_data.get('sys', {}).get('country')
        city_name = weather_data.get('name')
        
        # Format the response
        temp_unit = "°C" if units == "metric" else "°F"
        speed_unit = "m/s" if units == "metric" else "mph"
        
        weather_info = {
            "location": {
                "city": city_name,
                "country": country,
                "coordinates": {
                    "lon": weather_data.get('coord', {}).get('lon'),
                    "lat": weather_data.get('coord', {}).get('lat')
                }
            },
            "current": {
                "temperature": f"{temperature}{temp_unit}",
                "feels_like": f"{feels_like}{temp_unit}",
                "humidity": f"{humidity}%",
                "pressure": f"{pressure} hPa",
                "wind": {
                    "speed": f"{wind_speed} {speed_unit}",
                    "direction": _get_wind_direction(wind_direction)
                },
                "conditions": conditions,
                "description": description,
                "time": datetime.datetime.fromtimestamp(weather_data.get('dt', 0)).strftime('%Y-%m-%d %H:%M:%S')
            },
            "units": units
        }
        
        # Add sunrise/sunset if available
        if 'sys' in weather_data and 'sunrise' in weather_data['sys'] and 'sunset' in weather_data['sys']:
            sunrise = datetime.datetime.fromtimestamp(weather_data['sys']['sunrise'])
            sunset = datetime.datetime.fromtimestamp(weather_data['sys']['sunset'])
            
            weather_info["sun"] = {
                "sunrise": sunrise.strftime('%H:%M:%S'),
                "sunset": sunset.strftime('%H:%M:%S')
            }
        
        return weather_info
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else "unknown"
        return format_error_response(
            f"HTTP error occurred (code: {status_code}): {str(e)}",
            "The weather service might be down or the location is invalid"
        )
    except requests.exceptions.ConnectionError:
        return format_error_response(
            "Connection error occurred",
            "Check your internet connection and try again"
        )
    except requests.exceptions.Timeout:
        return format_error_response(
            "Request timed out",
            "The weather service is taking too long to respond, try again later"
        )
    except requests.exceptions.RequestException as e:
        return format_error_response(
            f"Request error: {str(e)}",
            "There was a problem with the weather service request"
        )
    except Exception as e:
        return format_error_response(
            f"Failed to get weather information: {str(e)}"
        )

def _get_wind_direction(degrees: float) -> str:
    """Convert wind direction in degrees to cardinal direction."""
    directions = [
        "North", "North-Northeast", "Northeast", "East-Northeast",
        "East", "East-Southeast", "Southeast", "South-Southeast",
        "South", "South-Southwest", "Southwest", "West-Southwest",
        "West", "West-Northwest", "Northwest", "North-Northwest"
    ]
    index = round(degrees / 22.5) % 16
    return directions[index]

if __name__ == "__main__":
    mcp.run(transport='stdio')
