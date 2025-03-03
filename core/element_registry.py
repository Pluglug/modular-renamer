"""
名前要素の登録・管理・生成
"""

from typing import Dict, Type, List
from .elements import INameElement


class ElementRegistry:
    """
    Registry for element types that can be created dynamically based on configuration
    """

    def __init__(self):
        self._element_types: Dict[str, Type] = {}

    def register_element_type(self, type_name: str, element_class: Type):
        """
        Register an element type with the registry

        Args:
            type_name: Unique identifier for this element type
            element_class: Class to instantiate for this element type
        """
        if not issubclass(element_class, INameElement):
            raise TypeError(
                f"Element class must implement INameElement interface: {element_class.__name__}"
            )

        self._element_types[type_name] = element_class

    def create_element(self, type_name: str, config: dict) -> INameElement:
        """
        Create an element instance based on its type and configuration

        Args:
            type_name: Type of element to create
            config: Configuration dictionary for the element

        Returns:
            An instance of the requested element type

        Raises:
            KeyError: If the element type is not registered
        """
        if type_name not in self._element_types:
            raise KeyError(f"Element type not registered: {type_name}")

        element_class = self._element_types[type_name]
        return element_class(config)

    def get_registered_types(self) -> List[str]:
        """
        Get a list of all registered element types

        Returns:
            List of element type names
        """
        return list(self._element_types.keys())

    def validate_elements_config(self, config: List) -> List[str]:
        """
        Validate a list of element configurations

        Args:
            config: List of element configurations to validate

        Returns:
            List of error messages, empty if valid
        """
        errors = []

        if not isinstance(config, list):
            errors.append("Elements configuration must be a list")
            return errors

        element_ids = set()

        for idx, element_config in enumerate(config):
            if not isinstance(element_config, dict):
                errors.append(f"Element at index {idx} must be a dictionary")
                continue

            if "type" not in element_config:
                errors.append(f"Element at index {idx} is missing 'type' field")
                continue

            element_type = element_config["type"]
            if element_type not in self._element_types:
                errors.append(f"Unknown element type '{element_type}' at index {idx}")
                continue

            if "id" not in element_config:
                errors.append(f"Element at index {idx} is missing 'id' field")
                continue

            element_id = element_config["id"]
            if element_id in element_ids:
                errors.append(f"Duplicate element ID '{element_id}' at index {idx}")
            else:
                element_ids.add(element_id)

        return errors
