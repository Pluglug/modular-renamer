"""
命名パターン定義と名前構築処理
旧 NamingProcessor
"""

from typing import List, Dict, Optional
from .elements import INameElement


class NamingPattern:
    """
    Represents a naming pattern that contains multiple elements to build names
    """

    def __init__(
        self, name: str, target_type: str, elements_config: List[Dict], element_registry
    ):
        """
        Initialize a naming pattern

        Args:
            name: Name of the pattern
            target_type: Type of target this pattern is for (object, bone, material, etc.)
            elements_config: List of configurations for each element
            element_registry: ElementRegistry to create elements
        """
        self.name = name
        self.target_type = target_type
        self.elements: List[INameElement] = []

        self._load_elements(elements_config, element_registry)

    def _load_elements(self, elements_config: List[Dict], element_registry):
        """
        Load elements from configuration

        Args:
            elements_config: List of element configurations
            element_registry: ElementRegistry to create elements
        """
        for config in elements_config:
            try:
                element_type = config["type"]
                element = element_registry.create_element(element_type, config)
                self.elements.append(element)
            except (KeyError, TypeError) as e:
                print(f"Error loading element: {e}")

        # Sort elements by order
        self.elements.sort(key=lambda e: e.order)

    def parse_name(self, name: str) -> None:
        """
        Parse a name and extract element values

        Args:
            name: Name to parse
        """
        # Reset all elements
        for element in self.elements:
            element.standby()

        # Parse the name
        for element in self.elements:
            element.parse(name)

    def update_elements(self, updates: Dict) -> None:
        """
        Update multiple elements' values

        Args:
            updates: Dictionary mapping element IDs to new values
        """
        for element_id, new_value in updates.items():
            for element in self.elements:
                if element.id == element_id:
                    element.set_value(new_value)
                    break

    def render_name(self) -> str:
        """
        Render the pattern into a name string

        Returns:
            The rendered name
        """
        # Get all enabled elements that have values
        parts = []
        for element in self.elements:
            if element.enabled:
                render_result = element.render()
                if render_result[1]:  # If there's a value
                    separator, value = render_result
                    if parts and separator:
                        parts.append(separator)
                    parts.append(value)

        return "".join(parts)

    def validate(self) -> List[str]:
        """
        Validate the pattern configuration

        Returns:
            List of error messages, empty if valid
        """
        errors = []

        # Check if there are any elements
        if not self.elements:
            errors.append("Pattern has no elements")
            return errors

        # Check for duplicate element IDs
        element_ids = {}
        for element in self.elements:
            if element.id in element_ids:
                errors.append(f"Duplicate element ID: {element.id}")
            else:
                element_ids[element.id] = True

        # Check for duplicate orders
        element_orders = {}
        for element in self.elements:
            if element.order in element_orders:
                errors.append(f"Duplicate element order: {element.order}")
            else:
                element_orders[element.order] = True

        return errors
