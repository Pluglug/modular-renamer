from typing import Dict, Callable, Any
from .core import IRenameTarget, INamespace


class INamespace(ABC):
    """
    Interface for name namespaces
    """

    @abstractmethod
    def contains(self, name: str) -> bool:
        """
        Check if a name exists in this namespace

        Args:
            name: Name to check

        Returns:
            True if the name exists
        """
        pass

    @abstractmethod
    def add(self, name: str) -> None:
        """
        Add a name to this namespace

        Args:
            name: Name to add
        """
        pass

    @abstractmethod
    def remove(self, name: str) -> None:
        """
        Remove a name from this namespace

        Args:
            name: Name to remove
        """
        pass

    @abstractmethod
    def update(self, old_name: str, new_name: str) -> None:
        """
        Update a name in this namespace

        Args:
            old_name: Old name
            new_name: New name
        """
        pass


class NamespaceBase(INamespace):
    """
    Base implementation of INamespace
    """

    def __init__(self):
        """
        Initialize the namespace
        """
        self.names: Set[str] = set()
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """
        Initialize the namespace with names
        """
        pass

    def contains(self, name: str) -> bool:
        """
        Check if a name exists in this namespace

        Args:
            name: Name to check

        Returns:
            True if the name exists
        """
        return name in self.names

    def add(self, name: str) -> None:
        """
        Add a name to this namespace

        Args:
            name: Name to add
        """
        self.names.add(name)

    def remove(self, name: str) -> None:
        """
        Remove a name from this namespace

        Args:
            name: Name to remove
        """
        if name in self.names:
            self.names.remove(name)

    def update(self, old_name: str, new_name: str) -> None:
        """
        Update a name in this namespace

        Args:
            old_name: Old name
            new_name: New name
        """
        self.remove(old_name)
        self.add(new_name)


class NamespaceManager:
    """
    Manages namespaces for different target types
    """

    def __init__(self):
        """
        Initialize the namespace manager
        """
        self.namespaces: Dict[Any, INamespace] = {}
        self._namespace_factories: Dict[str, Callable] = {}

    def register_namespace_type(self, target_type: str, factory: Callable) -> None:
        """
        Register a namespace factory for a target type

        Args:
            target_type: Type of target
            factory: Factory function that creates a namespace for a target
        """
        self._namespace_factories[target_type] = factory

    def get_namespace(self, target: IRenameTarget) -> INamespace:
        """
        Get the namespace for a target

        Args:
            target: Target to get namespace for

        Returns:
            Namespace for the target

        Raises:
            KeyError: If no namespace factory is registered for the target type
        """
        target_type = target.target_type
        namespace_key = target.get_namespace_key()

        # Return existing namespace if it exists
        if namespace_key in self.namespaces:
            return self.namespaces[namespace_key]

        # Create new namespace
        if target_type not in self._namespace_factories:
            raise KeyError(
                f"No namespace factory registered for target type: {target_type}"
            )

        factory = self._namespace_factories[target_type]
        namespace = factory(target)
        self.namespaces[namespace_key] = namespace

        return namespace
