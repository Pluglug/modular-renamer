from typing import Any, Dict, List

from ..contracts.namespace import INamespace, Namespace
from ..contracts.target import IRenameTarget


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
        raise KeyError(f"ターゲットの名前空間を作成できません: {target.bl_type}")

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
