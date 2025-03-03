"""
パターンの登録・検索・保存・読み込み
古い実装では明示的に分離されていなかった機能
"""

import json
from typing import Dict, List
import os

from .pattern import NamingPattern


class PatternRegistry:
    """
    Registry that manages naming patterns for different target types
    """

    def __init__(self, element_registry):
        """
        Initialize the pattern registry

        Args:
            element_registry: ElementRegistry to create elements for patterns
        """
        self.patterns: Dict[str, Dict[str, NamingPattern]] = {}
        self.element_registry = element_registry

    def register_pattern(self, pattern: NamingPattern) -> None:
        """
        Register a pattern with the registry

        Args:
            pattern: NamingPattern to register
        """
        target_type = pattern.target_type

        # Create target type dictionary if it doesn't exist
        if target_type not in self.patterns:
            self.patterns[target_type] = {}

        # Register the pattern
        self.patterns[target_type][pattern.name] = pattern

    def get_pattern(self, target_type: str, name: str) -> NamingPattern:
        """
        Get a pattern by target type and name

        Args:
            target_type: Target type
            name: Pattern name

        Returns:
            The requested pattern

        Raises:
            KeyError: If the pattern doesn't exist
        """
        if target_type not in self.patterns:
            raise KeyError(f"No patterns for target type: {target_type}")

        if name not in self.patterns[target_type]:
            raise KeyError(f"Pattern '{name}' not found for target type: {target_type}")

        return self.patterns[target_type][name]

    def get_patterns_for_type(self, target_type: str) -> List[NamingPattern]:
        """
        Get all patterns for a target type

        Args:
            target_type: Target type

        Returns:
            List of patterns for the target type
        """
        if target_type not in self.patterns:
            return []

        return list(self.patterns[target_type].values())

    def load_from_file(self, path: str) -> None:
        """
        Load patterns from a JSON file

        Args:
            path: Path to the JSON file
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Clear existing patterns
            self.patterns = {}

            # Load patterns
            for target_type, patterns in data.items():
                for pattern_name, pattern_data in patterns.items():
                    elements_config = pattern_data.get("elements", [])
                    pattern = NamingPattern(
                        pattern_name,
                        target_type,
                        elements_config,
                        self.element_registry,
                    )
                    self.register_pattern(pattern)

        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading patterns from {path}: {e}")

    def save_to_file(self, path: str) -> bool:
        """
        Save patterns to a JSON file

        Args:
            path: Path to the JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Convert patterns to a serializable format
            data = {}
            for target_type, patterns in self.patterns.items():
                data[target_type] = {}
                for pattern_name, pattern in patterns.items():
                    # Serialize elements
                    elements = []
                    for element in pattern.elements:
                        # Extract serializable properties from element
                        # This assumes elements have a to_dict method
                        elements.append(
                            {
                                "id": element.id,
                                "type": element.__class__.__name__,
                                "order": element.order,
                                "enabled": element.enabled,
                                "separator": element.separator,
                                # Additional properties would be added here
                            }
                        )

                    data[target_type][pattern_name] = {"elements": elements}

            # Write to file
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

            return True

        except (IOError, TypeError) as e:
            print(f"Error saving patterns to {path}: {e}")
            return False
