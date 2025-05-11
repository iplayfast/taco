# TACO Tool Orchestration Design Document

## Overview

This document outlines the design for TACO's tool orchestration system, which enables complex tool workflows while maintaining clean separation of concerns and providing good user experience.

## Architecture

### Component Responsibilities

1. **Chat System**
   - Maintains conversation history
   - Stores the original user prompt
   - Manages tool_stack for orchestration state
   - Handles user commands and context switches

2. **Ollama**
   - Orchestrates tool execution based on context
   - Determines which tools to use
   - Manages the flow between tools
   - Interprets results for users

3. **Tools**
   - Stateless, single-purpose functions
   - Provide their own usage instructions via `get_usage_instructions()`
   - Return structured results
   - Can indicate need for other tools

### State Management

The chat system maintains a `tool_stack` structure that tracks the current tool execution context. This stack:
- Grows when tools require other tools
- Shrinks as tools complete
- Gets cleared on user abandonment or context switch
- Is included in the system prompt for Ollama's context

## Tool Workflow

### Standard Flow

1. User makes a request
2. Ollama identifies the need for a specific tool
3. Tool's usage instructions are retrieved
4. If parameters are missing:
   - `collect_tool_parameters` usage instructions are retrieved
   - Parameters are collected one at a time from the user
5. Tool is executed with collected parameters
6. If tool needs another tool (e.g., `save_file`):
   - New tool is pushed onto the stack
   - Process repeats for the new tool
7. As tools complete, stack unwinds
8. Final result is presented to user

### Example: Code Generation Flow

```
User: "create a hello world program in python"

Stack progression:
1. [] → [create_code]
2. [create_code] → [create_code, collect_tool_parameters]
3. [create_code, collect_tool_parameters] → [create_code]  // after collection
4. [create_code] → [create_code, save_file]
5. [create_code, save_file] → [create_code]  // after saving
6. [create_code] → []  // complete
```

## User Controls

### Commands

- `/cancel` - Abandon current tool workflow and clear stack
- `/status` - Display current tool stack and context
- `/help` - Show available commands
- `/tools` - List all available tools
- `/tool <name>` - Show detailed information about a specific tool

### Abandonment Scenarios

1. **Explicit cancellation**: User types `/cancel`
2. **Empty response**: User presses Enter with no input
   - System prompts: "Continue with current task? (y/n)"
3. **Context switch**: User asks unrelated question
   - System detects topic change and clears stack

## Error Handling

1. **Tool failures**
   - Error is reported to user
   - Tool stack is cleared
   - User returns to normal conversation mode

2. **Parameter validation failures**
   - First attempt: Tool reports invalid parameters
   - System retries once with additional parameter guidance
   - If still fails: Treated as general tool failure

3. **Stack depth limits**
   - Maximum depth: 20 levels
   - At limit: Show `/status` and prompt user
   - User can continue (Y) for another 20 levels
   - Or cancel (N) to abandon workflow

## Implementation Details

### Tool Interface

Every tool should implement:
```python
def tool_function(param1, param2, ...):
    """Tool description"""
    # Tool implementation
    pass

def _get_tool_description():
    """Return formatted description with parameters"""
    pass

def _get_usage_instructions():
    """Return detailed usage instructions"""
    pass

# Attach metadata
tool_function._get_tool_description = _get_tool_description
tool_function._get_usage_instructions = _get_usage_instructions
```

### Tool Stack Structure

```python
class ChatSession:
    def __init__(self):
        self.tool_stack = []  # Stack of current tool contexts
        self.original_prompt = None  # User's original request
        
    def push_tool(self, tool_name, context):
        self.tool_stack.append({
            'tool': tool_name,
            'context': context,
            'timestamp': datetime.now()
        })
    
    def pop_tool(self):
        if self.tool_stack:
            return self.tool_stack.pop()
        return None
    
    def clear_stack(self):
        self.tool_stack = []
        self.original_prompt = None
```

### System Prompt Enhancement

The system prompt includes tool context when stack is not empty:
```
Current tool context:
- Active tool: create_code
- Waiting for: parameter collection
- Original request: "create a hello world program"
- Stack depth: 2

Available actions:
- Continue with parameter collection
- Use /cancel to abandon current task
- Use /status to see full context
```

## Benefits

1. **Clean Architecture**
   - Each component has single responsibility
   - Tools remain simple and stateless
   - Easy to add new tools

2. **User Control**
   - Clear visibility into current state
   - Multiple ways to abandon workflows
   - Protection against runaway processes

3. **Maintainability**
   - Tool logic separated from orchestration
   - Easy to debug with stack visibility
   - Consistent patterns across all tools

4. **Flexibility**
   - Tools can compose naturally
   - Complex workflows emerge from simple tools
   - Context preserved throughout workflow

## Future Enhancements

1. **Persistent Workflows**
   - Save/resume complex tool workflows
   - Workflow templates for common tasks

2. **Parallel Execution**
   - Execute independent tools concurrently
   - Merge results intelligently

3. **Conditional Flows**
   - Tools can specify conditional next steps
   - Branch based on results

4. **Progress Indicators**
   - Show progress for long-running tools
   - Estimated completion times

5. **Undo/Redo**
   - Undo last tool action
   - Replay workflows with modifications