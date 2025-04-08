import random
import re
from typing import Optional

from ..core.constants import POSITION_ENUM_ITEMS
from ..core.element import BaseElement, ElementConfig
from ..utils import logging

log = logging.get_logger(__name__)


class PositionElement(BaseElement):
    """
    位置要素
    """

    def __init__(self, element_config):
        super().__init__(element_config)

        # X軸の値を取得
        self.xaxis_type = element_config.xaxis_type
        self.xaxis_enabled = element_config.xaxis_enabled
        self.xaxis_values = (
            self.xaxis_type.split("|") if self.xaxis_type and self.xaxis_enabled else []
        )

        # Y軸の値を取得
        self.yaxis_enabled = element_config.yaxis_enabled
        self.yaxis_values = (
            POSITION_ENUM_ITEMS["YAXIS"][0][0].split("|") if self.yaxis_enabled else []
        )

        # Z軸の値を取得
        self.zaxis_enabled = element_config.zaxis_enabled
        self.zaxis_values = (
            POSITION_ENUM_ITEMS["ZAXIS"][0][0].split("|") if self.zaxis_enabled else []
        )

        # すべての可能な位置値を組み合わせる
        self.position_values = []
        if self.xaxis_enabled and self.xaxis_values:
            self.position_values.extend(self.xaxis_values)
        if self.yaxis_enabled and self.yaxis_values:
            self.position_values.extend(self.yaxis_values)
        if self.zaxis_enabled and self.zaxis_values:
            self.position_values.extend(self.zaxis_values)

    config_fields = {
        **BaseElement.config_fields,
        "xaxis_type": str,
        "xaxis_enabled": bool,
        "yaxis_enabled": bool,
        "zaxis_enabled": bool,
    }

    @classmethod
    def validate_config(cls, config: ElementConfig) -> Optional[str]:
        if error := super().validate_config(config):
            return error
        if not (config.xaxis_type or config.yaxis_type or config.zaxis_type):
            return "xaxis_type, yaxis_type, zaxis_type のいずれかが必要です"
        return None

    def _build_pattern(self):
        """Build pattern for position indicators for parsing"""
        if not self.position_values:
            log.warning(f"No position values defined for element {self.id}")
            # マッチしないように lookahead assertion を使う (絶対にマッチしないパターン)
            return "(?!.)"

        # 位置値をエスケープして正規表現パターンを構築
        escaped_positions = [re.escape(pos) for pos in self.position_values]
        positions_pattern = "|".join(escaped_positions)

        # 値のみをキャプチャする名前付きグループ
        value_capture = f"(?P<{self.id}>{positions_pattern})"

        # orderに基づいてセパレーターを含めるか決定
        if self.order == 0:
            # 先頭要素: セパレータなしで値のみマッチ
            # 後続のセパレータは次の要素のパターンに含まれる想定
            return value_capture
        else:
            # 2番目以降の要素: 先行するセパレータ + 値
            # セパレータは non-capturing group (?:...) にして、位置の値だけをキャプチャ
            sep = re.escape(self.separator)
            # セパレータがオプショナルでないことに注意 (前の要素がある前提のため)
            return f"(?:{sep}){value_capture}"

    def generate_random_value(self):
        """Generate a random position value"""
        if self.position_values:
            return random.choice(self.position_values)
        return "L"  # デフォルト値

    def get_value_by_idx(self, index: int) -> Optional[str]:
        """指定されたインデックスに対応する位置の値を取得する"""
        # get_value_by_idx が呼ばれるのはUIからで、その時点での有効な軸の値リストが必要
        combined_values = []
        if self.xaxis_enabled and self.xaxis_values:
            combined_values.extend(self.xaxis_values)
        if self.yaxis_enabled and self.yaxis_values:
            combined_values.extend(self.yaxis_values)
        if self.zaxis_enabled and self.zaxis_values:
            combined_values.extend(self.zaxis_values)

        if 0 <= index < len(combined_values):
            return combined_values[index]
        log.warning(
            f"Index {index} is out of range for position values: {combined_values}"
        )
        return None
