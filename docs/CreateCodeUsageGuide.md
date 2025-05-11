# Create Code Tool Usage Guide

## Overview

The `create_code` tool generates code based on natural language prompts. It uses default configurations from your TACO config file and requires confirmation before proceeding.

## Configuration

Default values are stored in `~/.config/taco/config.json`:
```json
{
  "tools": {
    "create_code": {
      "workingdir": "~/code_projects",
      "requirements": "requirements.txt",
      "model": "llama3"
    }
  }
}
```

## Installation

The `create_code` tool is located in `taco/tools/builtin/create_code.py` and is automatically loaded when TACO starts.

## Usage Examples

### Using the CLI `create` command (recommended):

```bash
# Basic usage - will prompt for confirmation
python main.py create "Create a snake game using pygame"

# Skip confirmation with --yes flag
python main.py create "Create a snake game using pygame" --yes

# Override specific defaults
python main.py create "Create a web scraper" --workingdir ~/scrapers --model codellama

# Full custom configuration
python main.py create "Create a REST API with FastAPI" \
  --workingdir ~/api_project \
  --requirements api_requirements.txt \
  --model llama3 \
  --yes
```

### Using the tool directly through `tools run`:

```bash
# Show configuration and cancel (isok=N)
python main.py tools run create_code "Create a snake game" "" "" "" "N"

# Proceed with defaults (isok=Y)
python main.py tools run create_code "Create a snake game" "" "" "" "Y"

# Custom configuration
python main.py tools run create_code "Create a web app" "~/webapps" "web_requirements.txt" "codellama" "Y"
```

### Using in chat mode:

```
/tools run create_code "Create a calculator app" "" "" "" "Y"
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `prompt` | Your code generation request | Required |
| `workingdir` | Directory for generated files | `~/code_projects` |
| `requirements` | Name for requirements file | `requirements.txt` |
| `model` | LLM model to use | `llama3` |
| `isok` | Confirmation flag ('Y' to proceed) | `N` |

## Workflow

1. Tool shows you the configuration it will use
2. If `isok` is not 'Y', it asks for confirmation
3. Creates the working directory if needed
4. Generates code using the specified model
5. Saves output as:
   - `generated_code.md` - Full response with explanations
   - Individual code files extracted from code blocks
   - `requirements.txt` if dependencies are needed

## Example Output

After successful generation:
```
Code generated successfully in /home/user/code_projects

Generated files:
  • generated_code.md
  • code_1.py
  • requirements.txt
```

## Tips

1. Always review the configuration before confirming
2. Use descriptive prompts for better results
3. Check the generated `requirements.txt` for dependencies
4. The full response in `generated_code.md` includes explanations and usage instructions

## Directory Structure

The tool is part of the builtin tools in:
```
taco/
├── tools/
│   ├── builtin/
│   │   ├── basic.py
│   │   ├── code.py
│   │   ├── create_code.py  # This tool
│   │   └── __init__.py
```