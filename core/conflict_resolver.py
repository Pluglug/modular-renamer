from typing import Any, Dict, List, Optional, Set

from .namespace import NamespaceCache, INamespace
from .pattern import NamingPattern
from .rename_target import IRenameTarget


class ConflictResolver:
    """
    名前の衝突を検出し解決するクラス
    """

    # 競合解決戦略
    STRATEGY_COUNTER = "counter"  # カウンターを用いて解決
    STRATEGY_FORCE = "force"  # 強制上書き

    def __init__(self, namespace_cache: NamespaceCache):
        """
        コンフリクトリゾルバーを初期化する

        Args:
            namespace_cache: NamespaceCacheインスタンス
        """
        self.namespace_cache = namespace_cache
        self.resolved_conflicts: List[Dict] = []

    def resolve_name_conflict(
        self,
        target: IRenameTarget,
        pattern: NamingPattern,
        proposed_name: str,
        strategy: str,
    ) -> str:
        """
        ターゲットの名前競合を解決する

        Args:
            target: リネーム対象
            pattern: 使用するパターン（カウンター要素の更新に使用）
            proposed_name: 提案された名前
            strategy: 競合解決戦略

        Returns:
            解決された名前
        """
        if not proposed_name:
            return ""

        # ターゲットの名前空間を取得
        namespace = self._get_namespace(target)
        if not namespace:
            return proposed_name  # 名前空間がない場合は提案名をそのまま返す

        # 現在の名前を取得
        original_name = target.get_name()

        # 名前が競合するか確認
        if not self._is_name_in_conflict(proposed_name, namespace, target):
            # 競合がなければ名前空間を更新して提案名を返す
            if original_name != proposed_name:  # 名前が変わる場合のみ更新
                namespace.update(original_name, proposed_name)
            return proposed_name

        # 解決戦略に応じて処理
        final_name = ""
        if strategy == self.STRATEGY_COUNTER:
            final_name = self._resolve_with_counter(pattern, proposed_name, namespace)
        elif strategy == self.STRATEGY_FORCE:
            final_name = self._resolve_with_force(proposed_name)
        else:
            # 不明な戦略の場合は提案名をそのまま返す
            final_name = proposed_name

        # 解決された名前で名前空間を更新
        if original_name != final_name:  # 名前が変わる場合のみ更新
            namespace.update(original_name, final_name)

        return final_name

    def apply_namespace_update(
        self, target: IRenameTarget, old_name: str, new_name: str
    ) -> None:
        """
        実際の名前空間を更新する

        Args:
            target: リネーム対象
            old_name: 古い名前
            new_name: 新しい名前
        """
        namespace = self._get_namespace(target)
        if namespace:
            namespace.update(old_name, new_name)

    def _get_namespace(self, target: IRenameTarget) -> Optional[INamespace]:
        """
        ターゲットの名前空間を取得する

        Args:
            target: リネーム対象

        Returns:
            名前空間、または取得できない場合はNone
        """
        try:
            return self.namespace_cache.get_namespace(target)
        except Exception:
            return None

    def _is_name_in_conflict(
        self, name: str, namespace: INamespace, target: IRenameTarget
    ) -> bool:
        """
        名前が競合するか確認する

        Args:
            name: チェックする名前
            namespace: 名前空間
            target: リネーム対象（現在の名前を除外するため）

        Returns:
            競合がある場合はTrue
        """
        # ターゲット自身の現在の名前は競合とみなさない
        if name == target.get_name():
            return False

        # 名前空間で名前の競合をチェック
        return namespace.contains(name)

    def _resolve_with_counter(
        self, pattern: NamingPattern, name: str, namespace: INamespace
    ) -> str:
        """
        カウンター要素を使用して名前競合を解決する

        Args:
            pattern: 命名パターン
            name: 競合している名前
            namespace: 名前空間

        Returns:
            解決された名前
        """
        # カウンター要素を探す
        counter_elements = [e for e in pattern.elements if hasattr(e, "increment")]

        if not counter_elements:
            # カウンター要素がない場合は単純にサフィックスを追加
            suffix = 1
            new_name = f"{name}.{suffix:03d}"

            while namespace.contains(new_name):
                suffix += 1
                new_name = f"{name}.{suffix:03d}"

                # 無限ループ防止
                if suffix > 999:
                    break

            return new_name

        # カウンター要素を使用
        counter = counter_elements[-1]  # 最後のカウンター要素を使用

        # 競合が解消されるまでカウンターを増分
        iterations = 0
        max_iterations = 1000  # 安全のため最大試行回数を制限

        while iterations < max_iterations:
            counter.increment()
            new_name = pattern.render_name()

            if not namespace.contains(new_name):
                return new_name

            iterations += 1

        # 最大試行回数に達した場合
        return f"{name}_unsolved_conflict"

    def _resolve_with_force(self, name: str) -> str:
        """
        強制上書きで名前競合を解決する（実質的に競合を無視）

        Args:
            name: 提案された名前

        Returns:
            同じ名前（変更なし）
        """
        return name

    def _find_conflicting_targets(
        self, target: IRenameTarget, name: str
    ) -> List[IRenameTarget]:
        """
        指定された名前と競合するターゲットを見つける

        Args:
            target: 現在のリネーム対象
            name: チェックする名前

        Returns:
            競合するターゲットのリスト
        """
        # 実際の実装では、BlenderのAPIを使用する必要がある
        # 現時点では空のリストを返す
        return []
