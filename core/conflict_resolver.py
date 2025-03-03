from typing import List, Dict, Any
from .core import IRenameTarget, INamespace, NamespaceManager


class ConflictResolver:
    """
    Resolves naming conflicts between targets
    """

    # Conflict resolution strategies
    STRATEGY_COUNTER = "counter"
    STRATEGY_FORCE = "force"

    def __init__(self, namespace_manager: NamespaceManager):
        """
        Initialize the conflict resolver

        Args:
            namespace_manager: NamespaceManager instance
        """
        self.namespace_manager = namespace_manager
        self.resolved_conflicts: List[Dict] = []

    def resolve(self, target: IRenameTarget, name: str, strategy: str) -> str:
        """
        Resolve a naming conflict

        Args:
            target: Target being renamed
            name: Proposed name
            strategy: Conflict resolution strategy

        Returns:
            Resolved name (may be the same as proposed if no conflict)
        """
        # Get the namespace for this target
        namespace = self.namespace_manager.get_namespace(target)

        # Check if there's a conflict
        current_name = target.get_name()
        if name == current_name or not namespace.contains(name):
            return name

        # Resolve conflict based on strategy
        if strategy == self.STRATEGY_COUNTER:
            resolved_name = self._resolve_with_counter(target, name, namespace)
        elif strategy == self.STRATEGY_FORCE:
            resolved_name = self._resolve_with_force(target, name, namespace)
        else:
            # Default to counter strategy
            resolved_name = self._resolve_with_counter(target, name, namespace)

        # Record the resolution
        self.resolved_conflicts.append(
            {
                "target_type": target.target_type,
                "original_name": target.get_name(),
                "proposed_name": name,
                "resolved_name": resolved_name,
                "strategy": strategy,
            }
        )

        return resolved_name

    def _resolve_with_counter(
        self, target: IRenameTarget, name: str, namespace: INamespace
    ) -> str:
        """
        Resolve conflict by adding a counter

        Args:
            target: Target being renamed
            name: Proposed name
            namespace: Namespace to check against

        Returns:
            Resolved name with counter
        """
        base_name = name
        counter = 1
        resolved_name = name

        # Try names with increasing counters until a unique name is found
        while namespace.contains(resolved_name) and resolved_name != target.get_name():
            resolved_name = f"{base_name}.{counter:03d}"
            counter += 1

            # Safety limit
            if counter > 999:
                # If we can't find a unique name, just use the original
                return target.get_name()

        return resolved_name

    def _resolve_with_force(
        self, target: IRenameTarget, name: str, namespace: INamespace
    ) -> str:
        """
        Resolve conflict by forcing the name and renaming conflicting targets

        Args:
            target: Target being renamed
            name: Proposed name
            namespace: Namespace to check against

        Returns:
            The proposed name
        """
        # Find all targets that conflict with this name
        conflicting_targets = self._find_conflicting_targets(target, name)

        # Rename conflicting targets with counter
        for idx, conflict_target in enumerate(conflicting_targets, 1):
            old_name = conflict_target.get_name()
            new_name = f"{name}.conflict.{idx:03d}"
            conflict_target.set_name(new_name)

            # Update namespace
            namespace = self.namespace_manager.get_namespace(conflict_target)
            namespace.update(old_name, new_name)

            # Record the resolution
            self.resolved_conflicts.append(
                {
                    "target_type": conflict_target.target_type,
                    "original_name": old_name,
                    "proposed_name": old_name,
                    "resolved_name": new_name,
                    "strategy": "conflict",
                }
            )

        return name

    def _find_conflicting_targets(
        self, target: IRenameTarget, name: str
    ) -> List[IRenameTarget]:
        """
        Find targets that conflict with a name

        Args:
            target: Target being renamed
            name: Proposed name

        Returns:
            List of conflicting targets
        """
        # This would require access to all targets in the scene
        # In a real implementation, this would need to use Blender's API
        # For now, we'll return an empty list
        return []
