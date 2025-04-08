from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Set

import bpy
from bpy.types import Context

from ..addon import prefs
from ..utils.logging import get_logger
from .conflict_resolver import ConflictResolver
from .element import ICounter
from ..elements.counter_element import BlenderCounter
from .element_registry import ElementRegistry
from .namespace import NamespaceCache
from .pattern import NamingPattern
from .pattern_system import PatternCache, PatternFacade
from .rename_target import IRenameTarget
from .collector import TargetCollector
from .scope import CollectionSource, OperationScope

log = get_logger(__name__)


class RenameOperationType(str, Enum):
    """リネーム操作の種類"""

    ADD_REPLACE = "ADD_REPLACE"
    REMOVE = "REMOVE"

    def __str__(self) -> str:
        return self.value


@dataclass
class RenameResult:
    """
    リネーム処理の結果
    """

    target: IRenameTarget
    original_name: str
    proposed_name: str
    final_name: str
    # success: bool = False
    # message: str = ""
    approved: bool = True

    def __repr__(self) -> str:
        return f"RenameResult(target={self.target.get_name()}, original={self.original_name}, final={self.final_name})"


class RenameContext:
    """
    一括リネーム操作を管理するクラス
    """

    def __init__(
        self,
        targets: List[IRenameTarget],
        pattern: NamingPattern,
        # strategy: str = "counter",
    ):
        """
        一括リネーム操作を初期化する

        Args:
            targets: リネーム対象のリスト
            pattern: 使用する命名パターン
        """
        self.targets: List[IRenameTarget] = targets
        self.pattern: NamingPattern = pattern
        # self.strategy: str = strategy
        # self.element_updates: Dict = {}
        self.results: List[RenameResult] = []
        # self.pending_results: Dict[str, RenameResult] = {}
        # self.has_conflicts = False

    def get_result_summary(self) -> str:
        """
        リネーム結果のサマリーを取得する

        Returns:
            サマリー文字列
        """
        success_count = sum(1 for result in self.results if result.success)
        return f"{success_count}/{len(self.targets)}件のリネームが成功しました"

    def get_name_changes(self) -> List[tuple[str, str]]:
        """
        リネーム前後の名前の変更リストを取得する

        Returns:
            List[tuple[str, str]]: (古い名前, 新しい名前)のタプルのリスト
        """
        changes = []
        for result in self.results:
            changes.append((result.original_name, result.final_name))
        return changes


class RenameService:
    """
    ターゲットの一括リネームサービス
    """

    def __init__(
        self,
        context: Context,
        scope: OperationScope,
    ):
        """
        リネームサービスを初期化する
        """
        self._target_collector = TargetCollector(context, scope)
        self._pattern_facade = PatternFacade(context)
        self._conflict_resolver = ConflictResolver()

        self.r_ctx: RenameContext = self._prepare_rename_context()

    def _prepare_rename_context(self) -> RenameContext:
        pattern = self._pattern_facade.get_active_pattern()
        if not pattern:
            raise ValueError("アクティブなパターンが見つかりません")

        targets = self._target_collector.collect_targets()
        if not targets:
            log.error("リネーム対象が見つかりません")
            # 空のターゲットリストでRenameContextを作成
            return RenameContext([], pattern)

        log.info(f"targets: {[t.get_name() for t in targets]}")
        return RenameContext(targets, pattern)

    def generate_rename_plan(
        self,
        updates: Dict[str, str],
    ):  # TODO: R-CTX or List[RenameResult]
        """
        要素の更新を適用する
        """

        counter_elements = []
        for element_id in updates.keys():
            try:
                element = self.r_ctx.pattern.get_element_by_id(element_id)
                if isinstance(element, ICounter):
                    counter_elements.append(element)
            except ValueError:
                continue

        for idx, target in enumerate(self.r_ctx.targets):
            # ターゲットの名前を解析
            self.r_ctx.pattern.parse_name(target.get_name())

            # # XXX: カウンター要素の値を更新
            # for counter in counter_elements:
            #     if isinstance(counter, BlenderCounter):
            #         # BlenderCounterの値を優先的に使用
            #         if counter.value is not None:
            #             counter_value = int(counter.value.lstrip('.'))
            #             counter.set_value(str(counter_value))
            #     else:
            #         # その他のカウンターはインデックスを使用
            #         counter.set_value(str(idx + 1))

            # その他の要素を更新
            self.r_ctx.pattern.update_elements(updates)

            # カウンター要素に対してインデックスを加算
            for counter in counter_elements:
                counter.add(idx)

            proposed_name = self.r_ctx.pattern.render_name()
            new_name = self._conflict_resolver.resolve_name_conflict(
                target, self.r_ctx.pattern, proposed_name, "counter"
            )

            self.r_ctx.results.append(
                RenameResult(
                    target=target,
                    original_name=target.get_name(),
                    proposed_name=proposed_name,
                    final_name=new_name,
                )
            )

        log.info(
            f"results:\n{chr(10).join([f'{r.original_name} -> {r.final_name}' for r in self.r_ctx.results])}"
        )
        return self.r_ctx

    def apply_rename_plan(self) -> None:
        """
        リネーム結果を実際のオブジェクトに適用する
        """
        # シンプルな解決策: 一度すべてのターゲットをランダムな名前に変更する
        # これをしないと、Namespaceで重複がない場合でも、.001が発生する
        for target in self.r_ctx.targets:
            target.set_name(f"__tmp_{id(target)}_{hash(target.get_name())}")

        for result in self.r_ctx.results:
            if result.approved:
                result.target.set_name(result.final_name)
