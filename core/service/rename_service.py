from typing import Dict

from bpy.types import Context

from ..contracts.counter import ICounter
from ..namespace.conflict import ConflictResolver
from ..pattern.facade import PatternFacade
from ..target.collector import TargetCollector
from ..target.scope import OperationScope
from ..service.rename_context import RenameContext, RenameResult
from ...utils.logging import get_logger

log = get_logger(__name__)


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
