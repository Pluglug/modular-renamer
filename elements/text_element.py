import random
import re
from typing import Optional, Tuple

from ..core.contracts.element import BaseElement, ElementConfig
from ..utils import logging, regex_utils

log = logging.get_logger(__name__)


class TextElement(BaseElement):
    """
    事前に定義された文字列の中から値を選択するテキスト要素
    """

    def __init__(self, element_config):
        super().__init__(element_config)
        self.items = getattr(element_config, "items", [])

    config_fields = {
        **BaseElement.config_fields,
        "items": list,
    }

    @classmethod
    def validate_config(cls, config: ElementConfig) -> Optional[str]:
        if error := super().validate_config(config):
            return error
        if not config.items:
            return "items は空ではないリストである必要があります"
        if not all(isinstance(item, str) for item in config.items):
            return "items の要素は全て文字列である必要があります"
        return None

    @regex_utils.add_separator_by_order
    @regex_utils.add_named_capture_group
    def _build_pattern(self) -> str:
        if not self.items:
            return ""

        escaped_items = [re.escape(item) for item in self.items]
        return "|".join(escaped_items)

    def generate_random_value(self) -> str:
        """Generate a random value from the available items"""
        if self.items:
            return random.choice(self.items)
        return ""


# class FreeTextElement(BaseElement):
#     """
#     フリーテキスト要素
#     """

#     def __init__(self, element_config):
#         super().__init__(element_config)
#         self.text = element_config.text

#     def standby(self):
#         super().standby()
#         # 常にコンパイル もしくはtextが変更された場合のみ
#         # やはりapply_settingsが必要か?
#         self.cache_invalidated = False

#     @regex_utils.add_separator_by_order
#     @regex_utils.add_named_capture_group
#     def _build_pattern(self) -> str:
#         return re.escape(self.text)
#         # TODO: Prefsを参照する方法を考える もしくはテキストの編集はEditModeのみ

#     def generate_random_value(self):
#         """Generate a random text value"""
#         if self.text:
#             return self.separator, self.text

#         # Generate a random word-like string
#         letters = "abcdefghijklmnopqrstuvwxyz"
#         length = random.randint(3, 8)
#         random_value = "".join(random.choice(letters) for _ in range(length))

#         return self.separator, random_value
