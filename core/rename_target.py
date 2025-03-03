"""
リネーム対象の統一インターフェース
旧 RenameableObject
"""

from abc import ABC, abstractmethod
from typing import Any, Set


class IRenameTarget(ABC):
    """
    Interface for objects that can be renamed
    """

    @property
    @abstractmethod
    def target_type(self) -> str:
        """
        Get the type of this target

        Returns:
            Target type string
        """
        pass

    @property
    @abstractmethod
    def blender_object(self) -> Any:
        """
        Get the underlying Blender object

        Returns:
            Blender object
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the current name of the target

        Returns:
            Current name
        """
        pass

    @abstractmethod
    def set_name(self, name: str) -> None:
        """
        Set the name of the target

        Args:
            name: New name
        """
        pass

    @abstractmethod
    def get_namespace_key(self) -> Any:
        """
        Get the key for the namespace this target belongs to

        Returns:
            Namespace key
        """
        pass
