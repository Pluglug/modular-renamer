from typing import Any, Dict, List

from .namespace import INamespace, NamespaceManager
from .rename_target import IRenameTarget


class ConflictResolver:
    """
    ターゲット間の名前の競合を解決する
    """

    # 競合解決戦略
    STRATEGY_COUNTER = "numeric_counter"
    STRATEGY_FORCE = "force"

    def __init__(self, namespace_manager: NamespaceManager):
        """
        競合解決器を初期化する

        Args:
            namespace_manager: NamespaceManagerインスタンス
        """
        self.namespace_manager = namespace_manager
        self.resolved_conflicts: List[Dict] = []

    def resolve(self, target: IRenameTarget, name: str, strategy: str) -> str:
        """
        名前の競合を解決する

        Args:
            target: リネーム対象のターゲット
            name: 提案された名前
            strategy: 競合解決戦略

        Returns:
            解決された名前（競合がない場合は提案名と同じ）
        """
        # このターゲットの名前空間を取得
        namespace = self.namespace_manager.get_namespace(target)

        # 競合があるかチェック
        current_name = target.get_name()
        if name == current_name or not namespace.contains(name):
            return name

        # 戦略に基づいて競合を解決
        if strategy == self.STRATEGY_COUNTER:
            resolved_name = self._resolve_with_counter(target, name, namespace)
        elif strategy == self.STRATEGY_FORCE:
            resolved_name = self._resolve_with_force(target, name, namespace)
        else:
            # デフォルトはカウンター戦略
            resolved_name = self._resolve_with_counter(target, name, namespace)

        # 解決を記録
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
        カウンターを追加して競合を解決する

        Args:
            target: リネーム対象のターゲット
            name: 提案された名前
            namespace: チェック対象の名前空間

        Returns:
            カウンター付きの解決された名前
        """
        base_name = name
        counter = 1
        resolved_name = name

        # 一意の名前が見つかるまで、カウンターを増やしながら名前を試す
        while namespace.contains(resolved_name) and resolved_name != target.get_name():
            resolved_name = f"{base_name}.{counter:03d}"
            counter += 1

            # 安全制限
            if counter > 999:
                # 一意の名前が見つからない場合は、元の名前を使用
                return target.get_name()

        return resolved_name

    def _resolve_with_force(
        self, target: IRenameTarget, name: str, namespace: INamespace
    ) -> str:
        """
        名前を強制的に設定し、競合するターゲットをリネームして競合を解決する

        Args:
            target: リネーム対象のターゲット
            name: 提案された名前
            namespace: チェック対象の名前空間

        Returns:
            提案された名前
        """
        # この名前と競合するすべてのターゲットを検索
        conflicting_targets = self._find_conflicting_targets(target, name)

        # 競合するターゲットをカウンター付きでリネーム
        for idx, conflict_target in enumerate(conflicting_targets, 1):
            old_name = conflict_target.get_name()
            new_name = f"{name}.conflict.{idx:03d}"
            conflict_target.set_name(new_name)

            # 名前空間を更新
            namespace = self.namespace_manager.get_namespace(conflict_target)
            namespace.update(old_name, new_name)

            # 解決を記録
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
        名前と競合するターゲットを検索する

        Args:
            target: リネーム対象のターゲット
            name: 提案された名前

        Returns:
            競合するターゲットのリスト
        """
        # これはシーン内のすべてのターゲットへのアクセスが必要
        # 実際の実装では、BlenderのAPIを使用する必要がある
        # 現時点では空のリストを返す
        return []

    def update_namespace(self, target: IRenameTarget, name: str) -> None:
        """
        名前空間を更新する
        """
        namespace = self.namespace_manager.get_namespace(target)
        namespace.update(target.get_name(), name)
