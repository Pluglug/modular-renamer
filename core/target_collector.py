from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .rename_target import IRenameTarget


class CollectionStrategy(ABC):
    """
    Interface for target collection strategies
    """

    @abstractmethod
    def collect(self, context: Any) -> List[IRenameTarget]:
        """
        Collect targets from the context

        Args:
            context: Blender context

        Returns:
            List of targets
        """
        pass


class TargetCollector:
    """
    Collects targets based on registered strategies
    """

    def __init__(self):
        """
        Initialize the target collector
        """
        self.strategies: Dict[str, CollectionStrategy] = {}

    def register_strategy(self, target_type: str, strategy: CollectionStrategy) -> None:
        """
        Register a collection strategy for a target type

        Args:
            target_type: Type of target
            strategy: Collection strategy
        """
        self.strategies[target_type] = strategy

    def collect(self, target_type: str, context: Any) -> List[IRenameTarget]:
        """
        Collect targets of a specific type

        Args:
            target_type: Type of target to collect
            context: Blender context

        Returns:
            List of targets

        Raises:
            KeyError: If no strategy is registered for the target type
        """
        if target_type not in self.strategies:
            raise KeyError(
                f"No collection strategy registered for target type: {target_type}"
            )

        strategy = self.strategies[target_type]
        return strategy.collect(context)
