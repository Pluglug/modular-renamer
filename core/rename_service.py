from typing import List, Dict, Any, Optional

from .pattern import NamingPattern
from .pattern_registry import PatternRegistry
from .rename_target import IRenameTarget
from .namespace import NamespaceManager
from .conflict_resolver import ConflictResolver


class RenameContext:
    """
    Context for a rename operation
    """

    def __init__(self, target: IRenameTarget, pattern: NamingPattern):
        """
        Initialize the rename context

        Args:
            target: Target being renamed
            pattern: Naming pattern to use
        """
        self.target = target
        self.pattern = pattern
        self.original_name = target.get_name()
        self.proposed_name = ""
        self.final_name = ""
        self.conflict_resolution = None

    def __repr__(self) -> str:
        return f"RenameContext(target={self.target.get_name()}, original={self.original_name}, proposed={self.proposed_name}, final={self.final_name})"


class RenameService:
    """
    Service for renaming targets
    """

    def __init__(
        self,
        pattern_registry: PatternRegistry,
        namespace_manager: NamespaceManager,
        conflict_resolver: ConflictResolver,
    ):
        """
        Initialize the rename service

        Args:
            pattern_registry: PatternRegistry instance
            namespace_manager: NamespaceManager instance
            conflict_resolver: ConflictResolver instance
        """
        self.pattern_registry = pattern_registry
        self.namespace_manager = namespace_manager
        self.conflict_resolver = conflict_resolver

    def prepare(self, target: IRenameTarget, pattern_name: str) -> RenameContext:
        """
        Prepare a rename operation

        Args:
            target: Target to rename
            pattern_name: Name of pattern to use

        Returns:
            Rename context

        Raises:
            KeyError: If pattern doesn't exist
        """
        target_type = target.target_type
        pattern = self.pattern_registry.get_pattern(target_type, pattern_name)

        context = RenameContext(target, pattern)

        # Parse the target's current name
        pattern.parse_name(target.get_name())

        # Generate proposed name
        context.proposed_name = pattern.render_name()

        return context

    def update_elements(self, context: RenameContext, updates: Dict) -> RenameContext:
        """
        Update elements in a rename context

        Args:
            context: Rename context
            updates: Dictionary of element updates

        Returns:
            Updated context
        """
        # Update pattern elements
        context.pattern.update_elements(updates)

        # Update proposed name
        context.proposed_name = context.pattern.render_name()

        return context

    def execute(self, context: RenameContext, strategy: str) -> bool:
        """
        Execute a rename operation

        Args:
            context: Rename context
            strategy: Conflict resolution strategy

        Returns:
            True if successful
        """
        if not context.proposed_name:
            return False

        # Resolve conflicts
        context.final_name = self.conflict_resolver.resolve(
            context.target, context.proposed_name, strategy
        )

        if not context.final_name:
            return False

        # Update the target's name
        old_name = context.target.get_name()
        context.target.set_name(context.final_name)

        # Update namespace
        namespace = self.namespace_manager.get_namespace(context.target)
        namespace.update(old_name, context.final_name)

        return True

    def batch_rename(
        self,
        targets: List[IRenameTarget],
        pattern_name: str,
        updates: Dict,
        strategy: str,
    ) -> List[RenameContext]:
        """
        Rename multiple targets

        Args:
            targets: List of targets to rename
            pattern_name: Name of pattern to use
            updates: Dictionary of element updates
            strategy: Conflict resolution strategy

        Returns:
            List of rename contexts
        """
        contexts = []

        for target in targets:
            # Skip targets with invalid type
            try:
                context = self.prepare(target, pattern_name)
                context = self.update_elements(context, updates)
                self.execute(context, strategy)
                contexts.append(context)
            except KeyError:
                # Skip targets for which the pattern doesn't exist
                pass

        return contexts
