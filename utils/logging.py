import logging
import logging.handlers
import os
import sys
import traceback
import datetime
from collections import deque
from enum import Enum

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty, IntProperty
from bpy.types import Operator, AddonPreferences

# ANSIカラーコード
COLORS = {
    "RESET": "\033[0m",
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[31;1m",  # Bold Red
}


class ColoredFormatter(logging.Formatter):
    """コンソール向けカラーフォーマッタ"""

    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"


class MemoryHandler(logging.Handler):
    """ログをメモリに保持するハンドラ"""

    def __init__(self, capacity=1000):
        super().__init__()
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)

    def emit(self, record):
        self.buffer.append(record)

    def get_records(self):
        return list(self.buffer)

    def clear(self):
        self.buffer.clear()


class AddonLogger:
    """アドオン用ロガークラス"""

    def __init__(self, addon_name):
        self.addon_name = addon_name
        self.logger = logging.getLogger(addon_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.memory_handler = MemoryHandler()
        self.console_handler = None
        self.file_handler = None

        self.logger.addHandler(self.memory_handler)
        self._current_rotation_settings = {}

    def configure(self, prefs):
        """設定を更新"""
        level = getattr(logging, prefs.log_level)
        self.logger.setLevel(level)

        # コンソールハンドラ
        if prefs.log_to_console and not self.console_handler:
            self.console_handler = logging.StreamHandler()
            self.console_handler.setFormatter(
                ColoredFormatter("%(levelname)s: %(message)s")
                if prefs.use_colors
                else logging.Formatter("%(levelname)s: %(message)s")
            )
            self.logger.addHandler(self.console_handler)
        elif not prefs.log_to_console and self.console_handler:
            self.logger.removeHandler(self.console_handler)
            self.console_handler = None

        # ファイルハンドラ
        if prefs.log_to_file:
            current_settings = {
                "path": prefs.log_file_path,
                "rotation_type": prefs.log_rotation_type,
                "max_size": prefs.log_max_size,
                "time_interval": prefs.log_time_interval,
                "backup_count": prefs.log_backup_count,
            }

            if (
                self.file_handler is None
                or current_settings != self._current_rotation_settings
            ):

                if self.file_handler:
                    self.logger.removeHandler(self.file_handler)
                    self.file_handler.close()

                handler_class = logging.FileHandler
                kwargs = {}

                if prefs.log_rotation_type == "SIZE":
                    handler_class = logging.handlers.RotatingFileHandler
                    kwargs["maxBytes"] = prefs.log_max_size * 1024 * 1024
                    kwargs["backupCount"] = prefs.log_backup_count
                elif prefs.log_rotation_type == "TIME":
                    handler_class = logging.handlers.TimedRotatingFileHandler
                    kwargs["when"] = prefs.log_time_interval.lower()
                    kwargs["interval"] = 1
                    kwargs["backupCount"] = prefs.log_backup_count

                try:
                    self.file_handler = handler_class(
                        filename=prefs.log_file_path,
                        encoding="utf-8",
                        delay=True,  # 最初の書き込みまでファイルを開かない
                        **kwargs,
                    )
                    self.file_handler.setFormatter(
                        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
                    )
                    self.logger.addHandler(self.file_handler)
                    self._current_rotation_settings = current_settings
                except PermissionError as e:
                    self.logger.error(f"Failed to create log file: {str(e)}")
                    prefs.log_to_file = False

    def capture_exception(self, additional_info=None):
        """例外をキャプチャしてログに記録"""
        exc_info = sys.exc_info()
        tb_text = "".join(traceback.format_exception(*exc_info))
        error_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        info = f"Error ID: {error_id}\n{tb_text}"
        if additional_info:
            info += f"\nAdditional Info: {additional_info}"

        self.logger.error(info)
        return error_id

    def section(self, title, level=logging.INFO):
        """セクション区切りデコレータ"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                self.logger.log(level, f"=== {title} ===")
                try:
                    return func(*args, **kwargs)
                finally:
                    self.logger.log(level, f"=== End: {title} ===")

            return wrapper

        return decorator

    def timer(self, message=None):
        """実行時間計測デコレータ"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                start = datetime.datetime.now()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed = datetime.datetime.now() - start
                    msg = message or f"{func.__name__} executed"
                    self.logger.info(f"{msg} in {elapsed.total_seconds():.2f}s")

            return wrapper

        return decorator

    def export_logs(self, file_path):
        """ログをファイルにエクスポート"""
        try:
            with open(file_path, "w") as f:
                for record in self.memory_handler.get_records():
                    f.write(f"{record.levelname}: {record.msg}\n")
            return True
        except Exception as e:
            self.logger.error(f"Log export failed: {str(e)}")
            return False


class AddonLoggerPreferencesMixin:
    """アドオンプリファレンス向けMixinクラス"""

    log_enable: BoolProperty(name="Enable Logging", default=True)

    log_level: EnumProperty(
        items=[
            ("DEBUG", "Debug", ""),
            ("INFO", "Info", ""),
            ("WARNING", "Warning", ""),
            ("ERROR", "Error", ""),
            ("CRITICAL", "Critical", ""),
        ],
        name="Log Level",
        default="INFO",
    )

    log_to_console: BoolProperty(name="Console Logging", default=True)

    use_colors: BoolProperty(name="Use Colors", default=True)

    log_to_file: BoolProperty(name="File Logging", default=False)

    log_file_path: StringProperty(name="Log File", subtype="FILE_PATH")

    memory_capacity: IntProperty(
        name="Memory Capacity", default=1000, min=100, max=10000
    )

    log_rotation_type: EnumProperty(
        items=[
            ("NONE", "None", "ログローテーションなし"),
            ("SIZE", "サイズ基準", "指定サイズに達したらログをローテート"),
            ("TIME", "時間基準", "指定間隔でログをローテート"),
        ],
        name="ログローテーション",
        default="NONE",
    )

    log_max_size: IntProperty(
        name="最大ログサイズ (MB)",
        default=10,
        min=1,
        max=1024,
        description="ローテートをトリガーするファイルサイズ",
    )

    log_time_interval: EnumProperty(
        items=[
            ("D", "毎日", "日単位でローテート"),
            ("H", "毎時", "時間単位でローテート"),
            ("MIDNIGHT", "日替わり", "日付変更時にローテート"),
        ],
        name="ローテーション間隔",
        default="D",
    )

    log_backup_count: IntProperty(
        name="保持バックアップ数",
        default=5,
        min=0,
        max=100,
        description="保持する古いログファイルの数（0で無制限）",
    )

    def draw_logger_preferences(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Logging Settings", icon="CONSOLE")
        box.prop(self, "log_enable")

        if self.log_enable:
            box.prop(self, "log_level")
            box.prop(self, "log_to_console")
            if self.log_to_console:
                box.prop(self, "use_colors")
            box.prop(self, "log_to_file")
            if self.log_to_file:
                box.prop(self, "log_file_path")
            box.prop(self, "memory_capacity")

        if self.log_to_file:
            box.prop(self, "log_rotation_type")

            if self.log_rotation_type != "NONE":
                sub = box.box()
                sub.label(text="ローテーション設定", icon="SETTINGS")

                if self.log_rotation_type == "SIZE":
                    sub.prop(self, "log_max_size")
                elif self.log_rotation_type == "TIME":
                    sub.prop(self, "log_time_interval")

                sub.prop(self, "log_backup_count")

                # 現在のログファイル情報を表示
                if os.path.exists(self.log_file_path):
                    stats = os.stat(self.log_file_path)
                    size_mb = stats.st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(stats.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    sub.label(
                        text=f"現在のログ: {size_mb:.1f}MB ({mtime})", icon="FILE_TEXT"
                    )


class LOG_OT_ExportLogs(Operator):
    """ログをエクスポートするオペレータ"""

    bl_idname = "log.export_logs"
    bl_label = "Export Logs"

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        logger = context.preferences.addons[__name__].preferences.logger
        try:
            # 現在のログファイルを強制的にローテート
            if logger.file_handler:
                if hasattr(logger.file_handler, "doRollover"):
                    logger.file_handler.doRollover()
                    logger.info("--- Manual log rotation triggered ---")

            # 最新のログファイルをエクスポート
            latest_log = logger.file_handler.baseFilename if logger.file_handler else ""
            if os.path.exists(latest_log):
                import shutil

                shutil.copy2(latest_log, self.filepath)
                self.report({"INFO"}, "Logs exported successfully")
                return {"FINISHED"}

            self.report({"ERROR"}, "Failed to export logs")
            return {"CANCELLED"}
        except Exception as e:
            logger.capture_exception()

    def execute(self, context):
        logger = context.preferences.addons[__name__].preferences.logger
        if logger.export_logs(self.filepath):
            self.report({"INFO"}, "Logs exported successfully")
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# class MyAddonPreferences(AddonPreferences, AddonLoggerPreferencesMixin):
#     bl_idname = __name__

#     def draw(self, context):
#         self.draw_logger_preferences(context)
#         self.layout.operator(LOG_OT_ExportLogs.bl_idname)

# def register():
#     bpy.utils.register_class(MyAddonPreferences)
#     bpy.utils.register_class(LOG_OT_ExportLogs)

#     prefs = bpy.context.preferences.addons[__name__].preferences
#     prefs.logger = AddonLogger(__name__)
#     prefs.logger.configure(prefs)

# def unregister():
#     bpy.utils.unregister_class(MyAddonPreferences)
#     bpy.utils.unregister_class(LOG_OT_ExportLogs)
