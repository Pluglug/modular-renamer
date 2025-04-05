from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from bpy.types import Context

from .conflict_resolver import ConflictResolver
from .element_registry import ElementRegistry
from .namespace import NamespaceCache
from .pattern import NamingPattern
from .pattern_system import PatternFacade, PatternCache, PatternFactory
from .rename_target import IRenameTarget, TargetCollector


class CollectionSource(Enum):
    """データ収集元"""

    VIEW3D = auto()
    OUTLINER = auto()
    NODE_EDITOR = auto()
    SEQUENCE_EDITOR = auto()
    FILE_BROWSER = auto()


@dataclass
class OperationScope:
    mode: CollectionSource = CollectionSource.VIEW3D
    # include_hidden: bool = False  # オプションアイディア
    # restrict_types: Optional[Set[Type]] = None  # 処理対象を限定するアイディア "OBJECT" など

    @classmethod
    def from_context(cls, context: Context) -> "OperationScope":
        # context.scene から文字列としてモードを取得
        mode_str = context.scene.rename_targets_mode

        # 文字列を CollectionSource Enum に変換
        try:
            collection_source_mode = CollectionSource[mode_str]
        except KeyError:
            # EnumProperty の定義と Scene の値が不一致の場合などのフォールバック
            print(
                f"警告: 無効なモード文字列 '{mode_str}' が検出されました。デフォルトの VIEW3D を使用します。"
            )
            collection_source_mode = CollectionSource.VIEW3D

        config = {
            # "mode": context.scene.rename_targets_mode, # 修正前
            "mode": collection_source_mode,  # 修正後
            # 将来的な設定の追加
            # "include_hidden": context.scene.rename_include_hidden,
            # "restrict_types": get_restricted_types_from_context(context),
        }
        return cls(**config)


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


class RenameContext:
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
        context: Context,
        scope: OperationScope,
    ):
        """
        リネームサービスを初期化する
        """
        self._target_collector = TargetCollector(context, scope)
        self._pattern_facade = PatternFacade(
            context,
            ElementRegistry.get_instance(),
            PatternCache.get_instance(),
        )
        self._conflict_resolver = ConflictResolver()

    def prepare_batch(
        self, target_type: str, pattern_name: str, context: Any
    ) -> RenameContext:
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
        return RenameContext(targets, pattern)

    def apply_element_updates(
        self, r_ctx: RenameContext, updates: Dict
    ) -> None:
        """
        バッチ操作の要素を更新する

        Args:
            r_ctx: バッチリネーム操作
            updates: 要素更新の辞書
        """
        r_ctx.element_updates.update(updates)
        r_ctx.pattern.update_elements(updates)

    def preview_batch(self, r_ctx: RenameContext) -> List[RenameResult]:
        """
        バッチリネーム操作のプレビューを生成する
        実際にオブジェクトは変更せず、結果のみを返す

        Args:
            r_ctx: バッチリネーム操作

        Returns:
            リネーム結果のリスト
        """
        results = []

        # 各ターゲットに対してリネームプレビューを生成
        for target in r_ctx.targets:
            # コピーを作成してパターンの状態を保存
            pattern_copy = r_ctx.pattern.clone()

            # ターゲットの処理
            result = self._process_target(
                target, pattern_copy, r_ctx.strategy, simulate=True
            )
            results.append(result)

        return results

    def execute_batch(self, r_ctx: RenameContext) -> List[RenameResult]:
        """
        バッチリネーム操作を実行する

        Args:
            r_ctx: バッチリネーム操作

        Returns:
            リネーム結果のリスト
        """
        r_ctx.results = []

        # フェーズ1: すべてのターゲットに対して名前を解決
        for target in r_ctx.targets:
            result = self._process_target(target, r_ctx.pattern, r_ctx.strategy)
            r_ctx.results.append(result)

            # IDまたはインデックスをキーとしてリザルトを保存
            target_key = str(target.get_namespace_key())
            r_ctx.pending_results[target_key] = result

        # フェーズ2: すべての名前解決が終わったら、実際にオブジェクトを更新
        self._apply_results(r_ctx)

        return r_ctx.results

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

    def _apply_results(self, r_ctx: RenameContext) -> None:
        """
        リネーム結果を実際のオブジェクトに適用する

        Args:
            r_ctx: バッチリネーム操作
        """
        # 名前変更を実行
        for result in r_ctx.results:
            if result.success:
                try:
                    # ターゲットの名前を更新
                    result.target.set_name(result.final_name)
                except Exception as e:
                    result.success = False
                    result.message = f"名前の適用中にエラーが発生しました: {str(e)}"
