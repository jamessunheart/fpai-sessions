#!/usr/bin/env python3
"""
Calculator Module
==================

A safe calculator that evaluates math expressions using ast.
Examples: /calc 5+3, /calc 100*0.15, /calc (50+30)/2
"""

import ast
import operator
import math

# Supported operators
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe functions
FUNCTIONS = {
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log,
    'log10': math.log10,
}

# Constants
CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
}


def ast_calculate(node):
    """Safely calculate an AST node using only safe operations."""
    if isinstance(node, ast.Constant):  # Numbers
        return node.value
    elif isinstance(node, ast.Num):  # Legacy numbers (Python 3.7)
        return node.n
    elif isinstance(node, ast.BinOp):  # Binary operations
        op = OPERATORS.get(type(node.op))
        if op:
            left = ast_calculate(node.left)
            right = ast_calculate(node.right)
            return op(left, right)
        raise ValueError(f"Unsupported operator: {type(node.op)}")
    elif isinstance(node, ast.UnaryOp):  # Unary operations
        op = OPERATORS.get(type(node.op))
        if op:
            return op(ast_calculate(node.operand))
        raise ValueError(f"Unsupported unary operator: {type(node.op)}")
    elif isinstance(node, ast.Call):  # Function calls
        func_name = node.func.id if isinstance(node.func, ast.Name) else None
        if func_name in FUNCTIONS:
            args = [ast_calculate(arg) for arg in node.args]
            return FUNCTIONS[func_name](*args)
        raise ValueError(f"Unknown function: {func_name}")
    elif isinstance(node, ast.Name):  # Variables (constants)
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise ValueError(f"Unknown constant: {node.id}")
    elif isinstance(node, ast.Expression):
        return ast_calculate(node.body)
    else:
        raise ValueError(f"Unsupported expression type: {type(node)}")


def calculate(expression: str) -> float:
    """Parse and calculate a math expression safely."""
    try:
        tree = ast.parse(expression, mode='eval')
        return ast_calculate(tree)
    except SyntaxError as e:
        raise ValueError(f"Invalid expression: {e}")


def handle(args: str, context: dict) -> str:
    """
    Handle the /calc command.
    
    Args:
        args: Math expression to evaluate
        context: Command context
    
    Returns:
        Calculation result or error message
    """
    if not args.strip():
        return (
            "🧮 **Calculator**\n\n"
            "Usage: `/calc <expression>`\n\n"
            "Examples:\n"
            "• `/calc 5 + 3 * 2` → 11\n"
            "• `/calc 100 * 0.15` → 15.0\n"
            "• `/calc sqrt(16)` → 4.0\n"
            "• `/calc (50 + 30) / 2` → 40.0\n\n"
            "Available: `sqrt`, `sin`, `cos`, `tan`, `log`, `pi`, `e`"
        )
    
    expression = args.strip()
    
    try:
        result = calculate(expression)
        
        # Format result nicely
        if isinstance(result, float):
            if result == int(result):
                result = int(result)
            else:
                result = round(result, 6)
        
        return f"🧮 `{expression}` = **{result}**"
        
    except ZeroDivisionError:
        return "❌ Division by zero!"
    except ValueError as e:
        return f"❌ {str(e)[:50]}"
    except Exception as e:
        return f"❌ Calculation error: {str(e)[:50]}"
