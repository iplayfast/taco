#!/usr/bin/env python3
"""
Test script to demonstrate automatic tool calling with TACO
"""
from taco.core.chat import ChatSession

def main():
    print("TACO Automatic Tool Calling Test")
    print("================================")
    print()
    
    # Create a chat session
    chat = ChatSession()
    
    # Test questions that should trigger tool usage
    test_questions = [
        "Can you calculate a mortgage for me?",
        "What's 100 degrees Fahrenheit in Celsius?",
        "Calculate compound interest on $10,000 at 5% for 10 years",
        "Analyze this text: The quick brown fox jumps over the lazy dog."
    ]
    
    for question in test_questions:
        print(f"\n[You]: {question}")
        response = chat.ask(question)
        print(f"[Assistant]: {response}")
        print("-" * 50)

if __name__ == "__main__":
    main()