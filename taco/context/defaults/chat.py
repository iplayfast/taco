"""
TACO Chat Context Templates
"""
from typing import Dict

# Chat context template
CHAT_TEMPLATE = """
You are having a conversation with a human user. Respond in a {style} tone.
Current conversation topic: {topic}
User information: {user_info}
"""

# Default variables
CHAT_VARIABLES = {
    "style": "helpful and friendly",
    "topic": "general conversation",
    "user_info": "No specific information provided"
}

# Coding assistant template
CODE_TEMPLATE = """
You are a coding assistant helping with {language} programming.
Expertise level: {expertise}
Programming style: {style}
Include explanations: {explanations}
"""

# Default code variables
CODE_VARIABLES = {
    "language": "Python",
    "expertise": "intermediate",
    "style": "clean and readable",
    "explanations": "yes"
}

def get_default_chat_context() -> Dict[str, Dict[str, str]]:
    """Get default context templates for chat"""
    return {
        "general_chat": {
            "template": CHAT_TEMPLATE,
            "variables": CHAT_VARIABLES
        },
        "code_assistant": {
            "template": CODE_TEMPLATE,
            "variables": CODE_VARIABLES
        }
    }
