# pyright: reportInvalidTypeForm=false
# DEPENDS_ON = ["property_groups"]
import json
from typing import List, Optional

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, IntProperty, PointerProperty,
                       StringProperty)

from .addon import ADDON_ID, prefs
from .core.constants import (ELEMENT_TYPE_ITEMS, POSITION_ENUM_ITEMS,
                             SEPARATOR_ITEMS)
from .core.pattern_system import PatternFacade
from .property_groups import (NamingElementItemProperty, NamingElementProperty,
                              NamingPatternProperty, modified_updater)
from .utils.logging import AddonLoggerPreferencesMixin, get_logger

log = get_logger(__name__)


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

            # PatternFacadeのインスタンスを再利用
            pf = getattr(self, "_pattern_facade", None)
            if pf is None:
                pf = PatternFacade(context)
                self._pattern_facade = pf

            # 同期処理を実行
            pf.synchronize_patterns()

        except Exception as e:
            log.error(f"パターンの同期中にエラーが発生しました: {e}")
            # エラーが発生した場合は編集モードを維持
            self.edit_mode = True


class ModularRenamerPreferences(
    AddonLoggerPreferencesMixin,
    bpy.types.AddonPreferences,
):
    """Addon preferences for ModularRenamer"""

    bl_idname = ADDON_ID

    # Whether the pattern is in edit mode
    edit_mode: BoolProperty(
        name="Edit Mode",
        description="Whether the pattern is in edit mode",
        default=False,
        # update=lambda self, context: update_edit_mode(self, context),
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
        if not self.patterns:
            return None
        return self.patterns[self.active_pattern_index]

    def add_pattern(self, id, name):
        pattern = self.patterns.add()
        pattern.id = id
        pattern.name = name
        return pattern

    def remove_pattern(self, index):
        if 0 <= index < len(self.patterns):
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
                    element_config["position_type"] = element.position_type

                pattern_data["elements"].append(element_config)

            data.append(pattern_data)

        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

        return True

    # Import patterns from JSON
    def import_patterns(self, filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Clear existing patterns
            self.patterns.clear()

            for pattern_data in data:
                pattern = self.add_pattern(
                    pattern_data["id"],
                    pattern_data["name"],
                )

                for element_config in pattern_data["elements"]:
                    element = pattern.add_element(
                        element_config["id"],
                        element_config["type"],
                        element_config["display_name"],
                    )

                    element.enabled = element_config.get("enabled", True)
                    element.order = element_config.get("order", 0)
                    element.separator = element_config.get("separator", "_")

                    # Set type-specific properties
                    if element.element_type == "text" and "items" in element_config:
                        for item_name in element_config["items"]:
                            item = element.items.add()
                            item.name = item_name

                    if (
                        element.element_type == "numeric_counter"
                        and "padding" in element_config
                    ):
                        element.padding = element_config["padding"]

                    if element.element_type == "regex" and "pattern" in element_config:
                        element.pattern = element_config["pattern"]

                    if (
                        element.element_type == "date"
                        and "date_format" in element_config
                    ):
                        element.date_format = element_config["date_format"]

                    if (
                        element.element_type == "free_text"
                        and "default_text" in element_config
                    ):
                        element.default_text = element_config["default_text"]

                    if (
                        element.element_type == "position"
                        and "position_type" in element_config
                    ):
                        element.position_type = element_config["position_type"]

            return True

        except Exception as e:
            print(f"Error importing patterns: {e}")
            return False

    def create_default_patterns(self):
        # Clear existing patterns
        if self.patterns:
            self.patterns.clear()

        # Create a default pattern for pose bones
        bone_pattern = self.add_pattern("pose_bone_default", "Default Bone Pattern")

        # Add prefix element
        prefix = bone_pattern.add_element("prefix", "text", "Prefix")
        for name in ["CTRL", "DEF", "MCH", "ORG", "DRV", "TRG", "PROP"]:
            item = prefix.items.add()
            item.name = name

        # Add middle element
        middle = bone_pattern.add_element("middle", "text", "Middle")
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
        for name in ["Finger", "Thumb", "Index", "Middle", "Ring", "Pinky"]:
            item = finger.items.add()
            item.name = name

        # Add suffix element
        suffix = bone_pattern.add_element("suffix", "text", "Suffix")
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
        counter.separator = "-"

        # Add position element
        position = bone_pattern.add_element("position", "position", "Position")
        position.separator = "."
        # X軸の設定
        position.xaxis_type = "L|R"
        position.xaxis_enabled = True
        # Y軸の設定（デフォルトで無効だが、設定可能にする）
        position.yaxis_enabled = False
        # Z軸の設定（デフォルトで無効だが、設定可能にする）
        position.zaxis_enabled = False

        return True

    def draw(self, context):
        layout = self.layout
        self.draw_logger_preferences(layout)


def register():

    # デフォルトパターンの作成
    pr = prefs()
    if not hasattr(pr, "patterns") or not pr.patterns:
        pr.create_default_patterns()
    if not hasattr(pr, "active_pattern_index") or not pr.active_pattern_index:
        pr.active_pattern_index = 0
