"""
TACO Parameter Collector Tool

A tool that collects parameters from users for other tools.
It needs to work in stages - first question, then subsequent questions based on state.
"""
from typing import Dict, Any, List, Optional

def collect_tool_parameters(tool_name: str = "", 
                          questions: List[str] = None,
                          parameter_names: List[str] = None,
                          current_state: Dict[str, Any] = None,
                          user_response: str = None) -> Dict[str, Any]:
    """
    Collect parameters for a tool by asking the user questions one at a time.
    
    This tool maintains state across calls to handle the collection process.
    
    Args:
        tool_name: Name of the tool to collect parameters for
        questions: List of questions to ask the user
        parameter_names: List of parameter names corresponding to questions
        current_state: Current state of the collection process
        user_response: User's response to the previous question
    
    Returns:
        Dict containing next question or collected parameters
    """
    # Initialize state if not provided
    if current_state is None:
        # This is the first call - validate and initialize
        if not tool_name:
            return {
                'status': 'error',
                'message': 'tool_name is required'
            }
        
        if not questions or not isinstance(questions, list):
            return {
                'status': 'error',
                'message': 'questions must be a non-empty list'
            }
        
        # Default parameter names if not provided
        if not parameter_names:
            parameter_names = [f"param_{i}" for i in range(len(questions))]
        
        if len(parameter_names) != len(questions):
            return {
                'status': 'error',
                'message': 'parameter_names must match questions length'
            }
        
        # Initialize collection state
        current_state = {
            'tool_name': tool_name,
            'questions': questions,
            'parameter_names': parameter_names,
            'current_index': 0,
            'collected_params': {}
        }
        
        # Return first question
        return {
            'status': 'collecting',
            'question': questions[0],
            'question_number': 1,
            'total_questions': len(questions),
            'state': current_state,
            'next_tool': 'collect_tool_parameters'
        }
    
    # Process user response if provided
    if user_response is not None:
        current_index = current_state.get('current_index', 0)
        parameter_names = current_state.get('parameter_names', [])
        questions = current_state.get('questions', [])
        collected_params = current_state.get('collected_params', {})
        
        # Store the response
        param_name = parameter_names[current_index]
        collected_params[param_name] = user_response
        
        # Move to next question
        current_index += 1
        current_state['current_index'] = current_index
        current_state['collected_params'] = collected_params
        
        if current_index < len(questions):
            # More questions to ask
            return {
                'status': 'collecting',
                'question': questions[current_index],
                'question_number': current_index + 1,
                'total_questions': len(questions),
                'state': current_state,
                'next_tool': 'collect_tool_parameters'
            }
        else:
            # All parameters collected
            return {
                'status': 'complete',
                'tool_name': current_state['tool_name'],
                'collected_parameters': collected_params,
                'message': f"All parameters collected for {current_state['tool_name']}"
            }
    
    # No response provided - return current state
    return {
        'status': 'waiting',
        'state': current_state,
        'message': 'Waiting for user response'
    }

# Add tool description
def _get_tool_description():
    """Get description for the parameter collector tool"""
    return """collect_tool_parameters:This tool collects parameters by asking questions one at a time and gathering responses."""


def _get_usage_instructions():
    """Get usage instructions for the parameter collector tool"""
    return """
The collect_tool_parameters tool helps gather required parameters from users through a series of questions.

Workflow:
1. First call: Initialize with tool_name and questions
   ```json
   {
     "tool_call": {
       "name": "collect_tool_parameters",
       "parameters": {
         "tool_name": "calculate_mortgage",
         "questions": [
           "What is the loan amount in dollars?",
           "What is the annual interest rate (as a percentage)?",
           "How many years is the loan term?"
         ],
         "parameter_names": ["principal", "annual_rate", "years"]
       }
     }
   }
   ```

2. Tool returns first question and state
3. Present question to user and get their response
4. Call tool again with state and user response:
   ```json
   {
     "tool_call": {
       "name": "collect_tool_parameters",
       "parameters": {
         "current_state": <state from previous response>,
         "user_response": "300000"
       }
     }
   }
   ```

5. Repeat steps 3-4 until all questions are answered
6. Tool returns collected parameters for use with target tool

The tool maintains state across calls to track progress through the questions.
"""

# Attach the description methods
collect_tool_parameters._get_tool_description = _get_tool_description
collect_tool_parameters._get_usage_instructions = _get_usage_instructions