from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .conflict_resolver import ConflictResolver
from .namespace import NamespaceManager
from .pattern import NamingPattern
from .pattern_registry import PatternRegistry
from .rename_target import IRenameTarget
from .target_collector import TargetCollector


@dataclass
class RenameResult:
    """
    リネーム処理の結果
    """

    target: IRenameTarget
    original_name: str
    proposed_name: str
    final_name: str
    success: bool = False
    message: str = ""

    def __repr__(self) -> str:
        return f"RenameResult(target={self.target.get_name()}, original={self.original_name}, final={self.final_name}, success={self.success})"


class BatchRenameOperation:
    """
    一括リネーム操作を管理するクラス
    """

    def __init__(
        self,
        targets: List[IRenameTarget],
        pattern: NamingPattern,
        strategy: str = "counter",
    ):
        """
        一括リネーム操作を初期化する

        Args:
            targets: リネーム対象のリスト
            pattern: 使用する命名パターン
            strategy: 競合解決戦略（デフォルト: "counter"）
        """
        self.targets = targets
        self.pattern = pattern
        self.strategy = strategy
        self.element_updates: Dict = {}
        self.results: List[RenameResult] = []
        self.pending_results: Dict[str, RenameResult] = {}
        self.has_conflicts = False

    def get_result_summary(self) -> str:
        """
        リネーム結果のサマリーを取得する

        Returns:
            サマリー文字列
        """
        success_count = sum(1 for result in self.results if result.success)
        return f"{success_count}/{len(self.targets)}件のリネームが成功しました"


class RenameService:
    """
    ターゲットの一括リネームサービス
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
        self, target_type: str, pattern_name: str, context: Any
    ) -> BatchRenameOperation:
        """
        一括リネーム操作を準備する

        Args:
            target_type: ターゲットタイプ
            pattern_name: 使用するパターンの名前
            context: Blenderコンテキスト

        Returns:
            バッチリネーム操作

        Raises:
            KeyError: パターンが存在しない場合
            ValueError: ターゲットが見つからない場合
        """
        # パターンを取得
        pattern = self.pattern_registry.get_pattern(target_type, pattern_name)
        if not pattern:
            raise KeyError(
                f"パターンが見つかりません: {pattern_name} (タイプ: {target_type})"
            )

        # ターゲットを収集
        targets = self.target_collector.collect(target_type, context)
        if not targets:
            raise ValueError(f"リネーム対象が見つかりません (タイプ: {target_type})")

        # バッチ操作を作成
        return BatchRenameOperation(targets, pattern)

    def apply_element_updates(
        self, batch_op: BatchRenameOperation, updates: Dict
    ) -> None:
        """
        バッチ操作の要素を更新する

        Args:
            batch_op: バッチリネーム操作
            updates: 要素更新の辞書
        """
        batch_op.element_updates.update(updates)
        batch_op.pattern.update_elements(updates)

    def preview_batch(self, batch_op: BatchRenameOperation) -> List[RenameResult]:
        """
        バッチリネーム操作のプレビューを生成する
        実際にオブジェクトは変更せず、結果のみを返す

        Args:
            batch_op: バッチリネーム操作

        Returns:
            リネーム結果のリスト
        """
        results = []

        # 各ターゲットに対してリネームプレビューを生成
        for target in batch_op.targets:
            # コピーを作成してパターンの状態を保存
            pattern_copy = batch_op.pattern.clone()

            # ターゲットの処理
            result = self._process_target(
                target, pattern_copy, batch_op.strategy, simulate=True
            )
            results.append(result)

        return results

    def execute_batch(self, batch_op: BatchRenameOperation) -> List[RenameResult]:
        """
        バッチリネーム操作を実行する

        Args:
            batch_op: バッチリネーム操作

        Returns:
            リネーム結果のリスト
        """
        batch_op.results = []

        # フェーズ1: すべてのターゲットに対して名前を解決
        for target in batch_op.targets:
            result = self._process_target(target, batch_op.pattern, batch_op.strategy)
            batch_op.results.append(result)

            # IDまたはインデックスをキーとしてリザルトを保存
            target_key = str(target.get_namespace_key())
            batch_op.pending_results[target_key] = result

        # フェーズ2: すべての名前解決が終わったら、実際にオブジェクトを更新
        self._apply_results(batch_op)

        return batch_op.results

    def _process_target(
        self,
        target: IRenameTarget,
        pattern: NamingPattern,
        strategy: str,
        simulate: bool = False,
    ) -> RenameResult:
        """
        単一ターゲットのリネーム処理を実行する

        Args:
            target: リネーム対象
            pattern: 使用するパターン
            strategy: 競合解決戦略
            simulate: シミュレーションモード（True: オブジェクトを変更しない）

        Returns:
            リネーム結果
        """
        # 現在の名前を取得
        original_name = target.get_name()

        # パターンにターゲットの現在の名前を解析させる（可能であれば）
        try:
            pattern.parse_name(original_name)
        except Exception as e:
            # パースエラーは無視して続行（新規名前のみ使用）
            pass

        # パターンから提案名を生成
        proposed_name = pattern.render_name()

        # 結果オブジェクトを初期化
        result = RenameResult(
            target=target,
            original_name=original_name,
            proposed_name=proposed_name,
            final_name="",
            success=False,
        )

        if not proposed_name:
            result.message = "パターンからの名前生成に失敗しました"
            return result

        # 競合を解決
        try:
            final_name = self.conflict_resolver.resolve_name_conflict(
                target, pattern, proposed_name, strategy
            )

            if not final_name:
                result.message = "名前競合の解決に失敗しました"
                return result

            # 結果を設定
            result.final_name = final_name
            result.success = True

        except Exception as e:
            result.message = f"リネーム処理中にエラーが発生しました: {str(e)}"

        return result

    def _apply_results(self, batch_op: BatchRenameOperation) -> None:
        """
        リネーム結果を実際のオブジェクトに適用する

        Args:
            batch_op: バッチリネーム操作
        """
        # 名前変更を実行
        for result in batch_op.results:
            if result.success:
                try:
                    # ターゲットの名前を更新
                    result.target.set_name(result.final_name)
                except Exception as e:
                    result.success = False
                    result.message = f"名前の適用中にエラーが発生しました: {str(e)}"
