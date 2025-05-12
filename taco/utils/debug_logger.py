"""
TACO Debug Logger
Handles comprehensive debug logging for the entire system.
"""
import os
import json
from rich.console import Console
from typing import Dict, List, Any, Optional

console = Console()

class DebugLogger:
    """Comprehensive debug logger for TACO"""
    
    def __init__(self, enabled: bool = False):
        """Initialize debug logger"""
        self.enabled = enabled
        
        # Check environment variable for debug level
        env_debug = os.environ.get('TACO_DEBUG_LEVEL', 'INFO').upper()
        if env_debug in ['DEBUG', 'VERBOSE']:
            self.enabled = True
    
    def enable(self):
        """Enable debugging"""
        self.enabled = True
    
    def disable(self):
        """Disable debugging"""
        self.enabled = False
    
    def log(self, message: str, category: str = "INFO", color: str = "blue"):
        """Log a debug message"""
        if not self.enabled:
            return
        
        # Print to console
        console.print(f"[{color}]DEBUG {category}: {message}[/{color}]")
    
    def log_error(self, message: str):
        """Log an error message"""
        self.log(message, "ERROR", "red")
    
    def log_warning(self, message: str):
        """Log a warning message"""
        self.log(message, "WARNING", "yellow")
    
    def log_success(self, message: str):
        """Log a success message"""
        self.log(message, "SUCCESS", "green")
    
    def log_json(self, data: Any, label: str = "JSON"):
        """Log a JSON object"""
        if not self.enabled:
            return
        
        if isinstance(data, dict) or isinstance(data, list):
            try:
                json_str = json.dumps(data, indent=2)
                if len(json_str) > 1000:
                    json_str = json_str[:1000] + "... (truncated)"
                self.log(f"{label}:\n{json_str}", "JSON", "cyan")
            except Exception as e:
                self.log(f"{label}: {str(data)} (Error formatting JSON: {str(e)})", "JSON", "cyan")
        else:
            self.log(f"{label}: {str(data)}", "JSON", "cyan")
    
    def log_dataflow(self, stage: str, data: Any):
        """Log data flow between components"""
        if not self.enabled:
            return
        
        message = f"DataFlow [{stage}]"
        self.log(message, "FLOW", "magenta")
        self.log_json(data, f"DataFlow [{stage}]")

# Global instance
debug_logger = DebugLogger()