import re


def to_snake_case(name: str) -> str:
    """
    Convert camelCase to snake_case

    Examples:
        >>> to_snake_case("BlenderCounter")     # "blender_counter"
        >>> to_snake_case("XMLParser")          # "xml_parser"
        >>> to_snake_case("blenderCounter")     # "blender_counter"
        >>> to_snake_case("Blender_Counter")    # "blender_counter"
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def is_pascal_case(name: str) -> bool:
    """
    より厳密なパスカルケースチェック

    条件：
    1. 先頭が大文字
    2. 続く文字は小文字または大文字
    3. 連続する大文字は許可しない（略語を除く）
    4. 数字、アンダースコア、その他の文字は不許可

    Examples:
        >>> is_pascal_case("BlenderCounter")     # True
        >>> is_pascal_case("XMLParser")          # True  (略語OK)
        >>> is_pascal_case("blenderCounter")     # False (先頭小文字)
        >>> is_pascal_case("Blender_Counter")    # False (アンダースコア)
        >>> is_pascal_case("BLENDERCounter")     # False (連続大文字)
        >>> is_pascal_case("Blender2Counter")    # False (数字)
    """
    if not name or len(name) < 2:
        return False

    # 先頭が大文字で始まるか
    if not name[0].isupper():
        return False

    # アルファベットのみか
    if not name.isalpha():
        return False

    # 連続する大文字をチェック（略語は例外）
    upper_count = 0
    prev_is_upper = True  # 最初の文字は大文字なので True で開始

    for c in name[1:]:
        is_upper = c.isupper()

        if is_upper:
            upper_count += 1
            if not prev_is_upper:  # 新しい単語の開始
                upper_count = 1
        else:
            if prev_is_upper and upper_count > 1:  # 略語の終わり
                if upper_count > 5:  # 略語が長すぎる
                    return False
            upper_count = 0

        prev_is_upper = is_upper

    # 最後の文字が大文字で終わる場合のチェック
    if prev_is_upper and upper_count > 5:
        return False

    return True
