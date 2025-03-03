# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Modular Renamer"
copyright = "2025, Pluglug"
author = "Pluglug"
release = "0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # Google/Numpy形式のDocstring対応
    "sphinx.ext.viewcode",  # ソースコード表示
    "sphinx.ext.intersphinx",  # 外部ドキュメントへのリンク
    "sphinx.ext.inheritance_diagram",  # 継承関係の図
    "sphinx.ext.graphviz",  # クラス図
    "sphinx_automodapi.automodapi",  # モジュールのAPIドキュメント
    "sphinxcontrib.mermaid",  # マーメイド図
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
]

autodoc_mock_imports = ["bpy", "mathutils"]

inheritance_graph_attrs = dict(rankdir="TB", size='"6.0, 8.0"')
inheritance_node_attrs = dict(
    shape="rect", fontsize=12, height=0.4, margin='"0.08, 0.03"'
)

mermaid_params = [
    "--theme",
    "default",
    "--width",
    "100%",
    "--backgroundColor",
    "transparent",
]

mermaid_version = "11.2.0"  # 使用するMermaidのバージョン
mermaid_output_format = "raw"  # HTML出力時はJavaScriptで描画
# mermaid_d3_zoom = True  # マウスホイールでズーム可能に
# mermaid_sequence_config = True  # シーケンス図の設定を有効化

mermaid_include_elk = "0.1.4"  # ELKレイアウトを有効化


# デフォルト初期化設定
mermaid_init_js = """
mermaid.initialize({
  startOnLoad: true,
  theme: 'default',
  themeVariables: {
    klassStyle: 'classic'
  },
  layoutEngine: 'elk'
})
"""

# source_suffix = {
#     '.rst': 'restructuredtext',
#     '.md': 'markdown',
# }

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_title = "Modular Renamer (Dev)"
html_static_path = ["_static"]
