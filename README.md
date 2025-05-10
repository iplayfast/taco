# TACO - Tool And Context Orchestrator

<p align="center">
  <img src="docs/taco_logo.ascii" alt="TACO ASCII Logo" width="600">
</p>

<p align="center">
  <em>A powerful CLI for orchestrating LLM tools and context with Ollama</em>
</p>

TACO is a command-line interface that combines the power of Large Language Models (via Ollama) with flexible tools and contextual templates to create a versatile environment for AI interactions.

## Features

- 🌮 **Chat with LLMs**: Seamless interaction with Ollama models
- 🧰 **Tool Integration**: Dynamic tool registry for extending capabilities
- 📝 **Context Management**: Template-based context for better conversations
- 🔄 **Pipe Support**: Unix-style pipe integration (`cat file.txt | python main.py context add`)
- 🧠 **Model Selection**: Choose and switch between different LLMs

## Requirements

- Python 3.10 or higher
- [Ollama](https://ollama.ai/) installed and running

## Installation

### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/taco.git
cd taco

# Install uv if not already installed
pip install uv

# Create virtual environment and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Linux/macOS
# OR
# .venv\Scripts\activate  # On Windows
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/taco.git
cd taco

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# OR
# .venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

Before running TACO, make sure Ollama is running in the background:

```bash
# In a separate terminal
ollama serve
```

Then you can start using TACO:

```bash
# Start interactive chat
python main.py

# List available models
python main.py model list

# Use a specific model
python main.py model use gemma3

# Execute a tool
python main.py tools run analyze_text "This is sample text"
```

## Command Reference

### Chat Commands

- `python main.py` or `python main.py chat` - Start interactive chat
- `python main.py "Your question here"` - Single query mode
- `python main.py chat --save=session.json` - Save chat history
- `python main.py chat --load=session.json` - Load and continue chat
- `python main.py chat --model=model_name` - Use specific model

### Model Management

- `python main.py model list` - List available models
- `python main.py model use <n>` - Select a model
- `python main.py model info <n>` - Show model details

### Tool Management

- `python main.py tools list` - List available tools
- `python main.py tools run <n> [args]` - Run a tool
- `python main.py tools help <n>` - Show tool help

### Context Management

- `python main.py context list` - List available contexts
- `python main.py context use <n>` - Set active context
- `python main.py context add <n>` - Add content to context

### Configuration

- `python main.py config list` - Show current configuration
- `python main.py config set <key> <value>` - Change configuration setting

Note: The default model is now `gemma3`. You can change it using `python main.py config set model.default <model_name>`.

## Available Tools

TACO comes with several built-in tools:

| Tool | Description |
|------|-------------|
| `analyze_text` | Provides statistics about text (word count, etc.) |
| `calculate_mortgage` | Calculates mortgage payment details |
| `calculate_compound_interest` | Calculates compound interest for investments |
| `convert_temperature` | Converts temperatures between C, F, and K |
| `run_python` | Executes Python code |
| `check_code` | Validates Python code without executing it |

## Working with Pipes

TACO supports Unix-style piping:

```bash
# Analyze text from a file
cat document.txt | python main.py tools run analyze_text

# Add file content to context
cat code.py | python main.py context add code_context
```

## Creating Custom Tools

You can extend TACO with your own custom tools:

1. Create a Python file with your tool functions:
   ```python
   # my_tools.py
   def word_count(text: str) -> dict:
       """Count words in text"""
       words = text.split()
       return {
           "word_count": len(words),
           "unique_words": len(set(words))
       }
   ```

2. Add it to TACO:
   ```bash
   python main.py tools add my_tools.py
   ```

## Creating Context Templates

You can create context templates manually:

1. Create a directory for contexts:
   ```bash
   mkdir -p ~/.config/taco/contexts
   ```

2. Create a JSON file for your context:
   ```bash
   cat > ~/.config/taco/contexts/programming.json << EOF
   {
     "template": "Language: {language}\nStyle: {style}\nDifficulty: {level}",
     "variables": {
       "language": "Python",
       "style": "Clean and efficient",
       "level": "Intermediate"
     }
   }
   EOF
   ```

3. Use the context:
   ```bash
   python main.py context use programming
   python main.py chat
   ```

## In-Chat Commands

While in a chat session, you can use special commands:

- `/help` - Show available commands
- `/model [name]` - Show or switch the current model
- `/clear` - Clear the chat history
- `/tools` - List available tools
- `/context` - Show active context
- `/exit` or `/quit` - Exit the chat session

## Configuration

TACO's configuration is stored in `~/.config/taco/config.json`. You can edit it directly or use the `python main.py config` commands.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

TACO builds upon:
- [Ollama](https://github.com/ollama/ollama) for LLM integration
- [Typer](https://typer.tiangolo.com/) for CLI interface
- [Rich](https://rich.readthedocs.io/) for terminal UI
- [ChromaDB](https://www.trychroma.com/) for vector storage capabilities
- Multiple open-source libraries for terminal UI and tool execution