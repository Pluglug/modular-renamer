from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Set, List

from .rename_target import IRenameTarget


class INamespace(ABC):
    """
    名前空間のインターフェース
    """

    @abstractmethod
    def contains(self, name: str) -> bool:
        """
        この名前空間に名前が存在するかチェックする

        Args:
            name: チェックする名前

        Returns:
            名前が存在する場合はTrue
        """
        pass

    @abstractmethod
    def add(self, name: str) -> None:
        """
        この名前空間に名前を追加する

        Args:
            name: 追加する名前
        """
        pass

    @abstractmethod
    def remove(self, name: str) -> None:
        """
        この名前空間から名前を削除する

        Args:
            name: 削除する名前
        """
        pass

    @abstractmethod
    def update(self, old_name: str, new_name: str) -> None:
        """
        この名前空間の名前を更新する

        Args:
            old_name: 古い名前
            new_name: 新しい名前
        """
        pass


class NamespaceBase(INamespace):
    """
    INamespaceの基本実装
    """

    def __init__(self):
        """
        名前空間を初期化する
        """
        self.names: Set[str] = set()
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """
        名前で名前空間を初期化する
        """
        pass

    def contains(self, name: str) -> bool:
        """
        この名前空間に名前が存在するかチェックする

        Args:
            name: チェックする名前

        Returns:
            名前が存在する場合はTrue
        """
        return name in self.names

    def add(self, name: str) -> None:
        """
        この名前空間に名前を追加する

        Args:
            name: 追加する名前
        """
        self.names.add(name)

    def remove(self, name: str) -> None:
        """
        この名前空間から名前を削除する

        Args:
            name: 削除する名前
        """
        if name in self.names:
            self.names.remove(name)

    def update(self, old_name: str, new_name: str) -> None:
        """
        この名前空間の名前を更新する

        Args:
            old_name: 古い名前
            new_name: 新しい名前
        """
        self.remove(old_name)
        self.add(new_name)


class NamespaceManager:
    """
    異なるターゲットタイプの名前空間を管理する
    """

    def __init__(self):
        """
        名前空間マネージャーを初期化する
        """
        self.namespaces: Dict[Any, INamespace] = {}
        self._namespace_factories: Dict[str, Callable] = {}

    def register_namespace_type(self, target_type: str, factory: Callable) -> None:
        """
        ターゲットタイプの名前空間ファクトリを登録する

        Args:
            target_type: ターゲットのタイプ
            factory: ターゲットの名前空間を作成するファクトリ関数
        """
        self._namespace_factories[target_type] = factory

    def get_namespace(self, target: IRenameTarget) -> INamespace:
        """
        ターゲットの名前空間を取得する

        Args:
            target: 名前空間を取得するターゲット

        Returns:
            ターゲットの名前空間

        Raises:
            KeyError: ターゲットタイプの名前空間ファクトリが登録されていない場合
        """
        target_type = target.target_type
        namespace_key = target.get_namespace_key()

        # 既存の名前空間がある場合は返す
        if namespace_key in self.namespaces:
            return self.namespaces[namespace_key]

        # 新しい名前空間を作成
        if target_type not in self._namespace_factories:
            raise KeyError(
                f"ターゲットタイプの名前空間ファクトリが登録されていません: {target_type}"
            )

        factory = self._namespace_factories[target_type]
        namespace = factory(target)
        self.namespaces[namespace_key] = namespace

        return namespace

    def get_all_namespaces(self) -> List[INamespace]:
        """
        管理している全ての名前空間のリストを取得する

        Returns:
            名前空間のリスト
        """
        return list(self.namespaces.values())
