from setuptools import setup, find_packages

setup(
    name="repo-index",
    version="0.1.0",
    description="IDE-like code indexer that creates searchable SQLite index of methods, constants, and variables",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "tree-sitter>=0.20.0",
        "tree-sitter-python>=0.20.0",
    ],
    entry_points={
        "console_scripts": [
            "repo-index=repo_index.cli:main",
        ],
    },
)