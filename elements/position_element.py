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
        """Build pattern for position indicators with appropriate separator based on order"""
        if not self.position_values:
            return f"(?P<{self.id}>)"

        # 位置値をエスケープして正規表現パターンを構築
        escaped_positions = [re.escape(pos) for pos in self.position_values]
        positions_pattern = "|".join(escaped_positions)

        # 順序に基づいてセパレーターを適用
        sep = re.escape(self.separator)

        if self.order == 0:  # 最初の要素
            return f"(?P<{self.id}>{positions_pattern}){sep}?"
        else:  # 順序が1以上の要素
            return f"{sep}?(?P<{self.id}>{positions_pattern})"

    def generate_random_value(self):
        """Generate a random position value"""
        if self.position_values:
            return random.choice(self.position_values)
        return "L"  # デフォルト値
