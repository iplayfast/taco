"""
TACO Basic Tools - Simple utility functions
"""
from typing import Dict, Any, List, Optional
import math

# COMPOUND INTEREST CALCULATOR
def calculate_compound_interest(principal: float, rate: float, time: float, compounds_per_year: int = 12) -> Dict[str, float]:
    """
    Calculate compound interest for an investment
    
    Args:
        principal: Initial investment amount
        rate: Annual interest rate (as a decimal, e.g., 0.05 for 5%)
        time: Investment period in years
        compounds_per_year: Number of times interest is compounded per year
    
    Returns:
        Dict containing final amount and interest earned
    """
    # Convert percentage to decimal if needed
    if rate > 1:
        rate = rate / 100
        
    final_amount = principal * (1 + rate/compounds_per_year)**(compounds_per_year*time)
    interest_earned = final_amount - principal
    
    return {
        "final_amount": round(final_amount, 2),
        "interest_earned": round(interest_earned, 2),
        "input_rate_percent": rate * 100
    }

def _get_calculate_compound_interest_description():
    """Get description for calculate_compound_interest tool"""
    return "calculate_compound_interest: Calculate compound interest for investments"

def _get_calculate_compound_interest_usage():
    """Get usage instructions for calculate_compound_interest tool"""
    return """
Calculate compound interest for investments.

Example:
```json
{
  "tool_call": {
    "name": "calculate_compound_interest",
    "parameters": {
      "principal": 10000,
      "rate": 0.05,
      "time": 10,
      "compounds_per_year": 12
    }
  }
}
```
Note: Rate can be provided as decimal (0.05) or percentage (5).
"""

calculate_compound_interest._get_tool_description = _get_calculate_compound_interest_description
calculate_compound_interest._get_usage_instructions = _get_calculate_compound_interest_usage

# TEXT ANALYZER
def analyze_text(text: str) -> Dict[str, Any]:
    """Analyze text and return statistics"""
    words = text.split()
    return {
        "word_count": len(words),
        "char_count": len(text),
        "avg_word_length": round(sum(len(word) for word in words) / max(len(words), 1), 2),
        "sentence_count": text.count('.') + text.count('!') + text.count('?')
    }

def _get_analyze_text_description():
    """Get description for analyze_text tool"""
    return "analyze_text: Analyze text and return statistics"

def _get_analyze_text_usage():
    """Get usage instructions for analyze_text tool"""
    return """
Analyze text to get word count, character count, and other statistics.

Example:
```json
{
  "tool_call": {
    "name": "analyze_text",
    "parameters": {
      "text": "This is a sample text to analyze."
    }
  }
}
```
"""

analyze_text._get_tool_description = _get_analyze_text_description
analyze_text._get_usage_instructions = _get_analyze_text_usage

# TEMPERATURE CONVERTER
def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert temperature between Celsius, Fahrenheit, and Kelvin
    
    Args:
        value: Temperature value to convert
        from_unit: Source unit (C, F, K, Celsius, Fahrenheit, Kelvin)
        to_unit: Target unit (C, F, K, Celsius, Fahrenheit, Kelvin)
    
    Returns:
        Converted temperature value
    """
    # Normalize units to single letter
    unit_map = {
        'CELSIUS': 'C',
        'FAHRENHEIT': 'F',
        'KELVIN': 'K',
        'C': 'C',
        'F': 'F',
        'K': 'K'
    }
    
    from_unit = unit_map.get(from_unit.upper())
    to_unit = unit_map.get(to_unit.upper())
    
    if not from_unit or not to_unit:
        raise ValueError(f"Invalid temperature unit. Valid units are: Celsius/C, Fahrenheit/F, Kelvin/K")

    conversions = {
        "C_to_F": lambda x: x * 9/5 + 32,
        "F_to_C": lambda x: (x - 32) * 5/9,
        "C_to_K": lambda x: x + 273.15,
        "K_to_C": lambda x: x - 273.15,
        "F_to_K": lambda x: (x - 32) * 5/9 + 273.15,
        "K_to_F": lambda x: (x - 273.15) * 9/5 + 32
    }
    
    key = f"{from_unit}_to_{to_unit}"
    if key not in conversions:
        if from_unit == to_unit:
            return round(value, 2)
        raise ValueError(f"Unsupported conversion: {from_unit} to {to_unit}")
        
    return round(conversions[key](value), 2)

def _get_convert_temperature_description():
    """Get description for convert_temperature tool"""
    return "convert_temperature: Convert temperature between Celsius, Fahrenheit, and Kelvin"

def _get_convert_temperature_usage():
    """Get usage instructions for convert_temperature tool"""
    return """
Convert temperature between different units.

Example:
```json
{
  "tool_call": {
    "name": "convert_temperature",
    "parameters": {
      "value": 32,
      "from_unit": "F",
      "to_unit": "C"
    }
  }
}
```
Units: C/Celsius, F/Fahrenheit, K/Kelvin
"""

convert_temperature._get_tool_description = _get_convert_temperature_description
convert_temperature._get_usage_instructions = _get_convert_temperature_usage

# MORTGAGE CALCULATOR
def calculate_mortgage(principal: float, annual_rate: float, years: int) -> Dict[str, float]:
    """
    Calculate mortgage payment details
    
    Args:
        principal: Loan amount in dollars
        annual_rate: Annual interest rate (as a percentage, e.g., 3.5 for 3.5%)
        years: Loan term in years
    
    Returns:
        Dict containing monthly payment, total payment, and total interest
    """
    # Convert annual rate from percentage to decimal
    annual_rate = annual_rate / 100
    
    # Convert to monthly rate
    monthly_rate = annual_rate / 12
    num_payments = years * 12
    
    # Handle edge case when rate is 0
    if monthly_rate == 0:
        monthly_payment = principal / num_payments
    else:
        # Standard mortgage payment formula
        monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    
    total_payment = monthly_payment * num_payments
    total_interest = total_payment - principal
    
    return {
        "monthly_payment": round(monthly_payment, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2)
    }

def _get_calculate_mortgage_description():
    """Get description for calculate_mortgage tool"""
    return "calculate_mortgage: Calculate monthly mortgage payments and total costs"

def _get_calculate_mortgage_usage():
    """Get usage instructions for calculate_mortgage tool"""
    return """
Calculate mortgage payments and total costs.

Example:
```json
{
  "tool_call": {
    "name": "calculate_mortgage",
    "parameters": {
      "principal": 300000,
      "annual_rate": 3.5,
      "years": 30
    }
  }
}
```
Note: Annual rate should be provided as a percentage (e.g., 3.5 for 3.5%).
"""

calculate_mortgage._get_tool_description = _get_calculate_mortgage_description
calculate_mortgage._get_usage_instructions = _get_calculate_mortgage_usage