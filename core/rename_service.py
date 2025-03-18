from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .conflict_resolver import ConflictResolver
from .namespace import NamespaceManager
from .pattern import NamingPattern
from .pattern_registry import PatternRegistry
from .rename_target import IRenameTarget


class RenameContext:
    """
    リネーム操作のコンテキスト
    """

    def __init__(self, target: IRenameTarget, pattern: NamingPattern):
        """
        リネームコンテキストを初期化する

        Args:
            target: リネーム対象
            pattern: 使用する命名パターン
        """
        self.target = target
        self.pattern = pattern
        self.original_name = target.get_name()
        self.proposed_name = ""
        self.final_name = ""
        self.conflict_resolution = None
        self.message = ""  # エラーメッセージなど

    def __repr__(self) -> str:
        return f"RenameContext(target={self.target.get_name()}, original={self.original_name}, proposed={self.proposed_name}, final={self.final_name})"


class RenameService:
    """
    ターゲットのリネームサービス
    """

    def __init__(
        self,
        pattern_registry: PatternRegistry,
        conflict_resolver: ConflictResolver,
    ):
        """
        リネームサービスを初期化する

        Args:
            pattern_registry: PatternRegistryインスタンス
            conflict_resolver: ConflictResolverインスタンス
        """
        self.pattern_registry = pattern_registry
        self.conflict_resolver = conflict_resolver

    def prepare(self, target: IRenameTarget, pattern_name: str) -> RenameContext:
        """
        リネーム操作を準備する

        Args:
            target: リネーム対象
            pattern_name: 使用するパターンの名前

        Returns:
            リネームコンテキスト

        Raises:
            KeyError: パターンが存在しない場合
        """
        target_type = target.target_type
        pattern = self.pattern_registry.get_pattern(target_type, pattern_name)

        context = RenameContext(target, pattern)

        # ターゲットの現在の名前を解析
        pattern.parse_name(target.get_name())

        # 提案名を生成
        context.proposed_name = pattern.render_name()

        return context

    def update_elements(self, context: RenameContext, updates: Dict) -> RenameContext:
        """
        リネームコンテキストの要素を更新する

        Args:
            context: リネームコンテキスト
            updates: 要素更新の辞書

        Returns:
            更新されたコンテキスト
        """
        # パターン要素を更新
        context.pattern.update_elements(updates)

        # 提案名を更新
        context.proposed_name = context.pattern.render_name()

        return context

    def execute(self, context: RenameContext, strategy: str) -> bool:
        """
        リネーム操作を実行する

        Args:
            context: リネームコンテキスト
            strategy: 競合解決戦略

        Returns:
            成功した場合はTrue
        """
        if not context.proposed_name:
            return False

        # 競合を解決
        context.final_name = self.conflict_resolver.resolve(
            context.target, context.proposed_name, strategy
        )

        if not context.final_name:
            return False

        # ターゲットの名前を更新
        old_name = context.target.get_name()
        context.target.set_name(context.final_name)
