from abc import ABC, abstractmethod
import inspect
from typing import Any, Dict, Set, List, Type, Optional

from bpy.types import Context


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


class Namespace(INamespace):
    """
    汎用名前空間コンテナ
    """

    def __init__(self, initializer):
        """
        名前空間を初期化する

        Args:
            context: Blenderコンテキスト
            initializer: 名前集合を初期化する関数(context) -> Set[str]
        """
        self._names: Set[str] = set()
        self._initializer = initializer

        if self._initializer:
            self._initialize()

    def _initialize(self) -> None:
        """
        名前空間を初期化する
        """
        names = self._initializer()
        if names:
            self._names = set(names)

    def contains(self, name: str) -> bool:
        return name in self._names

    def add(self, name: str) -> None:
        self._names.add(name)

    def remove(self, name: str) -> None:
        if name in self._names:
            self._names.remove(name)

    def update(self, old_name: str, new_name: str) -> None:
        self.remove(old_name)
        self.add(new_name)


class NamespaceCache:
    """
    名前空間のキャッシュを管理する
    """

    def __init__(self):
        """
        名前空間キャッシュを初期化する

        Args:
            context: Blenderコンテキスト
        """
        self._namespaces: Dict[Any, INamespace] = {}

    def get_namespace(self, target: "IRenameTarget") -> INamespace:
        """
        ターゲットの名前空間を取得する
        存在しない場合は作成してキャッシュする

        Args:
            target: リネームターゲット

        Returns:
            ターゲットの名前空間
        """
        key = target.get_namespace_key()

        # キャッシュにある場合はそれを返す
        if key in self._namespaces:
            return self._namespaces[key]

        # ターゲットに名前空間の作成を依頼
        namespace = Namespace(target.create_namespace)
        if namespace:
            self._namespaces[key] = namespace
            return namespace

        # 作成に失敗した場合はエラー
        raise KeyError(f"ターゲットの名前空間を作成できません: {target.target_type}")

    def update_context(self, context: Any) -> None:
        """
        コンテキストを更新する
        これにより名前空間キャッシュがクリアされる

        Args:
            context: 新しいBlenderコンテキスト
        """
        self._context = context
        self.clear()

    def clear(self) -> None:
        """
        名前空間キャッシュをクリアする
        """
        self._namespaces.clear()

    def get_all_namespaces(self) -> List[INamespace]:
        """
        キャッシュ内のすべての名前空間を取得する
        """
        return list(self._namespaces.values())
