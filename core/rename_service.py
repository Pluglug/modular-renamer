from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from bpy.types import Context

from .conflict_resolver import ConflictResolver
from .namespace import NamespaceManager
from .pattern import NamingPattern
from .pattern_registry import PatternRegistry
from .rename_target import IRenameTarget
from .target_collector import TargetCollector


class RenameExecutionContext:
    """
    リネーム実行全体のコンテキストを管理するクラス
    各リネーム操作の実行状態、名前空間の管理を担当
    """

    def __init__(self):
        """
        リネーム実行コンテキストを初期化する
        """
        self._namespace_manager = NamespaceManager()
        self._original_state = {}
        self._simulation_mode = False

    @property
    def namespace_manager(self) -> NamespaceManager:
        """名前空間マネージャーを取得する"""
        return self._namespace_manager

    def initialize(self) -> None:
        """
        コンテキストを初期化する
        名前空間マネージャーを準備し、初期状態を設定
        """
        self._namespace_manager = NamespaceManager()
        self._original_state = {}
        self._simulation_mode = False

    def enter_simulation_mode(self) -> None:
        """
        シミュレーションモードを開始する
        このモードでは、実際のオブジェクトは変更せず
        名前空間の更新のみをシミュレートする
        """
        self.backup_current_state()
        self._simulation_mode = True

    def exit_simulation_mode(self) -> None:
        """
        シミュレーションモードを終了する
        """
        self._simulation_mode = False

    def is_in_simulation_mode(self) -> bool:
        """
        現在シミュレーションモードかどうかを返す
        """
        return self._simulation_mode

    def backup_current_state(self) -> None:
        """
        現在の名前空間の状態をバックアップする
        """
        # シンプルな実装: 名前空間マネージャーの状態をバックアップ
        # 実際の実装では、より複雑な状態管理が必要かもしれない
        self._original_state = {
            'namespaces': self._namespace_manager.get_state()
        }

    def restore_original_state(self) -> None:
        """
        元の状態に戻す
        """
        if 'namespaces' in self._original_state:
            self._namespace_manager.restore_state(self._original_state['namespaces'])

    def reset(self) -> None:
        """
        コンテキストをリセットする
        """
        self._namespace_manager.reset()
        self._original_state = {}
        self._simulation_mode = False


class RenameResult:
    """
    単一ターゲットのリネーム結果
    """

    def __init__(self, target: IRenameTarget):
        """
        リネーム結果を初期化する

        Args:
            target: リネーム対象
        """
        self.target = target
        self.original_name = target.get_name()
        self.proposed_name = ""
        self.final_name = ""
        self.success = False
        self.message = ""

    def __repr__(self) -> str:
        return f"RenameResult(target={self.target.get_name()}, original={self.original_name}, proposed={self.proposed_name}, final={self.final_name}, success={self.success})"


class BatchRenameOperation:
    """
    複数ターゲットに対するバッチリネーム操作
    """

    def __init__(
        self,
        targets: List[IRenameTarget],
        pattern: NamingPattern,
        strategy: str = "counter",
        execution_context: RenameExecutionContext = None
    ):
        """
        バッチリネーム操作を初期化する

        Args:
            targets: リネーム対象のリスト
            pattern: 使用する命名パターン
            strategy: 名前競合解決戦略 (デフォルト: "counter")
            execution_context: リネーム実行コンテキスト
        """
        self.targets = targets
        self.pattern = pattern
        self.element_updates = {}
        self.strategy = strategy
        self.results = []
        self.pending_results = {}  # id -> RenameResult のマップ
        self.has_conflicts = False
        self.execution_context = execution_context or RenameExecutionContext()

    def get_result_summary(self) -> str:
        """
        操作結果の要約を取得する

        Returns:
            結果の要約文字列
        """
        success_count = sum(1 for r in self.results if r.success)
        return f"{success_count}/{len(self.targets)} ターゲットのリネームに成功しました"


class RenameService:
    """
    ターゲットのリネームサービス
    """

    def __init__(
        self,
        pattern_registry: PatternRegistry,
        conflict_resolver: ConflictResolver,
        target_collector: TargetCollector,
    ):
        """
        リネームサービスを初期化する

        Args:
            pattern_registry: PatternRegistryインスタンス
            conflict_resolver: ConflictResolverインスタンス
            target_collector: TargetCollectorインスタンス
        """
        self.pattern_registry = pattern_registry
        self.conflict_resolver = conflict_resolver
        self.target_collector = target_collector

    def prepare_batch(
        self,
        target_type: str,
        pattern_name: str,
        context: Context,
        execution_context: Optional[RenameExecutionContext] = None
    ) -> BatchRenameOperation:
        """
        バッチリネーム操作を準備する

        Args:
            target_type: ターゲットの種類
            pattern_name: 使用するパターンの名前
            context: Blenderコンテキスト
            execution_context: リネーム実行コンテキスト(オプション)

        Returns:
            バッチリネーム操作

        Raises:
            KeyError: パターンが存在しない場合
            ValueError: ターゲットの収集に失敗した場合
        """
        # 実行コンテキストの準備
        if execution_context is None:
            execution_context = RenameExecutionContext()
            execution_context.initialize()

        # パターンの取得
        pattern = self.pattern_registry.get_pattern(target_type, pattern_name)
        if not pattern:
            raise KeyError(f"パターンが見つかりません: {pattern_name} (タイプ: {target_type})")

        # ターゲットの収集
        targets = self.target_collector.collect(target_type, context)
        if not targets:
            raise ValueError(f"リネーム対象が見つかりません (タイプ: {target_type})")

        # バッチリネーム操作の作成
        batch_op = BatchRenameOperation(
            targets=targets,
            pattern=pattern,
            execution_context=execution_context
        )

        return batch_op

    def apply_element_updates(self, batch_op: BatchRenameOperation, updates: Dict) -> None:
        """
        バッチリネーム操作の要素を更新する

        Args:
            batch_op: バッチリネーム操作
            updates: 要素更新の辞書
        """
        batch_op.element_updates.update(updates)
        batch_op.pattern.update_elements(updates)

    def preview_batch(self, batch_op: BatchRenameOperation) -> List[RenameResult]:
        """
        バッチリネーム操作の実行結果をプレビューする
        実際のオブジェクト名は変更せず、シミュレーションのみを行う

        Args:
            batch_op: バッチリネーム操作

        Returns:
            リネーム結果のリスト
        """
        # シミュレーションモードを開始
        batch_op.execution_context.enter_simulation_mode()

        # 各ターゲットを処理
        results = []
        for target in batch_op.targets:
            result = self._process_target(
                target=target,
                pattern=batch_op.pattern,
                strategy=batch_op.strategy,
                execution_context=batch_op.execution_context
            )
            results.append(result)

        # 結果を記録
        batch_op.results = results
        batch_op.has_conflicts = any(not r.success for r in results)

        # シミュレーションモードを終了
        batch_op.execution_context.exit_simulation_mode()

        return results

    def execute_batch(self, batch_op: BatchRenameOperation) -> List[RenameResult]:
        """
        バッチリネーム操作を実行する
        実際のオブジェクト名を変更する

        Args:
            batch_op: バッチリネーム操作

        Returns:
            リネーム結果のリスト
        """
        # 実行準備
        batch_op.execution_context.reset()
        batch_op.execution_context.initialize()

        # 名前衝突を回避しながら、各ターゲットの提案名を生成
        results = []
        for target in batch_op.targets:
            result = self._process_target(
                target=target,
                pattern=batch_op.pattern,
                strategy=batch_op.strategy,
                execution_context=batch_op.execution_context
            )
            results.append(result)

        # 結果を記録
        batch_op.results = results
        batch_op.has_conflicts = any(not r.success for r in results)

        # 実際にリネームを適用
        self._apply_results(batch_op)

        return results

    def confirm_batch(self, batch_op: BatchRenameOperation) -> bool:
        """
        バッチリネーム操作の適用を確認する
        プレビュー後に呼び出され、実際のリネームを適用する

        Args:
            batch_op: バッチリネーム操作

        Returns:
            成功した場合はTrue
        """
        # プレビュー結果があることを確認
        if not batch_op.results:
            return False

        # 実行準備
        batch_op.execution_context.reset()
        batch_op.execution_context.initialize()

        # 以前に生成した結果を適用
        self._apply_results(batch_op)

        return True

    def _process_target(
        self,
        target: IRenameTarget,
        pattern: NamingPattern,
        strategy: str,
        execution_context: RenameExecutionContext
    ) -> RenameResult:
        """
        単一ターゲットのリネーム処理を行う

        Args:
            target: リネーム対象
            pattern: 使用する命名パターン
            strategy: 競合解決戦略
            execution_context: リネーム実行コンテキスト

        Returns:
            リネーム結果
        """
        result = RenameResult(target)

        try:
            # ターゲットの現在の名前を解析してパターン要素に反映
            pattern.parse_name(target.get_name())

            # 提案名を生成
            proposed_name = pattern.render_name()
            result.proposed_name = proposed_name

            # 競合を解決
            final_name = self.conflict_resolver.resolve_name_conflict(
                target=target,
                pattern=pattern,
                proposed_name=proposed_name,
                strategy=strategy
            )

            # シミュレーション名前空間を更新
            self.conflict_resolver.simulate_namespace_update(
                target=target,
                old_name=target.get_name(),
                new_name=final_name
            )

            result.final_name = final_name
            result.success = True

        except Exception as e:
            result.success = False
            result.message = str(e)

        return result

    def _apply_results(self, batch_op: BatchRenameOperation) -> None:
        """
        バッチリネーム操作の結果を実際に適用する

        Args:
            batch_op: バッチリネーム操作
        """
        # 成功した結果のみを適用
        for result in batch_op.results:
            if result.success:
                # 元の名前をバックアップ
                old_name = result.target.get_name()

                # ターゲットの名前を変更
                result.target.set_name(result.final_name)

                # 実際の名前空間を更新
                self.conflict_resolver.apply_namespace_update(
                    target=result.target,
                    old_name=old_name,
                    new_name=result.final_name
                )
