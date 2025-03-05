import random
import re
from typing import List, Tuple

from ..core.elements import BaseElement
from ..utils import logging, regex_utils

log = logging.get_logger(__name__)


class TextElement(BaseElement):
    """
    事前に定義された文字列の中から値を選択するテキスト要素
    """

    def __init__(self, element_data):
        super().__init__(element_data)
        self.items = [item.name for item in element_data.items]

    @regex_utils.add_separator_by_order
    @regex_utils.add_named_capture_group
    def _build_pattern(self) -> str:
        if not self.items:
            return ""

        escaped_items = [re.escape(item) for item in self.items]
        return "|".join(escaped_items)

    def generate_random_value(self) -> Tuple[str, str]:
        """Generate a random value from the available items"""
        if self.items:
            return self.separator, random.choice(self.items)
        return None, None


# class FreeTextElement(BaseElement):
#     """
#     フリーテキスト要素
#     """

#     def __init__(self, element_data):
#         super().__init__(element_data)
#         self.text = element_data.text

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
