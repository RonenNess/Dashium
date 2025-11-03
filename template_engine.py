"""
Simple HTML Template Engine.
Author: Ronen Ness.
Created: 2025.
"""
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import logger

log = logger.get_logger("templates")


class ITemplateEngine:
    """
    Interface for a template engine.
    """

    def render_template(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render a template with the given context
        
        Args:
            template_name (str): Name of the template file
            context (Optional[Dict[str, Any]]): Variables to replace in the template
            
        Returns:
            str: Rendered HTML content
        """
        raise NotImplementedError("render_template must be implemented by subclasses")


class SimpleTemplateEngine (ITemplateEngine):
    """
    A simple template engine that supports:
    1. Variable replacement: {{variable_name}}
    2. Dictionary/attribute access: {{x.something}}
    3. For loops: {% for x in items %}...{% endfor %}
    4. If/else conditionals: {% if var %}...{% else %}...{% endif %}
    5. Template inheritance: {% extends "base.html" %} with {% block name %}...{% endblock %}
    6. Unlimited extension chains: A extends B extends C extends D...
    7. Block inheritance: derived templates inherit blocks from base if not overridden
    """
    
    def __init__(self, template_dir: Union[str, Path]) -> None:
        """
        Initialize the template engine.
        
        Args:
            template_dir (Union[str, Path]): Directory containing template files
            
        Returns:
            None
        """
        self.template_dir = Path(template_dir)
        # Patterns for template processing
        self.variable_pattern = re.compile(r'\{\{\s*([\w\.]+)(?:\s*\|\s*([^}]+))?\s*\}\}')
        self.extends_pattern = re.compile(r'\{\%\s*extends\s+["\']([^"\']+)["\']\s*\%\}')
        self.block_pattern = re.compile(r'\{\%\s*block\s+(\w+)\s*\%\}(.*?)\{\%\s*endblock\s*\%\}', re.DOTALL)
        self.for_pattern = re.compile(r'\{\%\s*for\s+(\w+)\s+in\s+(\w+)\s*\%\}(.*?)\{\%\s*endfor\s*\%\}', re.DOTALL)
        self.if_pattern = re.compile(r'\{\%\s*if\s+(.+?)\s*\%\}(.*?)(?:\{\%\s*else\s*\%\}(.*?))?\{\%\s*endif\s*\%\}', re.DOTALL)
    
    def render_template(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render a template with the given context
        
        Args:
            template_name (str): Name of the template file
            context (Optional[Dict[str, Any]]): Variables to replace in the template
            
        Returns:
            str: Rendered HTML content
        """
        if context is None:
            context = {}
        
        try:
            # Build the complete inheritance chain
            inheritance_chain = self._build_inheritance_chain(template_name)
            log.debug(f"Inheritance chain: {' -> '.join(inheritance_chain)}")
            
            # Collect all blocks from the entire chain
            all_blocks = self._collect_blocks_from_chain(inheritance_chain)
            log.debug(f"Final blocks available: {list(all_blocks.keys())}")
            
            # Get the root template (last in chain)
            root_template = inheritance_chain[-1]
            root_content = self._load_template(root_template)
            
            # Apply all blocks to the root template
            final_content = self._apply_blocks(root_content, all_blocks)
            
            # Process for loops first (which will process their own if statements and variables)
            final_content = self._process_for_loops(final_content, context)
            
            # Process if/else conditionals (for conditions outside of loops)
            final_content = self._process_if_statements(final_content, context)
            
            # Process variables (for variables outside of loops)
            final_content = self._process_variables(final_content, context)
            
            return final_content
            
        except Exception as e:
            log.error(f"Error rendering template {template_name}: {e}")
            return f"<h1>Template Error</h1><p>Error rendering template: {str(e)}</p>"
    
    def _build_inheritance_chain(self, template_name: str) -> List[str]:
        """
        Build the complete inheritance chain from child to root
        
        Args:
            template_name (str): Name of the starting template
            
        Returns:
            List[str]: List of template names [child, parent, grandparent, ..., root]
        """
        chain = []
        current_template = template_name
        visited = set()
        
        while current_template:
            # Check for circular inheritance
            if current_template in visited:
                raise Exception(f"Circular inheritance detected: {current_template}")
            
            visited.add(current_template)
            chain.append(current_template)
            
            # Load template and check if it extends another
            content = self._load_template(current_template)
            extends_match = self.extends_pattern.search(content)
            
            if extends_match:
                current_template = extends_match.group(1)
            else:
                current_template = None
        
        return chain
    
    def _collect_blocks_from_chain(self, inheritance_chain: List[str]) -> Dict[str, str]:
        """
        Collect blocks from the entire inheritance chain
        Child blocks override parent blocks
        
        Args:
            inheritance_chain (List[str]): List of template names in inheritance order
            
        Returns:
            Dict[str, str]: Dictionary mapping block names to their content
        """
        all_blocks = {}
        
        # Process from root to child (reverse order)
        # This ensures child blocks override parent blocks
        for template_name in reversed(inheritance_chain):
            content = self._load_template(template_name)
            
            # Remove extends directive to get clean content
            clean_content = self.extends_pattern.sub('', content)
            
            # Extract blocks from this template
            template_blocks = self._extract_blocks(clean_content)
            log.debug(f"Template {template_name} has blocks: {list(template_blocks.keys())}")
            
            # Update all_blocks (later templates override earlier ones)
            all_blocks.update(template_blocks)
        
        return all_blocks
    
    def _extract_blocks(self, content: str) -> Dict[str, str]:
        """
        Extract all blocks from template content
        
        Args:
            content (str): Template content to extract blocks from
            
        Returns:
            Dict[str, str]: Dictionary mapping block names to their content
        """
        blocks = {}
        matches = self.block_pattern.findall(content)
        
        for block_name, block_content in matches:
            blocks[block_name] = block_content.strip()
        
        return blocks
    
    def _apply_blocks(self, root_content: str, blocks: Dict[str, str]) -> str:
        """
        Apply all collected blocks to the root template
        
        Args:
            root_content (str): Content of the root template
            blocks (Dict[str, str]): Dictionary of block names to their content
            
        Returns:
            str: Template content with blocks applied
        """
        def replace_block(match: re.Match[str]) -> str:
            block_name = match.group(1)
            default_content = match.group(2) if len(match.groups()) > 1 else ""
            
            # Use collected block if available, otherwise use default
            if block_name in blocks:
                log.debug(f"Applying block '{block_name}'")
                return blocks[block_name]
            else:
                log.debug(f"Using default content for block '{block_name}'")
                return default_content.strip()
        
        return self.block_pattern.sub(replace_block, root_content)
    
    def _load_template(self, template_name: str) -> str:
        """
        Load template content from file
        
        Args:
            template_name (str): Name of the template file to load
            
        Returns:
            str: Content of the template file
        """
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            raise Exception(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _process_if_statements(self, content: str, context: Dict[str, Any]) -> str:
        """
        Process {% if var %}...{% else %}...{% endif %} conditionals with support for nested conditions
        Supports both simple truthiness checks and comparison operations
        
        Args:
            content (str): Template content to process
            context (Dict[str, Any]): Variables available for evaluation
            
        Returns:
            str: Content with if statements processed
        """
        # Process nested if statements from innermost to outermost
        while True:
            # Find the next if statement to process
            if_match = self._find_next_if_statement(content)
            if not if_match:
                break
            
            start, end, condition, if_content, else_content = if_match
            
            log.debug(f"Processing if statement: '{condition}' with context keys: {list(context.keys())}")
            
            try:
                # Evaluate the condition
                comparison_result = self._evaluate_condition(condition, context)
                
                log.debug(f"Condition '{condition}' evaluated to: {comparison_result}")
                
                if comparison_result:
                    replacement = if_content
                else:
                    replacement = else_content
                
                # Replace this if statement with the result
                content = content[:start] + replacement + content[end:]
                    
            except Exception as e:
                log.warning(f"Error evaluating if condition '{condition}': {e}")
                # Replace with else content on error
                content = content[:start] + else_content + content[end:]
        
        return content
    
    def _find_next_if_statement(self, content: str) -> Optional[tuple]:
        """
        Find the next (innermost) if statement that has no nested if statements
        
        Args:
            content (str): Content to search in
            
        Returns:
            Optional[tuple]: (start, end, condition, if_content, else_content) or None if no if found
        """
        # Pattern to find if statements
        if_start_pattern = re.compile(r'\{\%\s*if\s+(.+?)\s*\%\}')
        else_pattern = re.compile(r'\{\%\s*else\s*\%\}')
        endif_pattern = re.compile(r'\{\%\s*endif\s*\%\}')
        
        # Find all if statements
        if_matches = list(if_start_pattern.finditer(content))
        if not if_matches:
            return None
        
        # For each if statement, find its matching endif
        for if_match in if_matches:
            if_start = if_match.start()
            condition = if_match.group(1).strip()
            
            # Find the matching endif by counting nested if/endif pairs
            pos = if_match.end()
            if_count = 1  # We found one if
            else_pos = None
            
            while pos < len(content) and if_count > 0:
                # Look for the next if, else, or endif
                next_if = if_start_pattern.search(content, pos)
                next_else = else_pattern.search(content, pos) if else_pos is None else None
                next_endif = endif_pattern.search(content, pos)
                
                # Find which comes first
                candidates = []
                if next_if:
                    candidates.append(('if', next_if.start(), next_if.end()))
                if next_else and if_count == 1:  # Only consider else for our current if level
                    candidates.append(('else', next_else.start(), next_else.end()))
                if next_endif:
                    candidates.append(('endif', next_endif.start(), next_endif.end()))
                
                if not candidates:
                    break  # No more matches found
                
                # Sort by position and take the first
                candidates.sort(key=lambda x: x[1])
                tag_type, tag_start, tag_end = candidates[0]
                
                if tag_type == 'if':
                    if_count += 1
                elif tag_type == 'else' and if_count == 1:
                    else_pos = tag_start
                elif tag_type == 'endif':
                    if_count -= 1
                    if if_count == 0:
                        # Found the matching endif
                        endif_start = tag_start
                        endif_end = tag_end
                        
                        # Check if this if statement has any nested if statements
                        if_content_start = if_match.end()
                        if_content_end = else_pos if else_pos else endif_start
                        if_content = content[if_content_start:if_content_end]
                        
                        else_content = ""
                        if else_pos:
                            else_content = content[else_pos + len("{% else %}"):endif_start]
                        
                        # Check if the if_content or else_content contains nested if statements
                        if (if_start_pattern.search(if_content) is None and 
                            if_start_pattern.search(else_content) is None):
                            # No nested if statements, we can process this one
                            return (if_start, endif_end, condition, if_content, else_content)
                
                pos = tag_end
        
        return None
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition expression (supports ==, !=, and truthiness)
        
        Args:
            condition (str): The condition to evaluate (e.g., 'widget.type == "line_graph"')
            context (Dict[str, Any]): Variables available for evaluation
            
        Returns:
            bool: Result of the condition evaluation
        """
        # Check for comparison operators
        if ' == ' in condition:
            left, right = condition.split(' == ', 1)
            left_value = self._get_variable_value(left.strip(), context)
            right_value = self._parse_literal_or_variable(right.strip(), context)
            log.debug(f"Comparison: '{left.strip()}' = {left_value} ({type(left_value)}) == '{right.strip()}' = {right_value} ({type(right_value)}) = {left_value == right_value}")
            return left_value == right_value
        elif ' != ' in condition:
            left, right = condition.split(' != ', 1)
            left_value = self._get_variable_value(left.strip(), context)
            right_value = self._parse_literal_or_variable(right.strip(), context)
            return left_value != right_value
        else:
            # Simple truthiness check
            return bool(self._get_variable_value(condition.strip(), context))
    
    def _get_variable_value(self, variable_path: str, context: Dict[str, Any]) -> Any:
        """
        Get the value of a variable from the context using dot notation
        
        Args:
            variable_path (str): The variable path (e.g., 'widget.type')
            context (Dict[str, Any]): Variables available for evaluation
            
        Returns:
            Any: The variable value or None if not found
        """
        parts = variable_path.split('.')
        
        # Try to get the root variable
        if parts[0] not in context:
            return None
        
        value = context[parts[0]]
        
        # Navigate through the path
        try:
            for part in parts[1:]:
                # Try attribute access first
                if hasattr(value, part):
                    value = getattr(value, part)
                # Then try dictionary access
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    # Path not found
                    return None
            
            return value
            
        except Exception as e:
            log.warning(f"Error accessing variable path '{variable_path}': {e}")
            return None
    
    def _parse_literal_or_variable(self, value_str: str, context: Dict[str, Any]) -> Any:
        """
        Parse a value that could be a string literal, number, or variable reference
        
        Args:
            value_str (str): The value string to parse
            context (Dict[str, Any]): Variables available for evaluation
            
        Returns:
            Any: The parsed value
        """
        value_str = value_str.strip()
        
        # Check if it's a quoted string literal
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]  # Remove quotes
        
        # Check if it's a number
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
        
        # Check if it's a boolean
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        
        # Assume it's a variable reference
        return self._get_variable_value(value_str, context)
    
    def _process_for_loops(self, content: str, context: Dict[str, Any]) -> str:
        """
        Process {% for x in items %}...{% endfor %} loops
        
        Args:
            content (str): Template content to process
            context (Dict[str, Any]): Variables available for iteration
            
        Returns:
            str: Content with for loops processed
        """
        def replace_for_loop(match: re.Match[str]) -> str:
            loop_var = match.group(1)  # e.g., 'x'
            iterable_name = match.group(2)  # e.g., 'var_name'
            loop_content = match.group(3)  # content inside the loop
            
            # Get the iterable from context
            if iterable_name not in context:
                log.warning(f"Iterable '{iterable_name}' not found in context")
                return ""
            
            iterable = context[iterable_name]
            
            # Check if it's actually iterable
            if not hasattr(iterable, '__iter__') or isinstance(iterable, str):
                log.warning(f"Variable '{iterable_name}' is not iterable")
                return ""
            
            # Render loop content for each item
            result = []
            for index, item in enumerate(iterable):
                # Create a new context with the loop variable and loop metadata
                loop_context = context.copy()
                loop_context[loop_var] = item
                
                # Add loop metadata object
                class LoopInfo:
                    def __init__(self, index: int):
                        self.index = index
                        self.index0 = index  # 0-based index alias
                        self.index1 = index + 1  # 1-based index
                
                loop_context['loop'] = LoopInfo(index)
                
                log.debug(f"Processing loop iteration {index} with {loop_var}={item}")
                log.debug(f"Loop context keys: {list(loop_context.keys())}")
                
                # Process if statements in this iteration (with loop context)
                rendered_iteration = self._process_if_statements(loop_content, loop_context)
                
                # Process variables in this iteration
                rendered_iteration = self._process_variables(rendered_iteration, loop_context)
                result.append(rendered_iteration)
            
            return ''.join(result)
        
        return self.for_pattern.sub(replace_for_loop, content)
    
    def _process_variables(self, content: str, context: Dict[str, Any]) -> str:
        """
        Replace {{variable_name}} or {{obj.attr}} with values from context
        
        Args:
            content (str): Template content to process
            context (Dict[str, Any]): Variables available for replacement
            
        Returns:
            str: Content with variables replaced
        """
        def replace_variable(match: re.Match[str]) -> str:
            variable_path = match.group(1)  # e.g., 'x' or 'x.something'
            default_value = match.group(2).strip() if match.group(2) else None  # e.g., '5' from '| 5'
            
            # Split by dots to handle nested access
            parts = variable_path.split('.')
            
            # Get the root variable
            if parts[0] not in context:
                if default_value is not None:
                    return default_value
                log.warning(f"Variable '{parts[0]}' not found in context")
                return f"{{{{ {variable_path} }}}}"  # Leave unreplaced
            
            value = context[parts[0]]
            
            # Navigate through the path
            try:
                for part in parts[1:]:
                    # Try attribute access first
                    if hasattr(value, part):
                        value = getattr(value, part)
                    # Then try dictionary access
                    elif isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        if default_value is not None:
                            return default_value
                        log.warning(f"Cannot access '{part}' in '{'.'.join(parts[:parts.index(part)])}'")
                        return f"{{{{ {variable_path} }}}}"
                
                # Handle None values as empty strings
                if value is None:
                    return ''
                
                # Convert Python booleans to JavaScript booleans
                if isinstance(value, bool):
                    return 'true' if value else 'false'
                
                # other values - return as string
                return str(value)
            
            except Exception as e:
                if default_value is not None:
                    return default_value
                log.warning(f"Error accessing '{variable_path}': {e}")
                return f"{{{{ {variable_path} }}}}"
        
        return self.variable_pattern.sub(replace_variable, content)


def create_template_engine(template_dir: Union[str, Path]) -> ITemplateEngine:
    """
    Factory function to create a template engine
    
    Args:
        template_dir (Union[str, Path]): Directory containing template files
        
    Returns:
        ITemplateEngine: Template engine instance
    """
    return SimpleTemplateEngine(template_dir)