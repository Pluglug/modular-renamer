# RENAMABLE_OBJECT_TYPES = [
#     ("POSE_BONE", "Pose Bone", "Rename pose bones"),
#     ("OBJECT", "Object", "Rename objects"),
#     ("MATERIAL", "Material", "Rename materials"),
# ]

# Default separator options
SEPARATOR_ITEMS = [
    ("_", "Underscore", "_"),
    (".", "Dot", "."),
    ("-", "Dash", "-"),
    (" ", "Space", " "),
]

ELEMENT_TYPE_ITEMS = [
    ("text", "Text", "Normal text with predefined options"),
    # ("free_text", "Free Text", "Any text input"),  # 未実装
    ("position", "Position", "Positional indicators (L/R, Top/Bot, etc)"),
    ("numeric_counter", "Numeric Counter", "Numerical counter with formatting options"),
    (
        "alphabetic_counter",
        "Alphabetic Counter",
        "Alphabetic counter with formatting options",
    ),
    # ("date", "Date", "Date in various formats"),  # 未実装
    # ("regex", "RegEx", "Custom regular expression pattern"),  # 未実装
]

# Position enum items organized by axis
POSITION_ENUM_ITEMS = {
    "XAXIS": [
        ("L|R", "L / R", "Upper case L/R", 1),
        ("l|r", "l / r", "Lower case l/r", 2),
        ("LEFT|RIGHT", "LEFT / RIGHT", "Full word LEFT/RIGHT", 3),
        ("Left|Right", "Left / Right", "Full word Left/Right", 4),
        ("left|right", "left / right", "Full word left/right", 5),
    ],
    "YAXIS": [
        ("Top|Bot", "Top / Bot", "Upper case Top/Bot", 1),
    ],
    "ZAXIS": [
        ("Fr|Bk", "Fr / Bk", "Upper case Fr/Bk", 1),
    ],
}
