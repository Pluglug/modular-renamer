"""
Enhanced Class Diagram Generator
自動クラス図生成システム v2.0

Pythonプロジェクトのコードから自動的にMermaid形式のクラス図を生成するシステムです。
LLMとの連携にも適したテキストベースのクラス図を生成します。
"""

import ast
import json
import os
import re
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

# -----------------------------------------------------------------------------
# 設定と定数
# -----------------------------------------------------------------------------


class DiagramConfig:
    """クラス図生成の設定を管理するクラス"""

    class OutputFormat(Enum):
        MERMAID = "mermaid"  # Mermaid形式
        PLANTUML = "plantuml"  # PlantUML形式

    def __init__(self):
        # 基本設定
        self.output_format = self.OutputFormat.MERMAID
        self.include_private = True  # プライベートメソッド/属性を含める
        self.include_dunder = False  # __で始まるメソッド/属性を含める
        self.include_docstrings = True  # docstringを含める
        self.include_imports = False  # importを含める
        self.include_empty_methods = True  # 空のメソッドも含める
        self.max_method_display_lines = 1  # メソッドの表示行数制限

        # 表示設定
        self.group_by_namespace = True  # 名前空間ごとにグループ化
        self.show_relationships = True  # 関係性を表示
        self.show_interface_stereotype = True  # インターフェースのステレオタイプを表示
        self.show_abstract_stereotype = True  # 抽象クラスのステレオタイプを表示
        self.show_type_hints = True  # 型ヒントを表示

        # 解析設定
        self.detect_interfaces_by_name = True  # 命名規則からインターフェースを検出
        self.detect_abstract_by_methods = True  # 抽象メソッドの有無から抽象クラスを検出
        self.interface_prefix = "I"  # インターフェース接頭辞
        self.abstract_prefix = ["Abstract", "Base"]  # 抽象クラスの接頭辞
        self.abstract_suffix = ["Base", "Abstract", "ABC"]  # 抽象クラスの接尾辞

        # デザイン設定
        self.theme = "default"  # 図のテーマ
        self.layout = "dagre"  # レイアウトアルゴリズム

        # 除外設定
        self.exclude_dirs = [
            ".venv",
            "venv",
            "__pycache__",
            ".git",
            "node_modules",
            "dist",
            "build",
        ]
        self.exclude_files = ["setup.py", "__init__.py"]
        self.exclude_modules = []

        # Blender固有設定
        self.exclude_blender_classes = True  # Blender固有のクラスを除外
        self.blender_base_classes = [
            "Operator",
            "PropertyGroup",
            "Panel",
            "UIList",
            "Menu",
            "AddonPreferences",
            # "AddonLoggerPreferencesMixin",
            "bpy_struct",
            "ID",
        ]

    def to_dict(self) -> dict:
        """設定を辞書形式で返す"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result

    def from_dict(self, data: dict) -> None:
        """辞書から設定を読み込む"""
        for key, value in data.items():
            if key == "output_format" and isinstance(value, str):
                self.output_format = self.OutputFormat(value)
            elif hasattr(self, key):
                setattr(self, key, value)


# -----------------------------------------------------------------------------
# コアクラス
# -----------------------------------------------------------------------------


class ClassInfo:
    """クラス情報を格納するクラス"""

    def __init__(
        self,
        name: str,
        namespace: str = "",
        is_interface: bool = False,
        is_abstract: bool = False,
        docstring: str = "",
    ):
        self.name = name
        self.namespace = namespace
        self.is_interface = is_interface
        self.is_abstract = is_abstract
        self.docstring = docstring
        self.attributes: List[Dict[str, str]] = []
        self.methods: List[Dict[str, str]] = []
        self.parent_classes: List[str] = []
        self.realizations: List[str] = []  # 実装するインターフェース
        self.dependencies: List[str] = []  # 依存関係
        self.associations: List[Dict[str, Any]] = []  # 関連関係
        self.nested_classes: List[str] = []  # ネストされたクラス

    def add_attribute(self, name: str, visibility: str = "+", type_hint: str = ""):
        """属性を追加"""
        self.attributes.append(
            {"name": name, "visibility": visibility, "type": type_hint}
        )

    def add_method(
        self,
        name: str,
        visibility: str = "+",
        params: List[Dict[str, str]] = None,
        return_type: str = "",
        is_abstract: bool = False,
        is_static: bool = False,
        is_class_method: bool = False,
    ):
        """メソッドを追加"""
        if params is None:
            params = []

        self.methods.append(
            {
                "name": name,
                "visibility": visibility,
                "params": params,
                "return_type": return_type,
                "is_abstract": is_abstract,
                "is_static": is_static,
                "is_class_method": is_class_method,
            }
        )

    def get_full_name(self) -> str:
        """完全な名前（名前空間を含む）を取得"""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name

    def to_dict(self) -> dict:
        """クラス情報を辞書形式で返す"""
        return {
            "name": self.name,
            "namespace": self.namespace,
            "is_interface": self.is_interface,
            "is_abstract": self.is_abstract,
            "docstring": self.docstring,
            "attributes": self.attributes,
            "methods": self.methods,
            "parent_classes": self.parent_classes,
            "realizations": self.realizations,
            "dependencies": self.dependencies,
            "associations": self.associations,
            "nested_classes": self.nested_classes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassInfo":
        """辞書からクラス情報を作成"""
        class_info = cls(
            name=data["name"],
            namespace=data.get("namespace", ""),
            is_interface=data.get("is_interface", False),
            is_abstract=data.get("is_abstract", False),
            docstring=data.get("docstring", ""),
        )
        class_info.attributes = data.get("attributes", [])
        class_info.methods = data.get("methods", [])
        class_info.parent_classes = data.get("parent_classes", [])
        class_info.realizations = data.get("realizations", [])
        class_info.dependencies = data.get("dependencies", [])
        class_info.associations = data.get("associations", [])
        class_info.nested_classes = data.get("nested_classes", [])
        return class_info


class RelationshipInfo:
    """クラス間の関係情報を格納するクラス"""

    class RelationType(Enum):
        INHERITANCE = "inheritance"  # 継承
        REALIZATION = "realization"  # 実現
        DEPENDENCY = "dependency"  # 依存
        ASSOCIATION = "association"  # 関連
        AGGREGATION = "aggregation"  # 集約
        COMPOSITION = "composition"  # 合成

    def __init__(
        self,
        source: str,
        target: str,
        relation_type: RelationType,
        label: str = "",
        source_multiplicity: str = "",
        target_multiplicity: str = "",
    ):
        self.source = source
        self.target = target
        self.relation_type = relation_type
        self.label = label
        self.source_multiplicity = source_multiplicity
        self.target_multiplicity = target_multiplicity

    def to_dict(self) -> dict:
        """関係情報を辞書形式で返す"""
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type.value,
            "label": self.label,
            "source_multiplicity": self.source_multiplicity,
            "target_multiplicity": self.target_multiplicity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RelationshipInfo":
        """辞書から関係情報を作成"""
        return cls(
            source=data["source"],
            target=data["target"],
            relation_type=cls.RelationType(data["relation_type"]),
            label=data.get("label", ""),
            source_multiplicity=data.get("source_multiplicity", ""),
            target_multiplicity=data.get("target_multiplicity", ""),
        )


class DiagramData:
    """クラス図のデータを管理するクラス"""

    def __init__(self):
        self.classes: Dict[str, ClassInfo] = {}  # クラス情報 (key: クラス名)
        self.relationships: List[RelationshipInfo] = []  # 関係情報
        self.namespaces: Set[str] = set()  # 名前空間

    def add_class(self, class_info: ClassInfo) -> None:
        """クラス情報を追加"""
        self.classes[class_info.get_full_name()] = class_info
        if class_info.namespace:
            self.namespaces.add(class_info.namespace)

    def add_relationship(self, relationship: RelationshipInfo) -> None:
        """関係情報を追加"""
        self.relationships.append(relationship)

    def get_class(self, name: str, namespace: str = "") -> Optional[ClassInfo]:
        """クラス情報を取得"""
        full_name = f"{namespace}.{name}" if namespace else name
        return self.classes.get(full_name)

    def to_dict(self) -> dict:
        """図データを辞書形式で返す"""
        return {
            "classes": {name: cls.to_dict() for name, cls in self.classes.items()},
            "relationships": [rel.to_dict() for rel in self.relationships],
            "namespaces": list(self.namespaces),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiagramData":
        """辞書から図データを作成"""
        diagram = cls()
        diagram.namespaces = set(data.get("namespaces", []))

        # クラス情報の復元
        for name, class_data in data.get("classes", {}).items():
            diagram.classes[name] = ClassInfo.from_dict(class_data)

        # 関係情報の復元
        for rel_data in data.get("relationships", []):
            diagram.relationships.append(RelationshipInfo.from_dict(rel_data))

        return diagram

    def serialize(self) -> str:
        """図データをJSON形式でシリアライズ"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def deserialize(cls, json_data: str) -> "DiagramData":
        """JSON形式の文字列から図データを復元"""
        return cls.from_dict(json.loads(json_data))


class CodeAnalyzer(ABC):
    """コード解析の基底クラス"""

    def __init__(self, config: DiagramConfig):
        self.config = config

    @abstractmethod
    def analyze(self, path: str) -> DiagramData:
        """コードを解析して図データを生成"""
        pass


class PythonASTAnalyzer(CodeAnalyzer):
    """Python ASTを使用したコード解析クラス"""

    def __init__(self, config: DiagramConfig):
        super().__init__(config)

    def analyze(self, path: str) -> DiagramData:
        """指定されたパスのPythonコードを解析"""
        diagram_data = DiagramData()

        if os.path.isfile(path) and path.endswith(".py"):
            self._analyze_file(path, diagram_data)
        elif os.path.isdir(path):
            self._analyze_directory(path, diagram_data)

        return diagram_data

    def _should_exclude(self, path: str, is_dir: bool = False) -> bool:
        """指定されたパスを除外すべきかどうか判定"""
        basename = os.path.basename(path)

        # ディレクトリの除外判定
        if is_dir:
            return basename in self.config.exclude_dirs

        # ファイルの除外判定
        if basename in self.config.exclude_files:
            return True

        # モジュールの除外判定
        if basename.endswith(".py"):
            module_name = basename[:-3]
            if module_name in self.config.exclude_modules:
                return True

        return False

    def _analyze_directory(self, directory: str, diagram_data: DiagramData) -> None:
        """ディレクトリ内のPythonファイルを再帰的に解析"""
        for root, dirs, files in os.walk(directory):
            # 除外ディレクトリをリストから削除して処理対象から外す
            dirs[:] = [
                d for d in dirs if not self._should_exclude(os.path.join(root, d), True)
            ]

            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith(".py") and not self._should_exclude(file_path):
                    self._analyze_file(file_path, diagram_data)

    def _analyze_file(self, file_path: str, diagram_data: DiagramData) -> None:
        """単一のPythonファイルを解析"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            # ファイルの相対パスから名前空間を取得
            rel_path = os.path.relpath(
                file_path, os.path.dirname(os.path.dirname(file_path))
            )
            namespace = os.path.dirname(rel_path).replace(os.path.sep, ".")

            tree = ast.parse(code)
            self._extract_classes(tree, namespace, diagram_data)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _extract_classes(
        self, tree: ast.AST, namespace: str, diagram_data: DiagramData
    ) -> None:
        """ASTからクラス情報を抽出"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._process_class_def(node, namespace, diagram_data)

    def _process_class_def(
        self, node: ast.ClassDef, namespace: str, diagram_data: DiagramData
    ) -> None:
        """クラス定義を処理"""
        # Blender固有クラスの除外
        if self.config.exclude_blender_classes:
            for base in node.bases:
                base_name = self._get_name_from_expr(base)
                for blender_class in self.config.blender_base_classes:
                    if base_name == blender_class or base_name.endswith(
                        "." + blender_class
                    ):
                        # Blender固有クラスを継承している場合は処理をスキップ
                        return

        # クラスの種類を判定
        is_interface = self._is_interface(node)
        is_abstract = self._is_abstract(node)

        # docstringを取得
        docstring = ast.get_docstring(node) or ""

        # クラス情報を作成
        class_info = ClassInfo(
            name=node.name,
            namespace=namespace,
            is_interface=is_interface,
            is_abstract=is_abstract,
            docstring=docstring,
        )

        # 親クラスを処理
        for base in node.bases:
            parent_name = self._get_name_from_expr(base)

            # ABCや一般的でないBlender基底クラスは関係図から除外
            if parent_name == "ABC" or parent_name.endswith(".ABC"):
                continue

            if self.config.exclude_blender_classes:
                skip_relation = False
                for blender_class in self.config.blender_base_classes:
                    if parent_name == blender_class or parent_name.endswith(
                        "." + blender_class
                    ):
                        skip_relation = True
                        break
                if skip_relation:
                    continue

            class_info.parent_classes.append(parent_name)

            # 関係性を追加
            relation_type = (
                RelationshipInfo.RelationType.REALIZATION
                if parent_name.startswith("I") and parent_name[1:2].isupper()
                else RelationshipInfo.RelationType.INHERITANCE
            )

            diagram_data.add_relationship(
                RelationshipInfo(
                    source=class_info.get_full_name(),
                    target=parent_name,
                    relation_type=relation_type,
                )
            )

        # クラスの内容を処理
        for item in node.body:
            # 属性定義を処理
            if isinstance(item, ast.Assign):
                self._process_attribute(item, class_info)

            # メソッド定義を処理
            elif isinstance(item, ast.FunctionDef):
                self._process_method(item, class_info)

            # ネストしたクラスを処理
            elif isinstance(item, ast.ClassDef):
                nested_class_name = item.name
                class_info.nested_classes.append(nested_class_name)

        # クラス情報を追加
        diagram_data.add_class(class_info)

    def _process_attribute(self, node: ast.Assign, class_info: ClassInfo) -> None:
        """属性定義を処理"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id

                # 可視性を判定
                visibility = "+"
                if name.startswith("__"):
                    if not self.config.include_dunder:
                        continue
                    visibility = "-"
                elif name.startswith("_"):
                    if not self.config.include_private:
                        continue
                    visibility = "#"

                # 型ヒントを取得
                type_hint = ""
                if hasattr(target, "annotation") and target.annotation:
                    type_hint = self._get_name_from_expr(target.annotation)

                class_info.add_attribute(name, visibility, type_hint)

    def _process_method(self, node: ast.FunctionDef, class_info: ClassInfo) -> None:
        """メソッド定義を処理"""
        name = node.name

        # 可視性を判定
        visibility = "+"
        if name.startswith("__") and name != "__init__":
            if not self.config.include_dunder:
                return
            visibility = "-"
        elif name.startswith("_"):
            if not self.config.include_private:
                return
            visibility = "#"

        # 抽象メソッドか判定
        is_abstract = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                is_abstract = True
                break
            elif (
                isinstance(decorator, ast.Attribute)
                and self._get_name_from_expr(decorator) == "abc.abstractmethod"
            ):
                is_abstract = True
                break

        # staticmethod, classmethodを判定
        is_static = False
        is_class_method = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "staticmethod":
                    is_static = True
                elif decorator.id == "classmethod":
                    is_class_method = True

        # パラメータ情報を抽出
        params = []
        for arg in node.args.args:
            if arg.arg in ("self", "cls") and not is_static:
                continue

            param_type = ""
            if hasattr(arg, "annotation") and arg.annotation:
                param_type = self._get_name_from_expr(arg.annotation)

            params.append({"name": arg.arg, "type": param_type})

        # 戻り値の型を取得
        return_type = ""
        if node.returns:
            return_type = self._get_name_from_expr(node.returns)

        class_info.add_method(
            name=name,
            visibility=visibility,
            params=params,
            return_type=return_type,
            is_abstract=is_abstract,
            is_static=is_static,
            is_class_method=is_class_method,
        )

    def _is_interface(self, node: ast.ClassDef) -> bool:
        """インターフェースかどうかを判定"""
        if not self.config.detect_interfaces_by_name:
            return False

        # 命名規則からインターフェースを判定
        if (
            node.name.startswith(self.config.interface_prefix)
            and len(node.name) > 1
            and node.name[1].isupper()
        ):
            return True

        # 内容からインターフェースを判定
        methods_abstract = True
        has_methods = False

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                has_methods = True
                is_abstract = False

                # 抽象メソッドか確認
                for decorator in item.decorator_list:
                    if (
                        isinstance(decorator, ast.Name)
                        and decorator.id == "abstractmethod"
                    ):
                        is_abstract = True
                        break

                if not is_abstract and item.name != "__init__":
                    methods_abstract = False
                    break

        return has_methods and methods_abstract

    def _is_abstract(self, node: ast.ClassDef) -> bool:
        """抽象クラスかどうかを判定"""
        # 命名規則から抽象クラスを判定（接頭辞）
        for prefix in self.config.abstract_prefix:
            if node.name.startswith(prefix):
                return True

        # 命名規則から抽象クラスを判定（接尾辞）
        for suffix in self.config.abstract_suffix:
            if node.name.endswith(suffix):
                return True

        # ABC（Abstract Base Class）の継承を確認
        for base in node.bases:
            base_name = self._get_name_from_expr(base)
            if base_name == "ABC" or base_name.endswith(".ABC"):
                return True

            # Blender固有の抽象基底クラスを除外
            if self.config.exclude_blender_classes:
                for blender_class in self.config.blender_base_classes:
                    if base_name == blender_class or base_name.endswith(
                        "." + blender_class
                    ):
                        return False

        if not self.config.detect_abstract_by_methods:
            return False

        # 抽象メソッドの有無から抽象クラスを判定
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                for decorator in item.decorator_list:
                    if (
                        isinstance(decorator, ast.Name)
                        and decorator.id == "abstractmethod"
                    ):
                        return True
                    elif (
                        isinstance(decorator, ast.Attribute)
                        and self._get_name_from_expr(decorator) == "abc.abstractmethod"
                    ):
                        return True

        return False

    def _get_name_from_expr(self, expr) -> str:
        """式からクラス名や型名を取得"""
        if isinstance(expr, ast.Name):
            return expr.id
        elif isinstance(expr, ast.Attribute):
            value_name = self._get_name_from_expr(expr.value)
            return f"{value_name}.{expr.attr}"
        elif isinstance(expr, ast.Subscript):
            value_name = self._get_name_from_expr(expr.value)
            if isinstance(expr.slice, ast.Index):
                if hasattr(expr.slice, "value"):
                    # Python 3.8以前
                    slice_name = self._get_name_from_expr(expr.slice.value)
                else:
                    # Python 3.9以降
                    slice_name = self._get_name_from_expr(expr.slice)
                return f"{value_name}[{slice_name}]"
            return f"{value_name}[...]"
        elif isinstance(expr, ast.Tuple):
            items = []
            for elt in expr.elts:
                items.append(self._get_name_from_expr(elt))
            return ", ".join(items)
        elif isinstance(expr, ast.Constant):
            return str(expr.value)
        elif isinstance(expr, ast.List):
            return "list"
        elif isinstance(expr, ast.Dict):
            return "dict"
        return "Any"


class DiagramGenerator(ABC):
    """図生成の基底クラス"""

    def __init__(self, config: DiagramConfig):
        self.config = config

    @abstractmethod
    def generate(self, diagram_data: DiagramData) -> str:
        """図を生成"""
        pass


class MermaidGenerator(DiagramGenerator):
    """Mermaid形式の図を生成するクラス"""

    def __init__(self, config: DiagramConfig):
        super().__init__(config)

    def generate(self, diagram_data: DiagramData) -> str:
        """Mermaid形式のクラス図を生成"""
        mermaid = "---\n"
        mermaid += "config:\n"
        mermaid += f"  theme: {self.config.theme}\n"
        mermaid += f"  layout: {self.config.layout}\n"
        mermaid += "---\n"
        mermaid += "classDiagram\n"

        # 名前空間ごとにクラスをグループ化
        if self.config.group_by_namespace:
            for namespace in sorted(diagram_data.namespaces):
                mermaid += f"    namespace {namespace} {{\n"

                # この名前空間に属するクラスを生成
                for full_name, class_info in diagram_data.classes.items():
                    if class_info.namespace == namespace:
                        mermaid += self._generate_class(class_info)

                mermaid += "    }\n"

        # 名前空間なし、または名前空間でグループ化しない場合のクラス
        namespaced_classes = set()
        for full_name, class_info in diagram_data.classes.items():
            if class_info.namespace and self.config.group_by_namespace:
                namespaced_classes.add(full_name)
                continue

            mermaid += self._generate_class(class_info)

        # 関係性を追加
        if self.config.show_relationships:
            for relationship in diagram_data.relationships:
                mermaid += self._generate_relationship(relationship)

        return mermaid

    def _generate_class(self, class_info: ClassInfo) -> str:
        """クラス定義を生成"""
        result = ""
        indent = (
            "        "
            if class_info.namespace and self.config.group_by_namespace
            else "    "
        )

        # クラス定義の開始
        result += f"{indent}class {class_info.name} {{\n"

        # ステレオタイプを追加
        if class_info.is_interface and self.config.show_interface_stereotype:
            result += f"{indent}    <<interface>>\n"
        elif class_info.is_abstract and self.config.show_abstract_stereotype:
            result += f"{indent}    <<abstract>>\n"

        # 属性
        for attr in class_info.attributes:
            type_hint = (
                f": {attr['type']}"
                if attr["type"] and self.config.show_type_hints
                else ""
            )
            result += f"{indent}    {attr['visibility']}{attr['name']}{type_hint}\n"

        # メソッド
        for method in class_info.methods:
            # パラメータ
            params = []
            for param in method["params"]:
                type_hint = (
                    f": {param['type']}"
                    if param["type"] and self.config.show_type_hints
                    else ""
                )
                params.append(f"{param['name']}{type_hint}")

            # 戻り値
            return_type = (
                f" {method['return_type']}"
                if method["return_type"] and self.config.show_type_hints
                else ""
            )

            # メソッド修飾子
            prefix = ""
            if method["is_abstract"]:
                prefix = "*"  # 抽象メソッド
            elif method["is_static"]:
                prefix = "$"  # 静的メソッド
            elif method["is_class_method"]:
                prefix = "^"  # クラスメソッド

            result += f"{indent}    {method['visibility']}{prefix}{method['name']}({', '.join(params)}){return_type}\n"

        result += f"{indent}}}\n"
        return result

    def _generate_relationship(self, relationship: RelationshipInfo) -> str:
        """関係性を生成"""
        arrow = {
            RelationshipInfo.RelationType.INHERITANCE: "<|--",
            RelationshipInfo.RelationType.REALIZATION: "<|..",
            RelationshipInfo.RelationType.DEPENDENCY: "<...",
            RelationshipInfo.RelationType.ASSOCIATION: "<-->",
            RelationshipInfo.RelationType.AGGREGATION: "o--",
            RelationshipInfo.RelationType.COMPOSITION: "*--",
        }[relationship.relation_type]

        source = relationship.source.split(".")[-1]  # 完全修飾名からクラス名のみを抽出
        target = relationship.target.split(".")[-1]

        label = f" : {relationship.label}" if relationship.label else ""

        return f"    {source} {arrow} {target}{label}\n"


class PlantUMLGenerator(DiagramGenerator):
    """PlantUML形式の図を生成するクラス"""

    def __init__(self, config: DiagramConfig):
        super().__init__(config)

    def generate(self, diagram_data: DiagramData) -> str:
        """PlantUML形式のクラス図を生成"""
        # 実装は省略（必要に応じて実装）
        return ""


# -----------------------------------------------------------------------------
# ユーティリティ関数
# -----------------------------------------------------------------------------


def generate_class_diagram(
    project_path: str,
    output_path: str = None,
    config: DiagramConfig = None,
    exclude_dirs: List[str] = None,
    exclude_files: List[str] = None,
    exclude_modules: List[str] = None,
) -> str:
    """クラス図を生成する関数

    Args:
        project_path: プロジェクトのルートパス
        output_path: 出力パス (指定しない場合は生成したクラス図を返すのみ)
        config: 図の設定
        exclude_dirs: 除外するディレクトリのリスト
        exclude_files: 除外するファイルのリスト
        exclude_modules: 除外するモジュールのリスト

    Returns:
        str: 生成されたクラス図
    """
    # 設定
    config = config or DiagramConfig()

    # 除外設定を更新
    if exclude_dirs:
        config.exclude_dirs.extend(exclude_dirs)
    if exclude_files:
        config.exclude_files.extend(exclude_files)
    if exclude_modules:
        config.exclude_modules.extend(exclude_modules)

    # コード解析
    analyzer = PythonASTAnalyzer(config)
    diagram_data = analyzer.analyze(project_path)

    # 図の生成
    if config.output_format == DiagramConfig.OutputFormat.MERMAID:
        generator = MermaidGenerator(config)
    elif config.output_format == DiagramConfig.OutputFormat.PLANTUML:
        generator = PlantUMLGenerator(config)
    else:
        raise ValueError(f"Unsupported output format: {config.output_format}")

    diagram = generator.generate(diagram_data)

    # ファイルに出力
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(diagram)

    return diagram


# -----------------------------------------------------------------------------
# コマンドラインインターフェース
# -----------------------------------------------------------------------------


def main():
    """コマンドライン実行時のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate class diagrams from Python code"
    )
    parser.add_argument("project_path", help="Path to the Python project root")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument(
        "-f",
        "--format",
        choices=["mermaid", "plantuml"],
        default="mermaid",
        help="Output format (default: mermaid)",
    )
    parser.add_argument(
        "-g",
        "--group-by-namespace",
        action="store_true",
        help="Group classes by namespace",
    )
    parser.add_argument(
        "-r",
        "--show-relationships",
        action="store_true",
        help="Show relationships between classes",
    )
    parser.add_argument(
        "-p",
        "--include-private",
        action="store_true",
        help="Include private methods and attributes",
    )
    parser.add_argument(
        "--no-docstrings", action="store_true", help="Exclude docstrings"
    )
    parser.add_argument(
        "--exclude-dirs",
        nargs="*",
        default=[],
        help="Directories to exclude (e.g. .venv node_modules)",
    )
    parser.add_argument(
        "--exclude-files",
        nargs="*",
        default=[],
        help="Files to exclude (e.g. setup.py test_*.py)",
    )
    parser.add_argument(
        "--exclude-modules",
        nargs="*",
        default=[],
        help="Modules to exclude (e.g. config utils)",
    )
    parser.add_argument(
        "--include-blender-classes",
        action="store_true",
        help="Include Blender-specific base classes in the diagram",
    )
    parser.add_argument(
        "--theme", default="default", help="Diagram theme (e.g. default, forest, dark)"
    )
    parser.add_argument(
        "--layout",
        default="dagre",
        help="Diagram layout algorithm (e.g. dagre, lr, td)",
    )

    args = parser.parse_args()

    # 設定オブジェクトを作成
    config = DiagramConfig()
    config.output_format = DiagramConfig.OutputFormat(args.format)
    config.group_by_namespace = args.group_by_namespace
    config.show_relationships = args.show_relationships
    config.include_private = args.include_private
    config.include_docstrings = not args.no_docstrings
    config.exclude_blender_classes = not args.include_blender_classes
    config.theme = args.theme
    config.layout = args.layout

    # クラス図生成
    diagram = generate_class_diagram(
        project_path=args.project_path,
        output_path=args.output,
        config=config,
        exclude_dirs=args.exclude_dirs,
        exclude_files=args.exclude_files,
        exclude_modules=args.exclude_modules,
    )

    # 結果表示
    if args.output:
        print(f"Class diagram saved to {args.output}")
    else:
        print(diagram)


if __name__ == "__main__":
    # サンプル実行コード
    config = DiagramConfig()
    config.output_format = DiagramConfig.OutputFormat.MERMAID
    config.group_by_namespace = True
    config.show_relationships = True
    config.include_private = True
    config.include_docstrings = True
    config.exclude_blender_classes = True
    config.theme = "default"
    config.layout = "dagre"

    # クラス図生成
    diagram = generate_class_diagram(
        project_path=".",
        output_path="./debug/class_diagram.mmd",
        config=config,
        exclude_dirs=[".venv", "docs", "tests", "utils"],
        exclude_files=["setup.py", "class_diagram_generator.py"],
        exclude_modules=["config", "utils"],
    )

    print(f"Class diagram generated and saved to class_diagram.mmd")
