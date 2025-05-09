# TACO - Tool And Context Orchestrator

<p align="center">
  <em>A powerful CLI for orchestrating LLM tools and context with Ollama</em>
</p>

TACO combines the power of Large Language Models (via Ollama) with flexible tools and contextual templates to create a versatile command-line interface for AI interactions.

## Features

- 🌮 **Chat with LLMs**: Seamless interaction with Ollama models
- 🧰 **Tool Integration**: Dynamic tool registry for extending capabilities
- 📝 **Context Management**: Template-based context for better conversations
- 🔄 **Pipe Support**: Unix-style pipe integration (`cat file.txt | taco context`)
- 🧠 **Model Selection**: Choose and switch between different LLMs

## Installation

```bash
# Install with pip
pip install taco-cli

# Or install from source
git clone https://github.com/yourusername/taco.git
cd taco
pip install -e .
```

## Quick Start

```bash
# Start interactive chat
taco chat

# List available models
taco model list

# Use a specific model
taco model use llama3

# List available tools
taco tools list

# Add content to context
cat document.txt | taco context add project

# Execute a tool
taco tools run analyze_text "This is sample text"

# Save chat session
taco chat --save=session.json
```

## Command Reference

### Chat Commands
- `taco chat` - Start interactive chat
- `taco "Your question here"` - Single query mode

### Model Management
- `taco model list` - List available models
- `taco model use <name>` - Select a model
- `taco model info <name>` - Show model details

### Tool Management
- `taco tools list` - List available tools
- `taco tools add <path>` - Add a tool
- `taco tools run <name> [args]` - Run a tool
- `taco tools help <name>` - Show tool help

### Context Management
- `taco context list` - List available contexts
- `taco context use <name>` - Set active context
- `taco context add <name>` - Add content to context
- `taco context create <name> <template>` - Create a new context

## Configuration

TACO's configuration is stored in `~/.config/taco/config.json`. You can edit this file directly or use:

```bash
taco config set model.default llama3
taco config set display.color true
```

## Extending TACO

### Adding Custom Tools

Create a Python file with functions:

```python
def my_custom_tool(arg1: str, arg2: int) -> dict:
    """Tool description here"""
    # Tool implementation
    return {"result": "success"}
```

Add it to TACO:

```bash
taco tools add /path/to/my_tools.py
```

### Creating Context Templates

```bash
taco context create coding "Language: {language}\nStyle: {style}"
taco context set coding language Python
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

TACO builds upon:
- [Ollama](https://github.com/ollama/ollama) for LLM integration
- Multiple open-source libraries for terminal UI and tool execution
