from dataclasses import dataclass
from enum import Enum
from typing import List

from ..contracts.target import IRenameTarget
from ..pattern.model import NamingPattern


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
