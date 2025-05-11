"""
TACO Basic Tools - Simple utility functions
"""
from typing import Dict, Any, List, Optional
import math

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

def analyze_text(text: str) -> Dict[str, Any]:
    """Analyze text and return statistics"""
    words = text.split()
    return {
        "word_count": len(words),
        "char_count": len(text),
        "avg_word_length": round(sum(len(word) for word in words) / max(len(words), 1), 2),
        "sentence_count": text.count('.') + text.count('!') + text.count('?')
    }

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

# Add custom description
def _get_tool_description():
    """Custom description for calculate_mortgage tool"""
    return """calculate_mortgage: Calculate monthly mortgage payments and total costs
    
Parameters:
- principal (number): Loan amount in dollars [REQUIRED]
- annual_rate (number): Annual interest rate as a percentage (e.g., 3.5 for 3.5%) [REQUIRED]
- years (number): Loan term in years [REQUIRED]
"""

def _get_usage_instructions():
    """Custom usage instructions for calculate_mortgage tool"""
    return """
Example usage:
1. If user provides all parameters: "Calculate mortgage for $300,000 at 3.5% for 30 years"
   Call directly with the provided values.

2. If parameters are missing: "Can you calculate a mortgage for me?"
   Use collect_tool_parameters first to gather the required information.
"""

calculate_mortgage._get_tool_description = _get_tool_description
calculate_mortgage._get_usage_instructions = _get_usage_instructions