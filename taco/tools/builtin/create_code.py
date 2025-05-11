"""
TACO Create Code Tool - Generate code based on prompts
Enhanced with context-aware parameter handling
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path
from taco.core.config import get_config
from taco.core.model import ModelManager

def create_code(prompt: str, 
               workingdir: str = "", 
               requirements: str = "", 
               model: str = "",
               _context_aware: bool = True) -> Dict[str, Any]:
    """
    Create code based on user prompt with specified configuration.
    
    Args:
        prompt: The user's code generation request
        workingdir: Working directory for the generated code
        requirements: Requirements file name
        model: Model to use for generation
        _context_aware: Whether to use context-aware parameter collection
    
    Returns:
        Dict containing generation result
    """
    # Check for missing parameters if context-aware
    if _context_aware and (not workingdir or not requirements or not model):
        # Build questions for missing parameters
        questions = []
        parameter_names = []
        
        if not workingdir:
            questions.append("What directory should I save the files in?")
            parameter_names.append("workingdir")
        if not requirements:
            questions.append("What should I name the requirements file?")
            parameter_names.append("requirements")
        if not model:
            questions.append("Which model should I use for code generation?")
            parameter_names.append("model")
        
        return {
            'status': 'needs_parameters',
            'tool_name': 'create_code',
            'parameters_needed': parameter_names,
            'questions': questions,
            'parameter_names': parameter_names,
            'next_tool': 'collect_tool_parameters',
            'context': {
                'original_params': {
                    'prompt': prompt,
                    'workingdir': workingdir,
                    'requirements': requirements,
                    'model': model
                }
            }
        }
    
    # Get config defaults
    config = get_config()
    tool_config = config.get('tools', {}).get('create_code', {})
    
    # Use defaults if not provided
    if not workingdir:
        workingdir = tool_config.get('workingdir', '~/code_projects')
    if not requirements:
        requirements = tool_config.get('requirements', 'requirements.txt')
    if not model:
        model = tool_config.get('model', config.get('model', {}).get('default', 'llama3'))
    
    # Expand user path
    workingdir = os.path.expanduser(workingdir)
    
    # Create working directory if it doesn't exist
    try:
        Path(workingdir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Failed to create working directory: {str(e)}"
        }
    
    # Initialize model manager
    model_manager = ModelManager()
    
    # Generate code using the specified model
    try:
        # Create a direct prompt asking for code in JSON format
        code_prompt = f"""
Generate code for the following request:
{prompt}

Return the code in JSON format with the following structure:
{{
    "code": "the actual code here",
    "language": "programming language used",
    "filename": "suggested filename",
    "description": "brief description of what the code does",
    "requirements": ["list", "of", "required", "packages"] or null if none needed
}}

Please provide only the JSON response, no additional text.
"""
        
        # Make direct Ollama API call
        response = model_manager.generate_response(
            model,
            [{"role": "user", "content": code_prompt}]
        )
        
        # Parse the JSON response
        try:
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'({.*})', response, re.DOTALL)
            if json_match:
                code_data = json.loads(json_match.group(1))
            else:
                # If no JSON found, try to parse the whole response
                code_data = json.loads(response)
            
            # Extract code and metadata
            code_content = code_data.get('code', '')
            language = code_data.get('language', 'text')
            suggested_filename = code_data.get('filename', 'generated_code.txt')
            description = code_data.get('description', '')
            requirements_list = code_data.get('requirements', [])
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: treat entire response as code
            code_content = response
            language = 'text'
            suggested_filename = 'generated_code.txt'
            description = 'Generated code'
            requirements_list = []
        
        # Return the generated code data - let another tool handle saving
        return {
            'status': 'success',
            'code': code_content,
            'language': language,
            'filename': suggested_filename,
            'description': description,
            'requirements': requirements_list,
            'workingdir': workingdir,
            'requirements_file': requirements,
            'next_tool': 'save_code',
            'message': f"Code generated successfully. Ready to save to {workingdir}"
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Failed to generate code: {str(e)}"
        }

# Add custom description method
def _get_tool_description():
    """Custom description for create_code tool"""
    return """create_code: Generate code"""



def _get_usage_instructions():
    """Custom usage instructions for create_code tool"""
    return """
The create_code tool generates code based on natural language prompts.
It's context-aware and will use project defaults when available.

IMPORTANT: Only provide the 'prompt' parameter. Do NOT provide default values for workingdir, requirements, or model. The tool will collect these from the user if needed.

Workflow:
1. Call create_code with ONLY the prompt parameter
2. If parameters are missing, the tool will return status='needs_parameters'
3. The tool will guide you to use collect_tool_parameters
4. After collecting parameters, call create_code again with all values
5. Use the save_code tool to save the generated files

Example initial call:
```json
{
  "tool_call": {
    "name": "create_code",
    "parameters": {
      "prompt": "Create a snake game using pygame"
    }
  }
}
""";    

# Attach the description methods to the function
create_code._get_tool_description = _get_tool_description
create_code._get_usage_instructions = _get_usage_instructions