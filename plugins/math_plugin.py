from typing import Optional, Dict, Any
from plugins.base import FastCommandPlugin

class MathPlugin(FastCommandPlugin):
    def handle(self, text: str) -> Optional[Dict[str, Any]]:
        if text.startswith("what is ") or text.startswith("calculate "):
            try:
                expression = text.replace("what is", "").replace("calculate", "").strip()
                
                # STT engines often transcribe math operators as words
                replacements = {
                    "plus": "+",
                    "minus": "-",
                    "times": "*",
                    "multiplied by": "*",
                    "divided by": "/",
                    "over": "/",
                    "x": "*",
                    "to the power of": "**",
                    "squared": "** 2",
                    "cubed": "** 3",
                    "percent of": "/ 100 *"
                }
                
                for word, op in replacements.items():
                    expression = expression.replace(word, op)
                    
                # Clean up any random words STT might add
                # Allow numbers, operators, decimals, spaces, parenthesis
                import re
                cleaned_expr = re.sub(r'[^0-9\+\-\*\/\(\)\.\s]', '', expression)
                
                if cleaned_expr.strip():
                    # Basic safe math evaluation
                    result = eval(cleaned_expr, {"__builtins__": None}, {})
                    
                    # Formatting the result
                    if isinstance(result, float):
                        result = round(result, 4)
                        if result.is_integer():
                            result = int(result)
                            
                    return {"action": "reply", "reply": f"The answer is {result}."}
            except Exception as e:
                pass
        return None
