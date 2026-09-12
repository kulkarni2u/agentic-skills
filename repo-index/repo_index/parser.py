"""AST-based code parser for indexing methods, constants, and variables."""

import ast
from typing import Dict, List, Any


def parse_source(code: str) -> ast.AST:
    """Parse source code and return the AST."""
    return ast.parse(code)


def extract_nodes(tree: ast.AST, source: str) -> Dict[str, List[Dict[str, Any]]]:
    """Extract methods, constants, and variables from the AST."""
    methods = []
    constants = []
    variables = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            methods.append({
                "name": node.name,
                "lineno": node.lineno,
                "col_offset": node.col_offset,
                "end_lineno": node.end_lineno,
                "end_col_offset": node.end_col_offset,
            })
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    constants.append({
                        "name": target.id,
                        "lineno": target.lineno,
                        "col_offset": target.col_offset if hasattr(target, 'col_offset') else 0,
                    })

    return {
        "methods": methods,
        "constants": constants,
        "variables": variables,
    }
