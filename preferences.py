# pyright: reportInvalidTypeForm=false
# DEPENDS_ON = ["props"]
import json
from typing import List, Optional

import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.app.translations import contexts as i18n_contexts

from .addon import ADDON_ID, prefs
from .core.constants import ELEMENT_TYPE_ITEMS, POSITION_ENUM_ITEMS, SEPARATOR_ITEMS
from .core.pattern.facade import PatternFacade
# from .ui.props import NamingPatternProperty
from .utils.logging import get_logger, LoggerPreferences

log = get_logger(__name__)


# FIXME: リロードの問題が解決しないため、Prefsにて定義
# ----------------------- Props -----------------------
class ModifiedPropMixin:
    def _update_modified(self):
        """自分と親のmodifiedフラグをTrueに"""
        if hasattr(self, "modified"):
            self.modified = True
        parent = getattr(self, "id_data", None)
        if parent and hasattr(parent, "_update_modified"):
            parent._update_modified()


def modified_updater():
    return lambda self, context: self._update_modified()


class NamingElementItemProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
    """Single item within a naming element's options"""

    name: StringProperty(
        name="Name",
        description="Name of this item",
        default="",
        update=modified_updater(),
    )


class NamingElementProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
    """Definition of a naming element"""

    id: StringProperty(
        name="ID", description="Unique identifier for this element", default=""
    )

    display_name: StringProperty(
        name="Display Name",
        description="User-friendly name for this element",
        default="",
        update=modified_updater(),
    )

    element_type: EnumProperty(
        name="Type",
        description="Type of this naming element",
        items=ELEMENT_TYPE_ITEMS,
        default="text",
        update=modified_updater(),
    )

    enabled: BoolProperty(
        name="Enabled",
        description="Whether this element is active",
        default=True,
        update=modified_updater(),
    )

    order: IntProperty(
        name="Order",
        description="Position in the naming sequence",
        default=0,
        min=0,
        update=modified_updater(),
    )

    # For all elements - separator selection
    separator: EnumProperty(
        name="Separator",
        description="Character used to separate this element from the next",
        items=SEPARATOR_ITEMS,
        default="_",
        translation_context=i18n_contexts.operator_default,
        update=modified_updater(),
    )

    # For text elements - predefined options
    items: CollectionProperty(
        type=NamingElementItemProperty,
        name="Items",
        description="Predefined text options for this element",
    )

    # For text elements - active item index
    active_item_index: IntProperty(
        name="Active Item Index", default=0, update=modified_updater()
    )

    def get_item_by_idx(self, idx: int) -> Optional[NamingElementItemProperty]:
        if not self.items:
            return None
        return self.items[idx]

    # For counter elements
    padding: IntProperty(
        name="Padding",
        description="Number of digits for counter (zero-padded)",
        default=2,
        min=1,
        max=10,
        update=modified_updater(),
    )

    # # For regex elements
    # pattern: StringProperty(
    #     name="Pattern",
    #     description="Regular expression pattern for matching",
    #     default="(.*)",
    #     update=modified_updater(),
    # )

    # # For date elements
    # date_format: StringProperty(
    #     name="Format",
    #     description="Date format string (strftime)",
    #     default="%Y%m%d",
    #     update=modified_updater(),
    # )

    # # For free text
    # default_text: StringProperty(
    #     name="Default Text",
    #     description="Default text to use",
    #     default="",
    #     update=modified_updater(),
    # )

    # For position elements
    xaxis_type: EnumProperty(
        name="X Axis Type",
        description="Type of X-axis position indicator",
        items=[(item[0], item[1], item[2]) for item in POSITION_ENUM_ITEMS["XAXIS"]],
        default="L|R",
        update=modified_updater(),
    )

    xaxis_enabled: BoolProperty(
        name="X Axis Enabled",
        description="Whether X-axis position is enabled",
        default=True,
        update=modified_updater(),
    )

    yaxis_enabled: BoolProperty(
        name="Y Axis Enabled",
        description="Whether Y-axis position is enabled",
        default=False,
        update=modified_updater(),
    )

    zaxis_enabled: BoolProperty(
        name="Z Axis Enabled",
        description="Whether Z-axis position is enabled",
        default=False,
        update=modified_updater(),
    )


class NamingPatternProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
    """A complete naming pattern for a specific object type"""

    id: StringProperty(
        name="ID", description="Unique identifier for this pattern", default=""
    )

    name: StringProperty(
        name="Name",
        description="User-friendly name for this pattern",
        default="",
        update=modified_updater(),
    )

    elements: CollectionProperty(
        type=NamingElementProperty,
        name="Elements",
        description="Elements that make up this naming pattern",
    )

    modified: BoolProperty(
        name="Modified",
        description="Whether the pattern has been modified",
        default=True,
    )

    active_element_index: IntProperty(name="Active Element Index", default=0)

    def get_element_by_id(self, id: str) -> Optional[NamingElementProperty]:
        if not self.elements:
            return None
        for elem in self.elements:
            if elem.id == id:
                return elem
        return None

    # Add or remove an element
    def add_element(self, id, element_type, display_name):
        self.modified = True
        elem = self.elements.add()
        elem.id = id
        elem.element_type = element_type
        elem.display_name = display_name
        elem.order = len(self.elements) - 1
        return elem

    def remove_element(self, index):
        self.modified = True
        if 0 <= index < len(self.elements):
            removed_order = self.elements[index].order
            self.elements.remove(index)

            # 削除されたエレメントよりも高い順序値を持つエレメントの順序を調整
            for elem in self.elements:
                if elem.order > removed_order:
                    elem.order -= 1

    def move_element_up(self, index):
        """エレメントを上に移動（順序を前に）"""
        self.modified = True
        if 0 < index < len(self.elements):
            # 現在のエレメントと1つ前のエレメントの順序値を取得
            current_elem = self.elements[index]
            prev_elem = self.elements[index - 1]

            # 順序値を交換
            temp_order = current_elem.order
            current_elem.order = prev_elem.order
            prev_elem.order = temp_order

            # UIリストの表示順序に反映するために、コレクション内の要素も交換
            self.elements.move(index, index - 1)
            self.active_element_index = index - 1

    def move_element_down(self, index):
        """エレメントを下に移動（順序を後ろに）"""
        self.modified = True
        if 0 <= index < len(self.elements) - 1:
            # 現在のエレメントと1つ後のエレメントの順序値を取得
            current_elem = self.elements[index]
            next_elem = self.elements[index + 1]

            # 順序値を交換
            temp_order = current_elem.order
            current_elem.order = next_elem.order
            next_elem.order = temp_order

            # UIリストの表示順序に反映するために、コレクション内の要素も交換
            self.elements.move(index, index + 1)
            self.active_element_index = index + 1


# ----------------------- End Props -----------------------


def update_edit_mode(self, context):
    """パターンの編集モードが変更されたときの処理

    Args:
        self: ModularRenamerPreferences
        context: bpy.types.Context
    """
    if not context:
        return

    if self.edit_mode:
        log.debug("Enter edit mode")
    else:
        log.debug("Exit edit mode")
        try:
            # 変更されたパターンを取得
            modified_patterns = self.get_modified_patterns()
            if not modified_patterns:
                return

            pf = PatternFacade(context)
            pf.synchronize_patterns()

        except Exception as e:
            log.error(f"パターンの同期中にエラーが発生しました: {e}", exc_info=True)


class ModularRenamerPreferences(AddonPreferences):
    """Addon preferences for ModularRenamer"""

    bl_idname = ADDON_ID

    logger_prefs: PointerProperty(type=LoggerPreferences)

    # Whether the pattern is in edit mode
    edit_mode: BoolProperty(
        name="Edit Mode",
        description="Whether the pattern is in edit mode",
        default=False,
        update=update_edit_mode,
    )

    # Collection of all naming patterns
    patterns: CollectionProperty(
        type=NamingPatternProperty,
        name="Naming Patterns",
        description="All available naming patterns",
    )

    def get_modified_patterns(self) -> List[NamingPatternProperty]:
        return [pattern for pattern in self.patterns if pattern.modified]

    # Currently selected pattern
    active_pattern_index: IntProperty(name="Active Pattern", default=0)

    def get_active_pattern(self) -> Optional[NamingPatternProperty]:
        # アクティブインデックスが範囲内か確認
        if not self.patterns or not (
            0 <= self.active_pattern_index < len(self.patterns)
        ):
            # 範囲外なら最初のパターンを選択（またはNone）
            if self.patterns:
                self.active_pattern_index = 0
                return self.patterns[0]
            else:
                return None
        return self.patterns[self.active_pattern_index]

    def add_pattern(self, id, name):
        pattern = self.patterns.add()
        pattern.id = id
        pattern.name = name
        return pattern

    def remove_pattern(self, index):
        if 0 <= index < len(self.patterns):
            # アクティブインデックスを調整
            if self.active_pattern_index >= index:
                self.active_pattern_index = max(0, self.active_pattern_index - 1)
            self.patterns.remove(index)

    # Export patterns to JSON
    def export_patterns(self, filepath):
        data = []
        for pattern in self.patterns:
            pattern_data = {
                "id": pattern.id,
                "name": pattern.name,
                "elements": [],
            }

            for element in pattern.elements:
                element_config = {
                    "id": element.id,
                    "display_name": element.display_name,
                    "type": element.element_type,
                    "enabled": element.enabled,
                    "order": element.order,
                    "separator": element.separator,
                }

                # Add type-specific properties
                if element.element_type == "text":
                    element_config["items"] = [item.name for item in element.items]
                elif element.element_type == "numeric_counter":
                    element_config["padding"] = element.padding
                # elif element.element_type == "regex":
                #     element_config["pattern"] = element.pattern
                # elif element.element_type == "date":
                #     element_config["date_format"] = element.date_format
                # elif element.element_type == "free_text":
                #     element_config["default_text"] = element.default_text
                elif element.element_type == "position":
                    # PositionElement の設定を正しくエクスポート
                    element_config["xaxis_type"] = element.xaxis_type
                    element_config["xaxis_enabled"] = element.xaxis_enabled
                    element_config["yaxis_enabled"] = element.yaxis_enabled
                    element_config["zaxis_enabled"] = element.zaxis_enabled

                pattern_data["elements"].append(element_config)

            data.append(pattern_data)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            log.info(f"Patterns exported to {filepath}")
            return True
        except Exception as e:
            log.error(f"Error exporting patterns: {e}", exc_info=True)
            return False

    # Import patterns from JSON
    def import_patterns(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Clear existing patterns before import
            self.patterns.clear()
            self.active_pattern_index = 0  # インデックスリセット

            for pattern_data in data:
                pattern = self.add_pattern(
                    pattern_data.get(
                        "id", f"imported_pattern_{len(self.patterns)}"
                    ),  # IDフォールバック
                    pattern_data.get("name", "Imported Pattern"),  # Nameフォールバック
                )

                for element_config in pattern_data.get("elements", []):
                    elem_id = element_config.get("id", f"elem_{len(pattern.elements)}")
                    elem_type = element_config.get("type", "text")  # Typeフォールバック
                    elem_disp_name = element_config.get(
                        "display_name", "Imported Element"
                    )

                    element = pattern.add_element(
                        elem_id,
                        elem_type,
                        elem_disp_name,
                    )

                    element.enabled = element_config.get("enabled", True)
                    element.order = element_config.get(
                        "order", len(pattern.elements) - 1
                    )
                    element.separator = element_config.get("separator", "_")

                    # Set type-specific properties safely
                    if element.element_type == "text" and "items" in element_config:
                        element.items.clear()  # Clear default items if any
                        for item_name in element_config.get("items", []):
                            item = element.items.add()
                            item.name = item_name

                    elif (
                        element.element_type == "numeric_counter"
                        and "padding" in element_config
                    ):
                        # Make sure padding has a valid value
                        padding_val = element_config.get("padding", 2)
                        element.padding = max(
                            1, min(int(padding_val), 10)
                        )  # Clamp between 1 and 10

                    # elif element.element_type == "regex" and "pattern" in element_config:
                    #     element.pattern = element_config.get("pattern", "(.*)")

                    # elif element.element_type == "date" and "date_format" in element_config:
                    #     element.date_format = element_config.get("date_format", "%Y%m%d")

                    # elif element.element_type == "free_text" and "default_text" in element_config:
                    #     element.default_text = element_config.get("default_text", "")

                    elif element.element_type == "position":
                        element.xaxis_type = element_config.get("xaxis_type", "L|R")
                        element.xaxis_enabled = element_config.get(
                            "xaxis_enabled", True
                        )
                        element.yaxis_enabled = element_config.get(
                            "yaxis_enabled", False
                        )
                        element.zaxis_enabled = element_config.get(
                            "zaxis_enabled", False
                        )

            log.info(f"Patterns imported from {filepath}")
            return True

        except FileNotFoundError:
            log.error(f"Import file not found: {filepath}")
            return False
        except json.JSONDecodeError:
            log.error(f"Error decoding JSON from file: {filepath}")
            return False
        except Exception as e:
            log.error(f"Error importing patterns: {e}", exc_info=True)
            # インポート失敗時も部分的に読み込まれたパターンは残る可能性がある
            return False

    def create_default_patterns(self):
        # デフォルトパターンが既に存在するかチェック（ID基準が望ましい）
        existing_ids = {p.id for p in self.patterns}
        if "pose_bone_default" in existing_ids:
            log.info(
                "Default pattern 'pose_bone_default' already exists. Skipping creation."
            )
            return False  # 作成しなかったことを示す

        log.info("Creating default patterns...")
        try:
            # Create a default pattern for pose bones
            bone_pattern = self.add_pattern("pose_bone_default", "Default Bone Pattern")

            # Add prefix element
            prefix = bone_pattern.add_element("prefix", "text", "Prefix")
            prefix.items.clear()
            for name in ["CTRL", "DEF", "MCH", "ORG", "DRV", "TRG", "PROP"]:
                item = prefix.items.add()
                item.name = name

            # Add middle element
            middle = bone_pattern.add_element("middle", "text", "Middle")
            middle.items.clear()
            for name in [
                "Bone",
                "Root",
                "Spine",
                "Chest",
                "Torso",
                "Hips",
                "Tail",
                "Neck",
                "Head",
                "Shoulder",
                "Arm",
                "Elbow",
                "ForeArm",
                "Hand",
                "InHand",
                "Finger",
                "UpLeg",
                "Leg",
                "Shin",
                "Foot",
                "Knee",
                "Toe",
            ]:
                item = middle.items.add()
                item.name = name

            # Add finger element
            finger = bone_pattern.add_element("finger", "text", "Finger")
            finger.items.clear()
            for name in ["Finger", "Thumb", "Index", "Middle", "Ring", "Pinky"]:
                item = finger.items.add()
                item.name = name

            # Add suffix element
            suffix = bone_pattern.add_element("suffix", "text", "Suffix")
            suffix.items.clear()
            for name in [
                "Base",
                "Tweak",
                "Pole",
                "IK",
                "FK",
                "Roll",
                "Rot",
                "Loc",
                "Scale",
                "INT",
            ]:
                item = suffix.items.add()
                item.name = name

            # Add counter element
            counter = bone_pattern.add_element("counter", "numeric_counter", "Counter")
            counter.padding = 2
            counter.separator = "."  # 区切り文字を'.'に変更（一般的）

            # Add position element
            position = bone_pattern.add_element("position", "position", "Position")
            position.separator = "."
            position.xaxis_type = "L|R"
            position.xaxis_enabled = True
            position.yaxis_enabled = False
            position.yaxis_enabled = False
            # Z軸の設定（デフォルトで無効だが、設定可能にする）
            position.yaxis_enabled = False
            # Z軸の設定（デフォルトで無効だが、設定可能にする）
            position.zaxis_enabled = False

            log.info("Default patterns created successfully.")
            return True  # 作成成功
        except Exception as e:
            log.error(f"Error creating default patterns: {e}", exc_info=True)
            # 作成中にエラーが発生した場合、部分的に作成されたパターンが残る可能性がある
            # 必要であれば、ここでロールバック処理を追加する
            return False  # 作成失敗

    def draw(self, context):
        layout = self.layout
        LoggerPreferences.draw(self, layout)


def register():

    # デフォルトパターンの作成
    pr = prefs()
    if not hasattr(pr, "patterns") or not pr.patterns:
        pr.create_default_patterns()
    if not hasattr(pr, "active_pattern_index") or not pr.active_pattern_index:
        pr.active_pattern_index = 0
