from abc import ABC, abstractmethod
from typing import Dict, List

from bpy.types import Context

from .rename_target import IRenameTarget


class CollectionStrategy(ABC):
    """
    ターゲット収集戦略のインターフェース
    """

    @abstractmethod
    def collect(self, context: Context) -> List[IRenameTarget]:
        """
        コンテキストからターゲットを収集する

        Args:
            context: bpy.context

        Returns:
            ターゲットのリスト
        """
        pass


class TargetCollector:
    """
    登録された戦略に基づいてターゲットを収集する
    """

    def __init__(self):
        """
        ターゲットコレクターを初期化する
        """
        self._strategies: Dict[str, CollectionStrategy] = {}  # {type_name: strategy}

    def register_strategy(self, target_type: str, strategy: CollectionStrategy) -> None:
        """
        ターゲットタイプの収集戦略を登録する

        Args:
            target_type: ターゲットのタイプ
            strategy: 収集戦略
        """
        self._strategies[target_type] = strategy

    def collect(self, target_type: str, context: Context) -> List[IRenameTarget]:
        """
        特定のタイプのターゲットを収集する

        Args:
            target_type: 収集するターゲットのタイプ
            context: bpy.context

        Returns:
            ターゲットのリスト

        Raises:
            KeyError: ターゲットタイプの戦略が登録されていない場合
        """
        if target_type not in self._strategies:
            raise KeyError(
                f"ターゲットタイプの収集戦略が登録されていません: {target_type}"
            )

        strategy = self._strategies[target_type]
        return strategy.collect(context)
