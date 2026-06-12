#!/usr/bin/env python3
"""
MODULE TEMPLATES
================

Templates for scaffolding new modules.
"""

import json
from datetime import datetime


class ModuleTemplates:
    """Templates for creating new modules."""
    
    @staticmethod
    def module_json(
        module_name: str,
        command: str,
        description: str,
        author: str,
        version: str = "1.0.0"
    ) -> str:
        """Generate module.json content."""
        data = {
            "name": module_name,
            "version": version,
            "description": description,
            "author": author,
            "command": command,
            "type": "telegram_command",
            "entry": "handler.py",
            "created": datetime.now().isoformat()
        }
        return json.dumps(data, indent=2)
    
    @staticmethod
    def handler_py(
        command: str,
        description: str,
        initial_logic: str = None
    ) -> str:
        """Generate handler.py content."""
        
        # Default handler if no logic provided
        if not initial_logic:
            initial_logic = '''    if not args.strip():
        return f"Usage: {command} <your input here>"
    
    # TODO: Implement your logic here
    return f"You said: {args}"'''
        
        template = f'''#!/usr/bin/env python3
"""
{command.upper()} Command
{'=' * (len(command) + 8)}

{description}
"""


def handle(args: str, context: dict) -> str:
    """
    Handle the {command} command.
    
    Args:
        args: Command arguments (everything after the command)
        context: Contains user_id, chat_id, and other metadata
    
    Returns:
        Response string to send back to the user
    """
{initial_logic}
'''
        return template
    
    @staticmethod
    def readme_md(
        module_name: str,
        command: str,
        description: str,
        author: str,
        examples: list = None
    ) -> str:
        """Generate README.md content."""
        
        examples_text = ""
        if examples:
            examples_text = "\n## Examples\n\n"
            for ex in examples:
                examples_text += f"```\n{ex}\n```\n\n"
        else:
            examples_text = f"""
## Examples

```
{command}
{command} hello world
```
"""
        
        template = f'''# {module_name.replace("-", " ").title()}

{description}

## Usage

```
{command} <arguments>
```
{examples_text}
## Author

Built by {author}

## Version

1.0.0
'''
        return template
    
    @staticmethod
    def simple_echo_handler(command: str) -> str:
        """A simple echo handler for testing."""
        return f'''    # Simple echo - replace with your logic
    if not args.strip():
        return "Please provide some text after the command."
    
    return f"Echo: {{args}}"'''
    
    @staticmethod
    def data_storage_handler(command: str, data_type: str = "entries") -> str:
        """Handler template for storing/retrieving data."""
        return f'''    import json
    from pathlib import Path
    from datetime import datetime
    
    # Data storage path (in user's sandbox)
    user_id = context.get("user_id", 0)
    data_file = Path(f"/opt/fpai/data/{command.strip('/')}/user_{{user_id}}.json")
    data_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_data():
        if data_file.exists():
            try:
                return json.loads(data_file.read_text())
            except:
                return []
        return []
    
    def save_data(data):
        data_file.write_text(json.dumps(data, indent=2))
    
    # No args - show stored {data_type}
    if not args.strip():
        {data_type} = load_data()
        if not {data_type}:
            return "No {data_type} stored yet. Add one with: {command} <text>"
        
        lines = []
        for entry in {data_type}[-10:]:  # Last 10
            lines.append(f"- {{entry.get('text', '')}} ({{entry.get('date', '')}})")
        
        return "Your {data_type}:\\n" + "\\n".join(lines)
    
    # Add new entry
    {data_type} = load_data()
    {data_type}.append({{
        "text": args.strip(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "timestamp": datetime.now().isoformat()
    }})
    save_data({data_type})
    
    return f"Saved: {{args.strip()}}\\n\\nTotal {data_type}: {{len({data_type})}}"'''
    
    @staticmethod
    def api_fetch_handler(command: str, api_description: str = "data") -> str:
        """Handler template for fetching from APIs."""
        return f'''    # API fetch handler
    # Note: For network access, use approved HTTP clients only
    
    if not args.strip():
        return "Usage: {command} <query>"
    
    query = args.strip()
    
    try:
        # TODO: Replace with actual API call
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"https://api.example.com/{{query}}") as resp:
        #         data = await resp.json()
        
        # Placeholder response
        return f"Fetching {api_description} for: {{query}}\\n\\n[API integration pending]"
        
    except Exception as e:
        return f"Error fetching {api_description}: {{str(e)[:50]}}"'''
    
    @staticmethod
    def calculator_handler(command: str) -> str:
        """Handler template for safe calculations."""
        return '''    import ast
    import operator
    import math
    
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    FUNCTIONS = {
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'abs': abs,
        'round': round,
    }
    
    CONSTANTS = {'pi': math.pi, 'e': math.e}
    
    def calc_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return OPERATORS[type(node.op)](calc_node(node.left), calc_node(node.right))
        elif isinstance(node, ast.UnaryOp):
            return OPERATORS[type(node.op)](calc_node(node.operand))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FUNCTIONS:
                return FUNCTIONS[node.func.id](*[calc_node(a) for a in node.args])
        elif isinstance(node, ast.Name) and node.id in CONSTANTS:
            return CONSTANTS[node.id]
        elif isinstance(node, ast.Expression):
            return calc_node(node.body)
        raise ValueError(f"Unsupported: {type(node)}")
    
    if not args.strip():
        return "Usage: ''' + command + ''' <expression>\\n\\nExamples: 5+3*2, sqrt(16), pi*2"
    
    try:
        tree = ast.parse(args.strip(), mode="eval")
        result = calc_node(tree)
        if isinstance(result, float) and result == int(result):
            result = int(result)
        return f"{args.strip()} = {result}"
    except Exception as e:
        return f"Error: {str(e)[:50]}"'''
    
    @staticmethod
    def random_choice_handler(command: str, items_name: str = "items") -> str:
        """Handler template for random selection from a list."""
        return f'''    import random
    
    # Define your {items_name} here
    {items_name.upper()} = [
        "Item 1",
        "Item 2", 
        "Item 3",
        "Item 4",
        "Item 5",
    ]
    
    if args.strip().lower() == "list":
        return "Available {items_name}:\\n" + "\\n".join(f"- {{item}}" for item in {items_name.upper()})
    
    choice = random.choice({items_name.upper()})
    return f"{{choice}}"'''


