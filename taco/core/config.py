"""
TACO Configuration Management
"""
import os
import json
from typing import Dict, Any, Optional

# Default configuration
DEFAULT_CONFIG = {
    "model": {
        "default": "llama3",
        "host": "http://localhost:11434"
    },
    "display": {
        "color": True,
        "animation": True
    },
    "tools": {
        "paths": []
    },
    "context": {
        "active": None
    }
}

def get_config_path() -> str:
    """Get the path to the config file"""
    config_dir = os.path.expanduser("~/.config/taco")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")

def get_config() -> Dict[str, Any]:
    """Load the configuration file"""
    config_path = get_config_path()
    
    # If config doesn't exist, create default
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    
    # Load config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Ensure all default sections exist
        for section, values in DEFAULT_CONFIG.items():
            if section not in config:
                config[section] = values
        
        return config
    except Exception:
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> bool:
    """Save the configuration to file"""
    config_path = get_config_path()
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False

def set_config_value(key_path: str, value: Any) -> bool:
    """Set a configuration value using dot notation (e.g., 'model.default')"""
    config = get_config()
    
    # Split the key path
    parts = key_path.split('.')
    
    if len(parts) != 2:
        return False
    
    section, key = parts
    
    # Check if section exists
    if section not in config:
        config[section] = {}
    
    # Set the value
    config[section][key] = value
    
    # Save the config
    return save_config(config)
