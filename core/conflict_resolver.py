from typing import Any, Dict, List, Optional, Set

from ..elements.counter_element import NumericCounter, BlenderCounter
from .namespace import NamespaceCache, INamespace
from .pattern import NamingPattern
from .rename_target import IRenameTarget

from ..utils.logging import get_logger

log = get_logger(__name__)


class ConflictResolver:
    """
    名前の衝突を検出し解決するクラス
    """

    # 競合解決戦略
    STRATEGY_COUNTER = "counter"  # カウンターを用いて解決
    STRATEGY_FORCE = "force"  # 強制上書き

    def __init__(self):
        """
        コンフリクトリゾルバーを初期化する
        """
        self._namespace_cache = NamespaceCache()
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
        # elif strategy == self.STRATEGY_FORCE:
        #     final_name = self._resolve_with_force(proposed_name)
        else:
            print(f"Not Supported Strategy: {strategy}")
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
        namespace.update(old_name, new_name)

    def _get_namespace(self, target: IRenameTarget) -> INamespace:
        """
        ターゲットの名前空間を取得する

        Args:
            target: リネーム対象

        Returns:
            名前空間、または取得できない場合はNone
        """
        return self._namespace_cache.get_namespace(target)

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
        # NumericCounterを探す
        # TODO: PatternやPatternFacadeを通じてカウンター要素を取得すべき
        numeric_counter = [
            e for e in pattern.elements if isinstance(e, NumericCounter)
        ][-1]
        blender_counter = [
            e for e in pattern.elements if isinstance(e, BlenderCounter)
        ][-1]

        log.info(f"numeric_counter: {numeric_counter.value}")
        log.info(f"blender_counter: {blender_counter.value}")

        # BlenderCounterの値を優先的に使用
        if blender_counter.value is not None:
            # BlenderCounterの値を直接設定
            counter_value = int(blender_counter.value.lstrip('.'))
            numeric_counter.set_value(str(counter_value))
            log.info(f"set counter value: {counter_value}")
        else:
            # BlenderCounterの値がない場合は、現在のNumericCounterの値を使用
            current_value = numeric_counter.value_int or 1
            numeric_counter.set_value(str(current_value))
            log.info(f"using current counter: {current_value}")

        if not numeric_counter:
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

        # 競合が解消されるまでカウンターを増分
        start_value = numeric_counter.value_int or 1
        max_value = start_value + 1000

        for idx in range(start_value, max_value):
            # TODO: Patternがincrementすべき
            # counter.increment()
            # new_name = pattern.render_name()
            proposed_name = numeric_counter.gen_proposed_name(idx)
            log.debug(f"resolving with counter: {proposed_name}")

            if not namespace.contains(proposed_name):
                return proposed_name

        # 最大試行回数に達した場合
        return f"{name}_unsolved_conflict"

    # # デフォルトの挙動としては、現在の「現在値からのインクリメント」方式の方が、パフォーマンスと設計の一貫性の観点からバランスが良い
    # def _find_unused_min_counter_value(
    #     self, pattern: NamingPattern, namespace: INamespace, name: str, start_value: int = 1
    # ) -> int:
    #     """
    #     未使用の最小のカウンター値を見つける
    #     メリット: 名前の連番にできた欠番（例: .002 がない状態）を自動的に埋めようとするため、結果として番号がきれいに整列しやすい。
    #     デメリット: 衝突のたびに最小値を 1 から探索し直す可能性があり、要素数が多い場合に計算コストが高くなる可能性がある。また、リネームの順序によって割り当てられる番号が変わる可能性が現在のロジックより高い。ユーザーが意図したカウンター開始値が無視される場合がある。
    #     """
    #     numeric_counter = [e for e in pattern.elements if isinstance(e, NumericCounter)][-1]
    #     for idx in range(start_value, 1000):
    #         proposed_name = numeric_counter.gen_proposed_name(idx)
    #         if not namespace.contains(proposed_name):
    #             return idx
    #     return None

    def _resolve_with_force(self, name: str) -> str:
        """強制上書きで名前競合を解決する"""
        return name

    def _find_conflicting_targets(
        self, target: IRenameTarget, name: str
    ) -> List[IRenameTarget]:
        """指定された名前と競合するターゲットを見つける"""
        # Contextが必要
        pass
