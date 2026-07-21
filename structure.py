from pathlib import Path

# ==========================================================
# Project Root
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parent

# ==========================================================
# Ignore
# ==========================================================

IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
}

IGNORE_FILES = {
    ".DS_Store",
}

# ==========================================================
# Tree Printer
# ==========================================================

def print_tree(path: Path, prefix: str = "") -> None:
    """
    Prints the project tree while ignoring unnecessary folders.
    """

    entries = sorted(
        [
            p for p in path.iterdir()
            if p.name not in IGNORE_DIRS
            and p.name not in IGNORE_FILES
        ],
        key=lambda p: (p.is_file(), p.name.lower())
    )

    total = len(entries)

    for index, entry in enumerate(entries):

        connector = "└── " if index == total - 1 else "├── "

        print(prefix + connector + entry.name)

        if entry.is_dir():

            extension = "    " if index == total - 1 else "│   "

            print_tree(entry, prefix + extension)


# ==========================================================
# Main
# ==========================================================

if __name__ == "__main__":

    print(PROJECT_ROOT.name)
    print_tree(PROJECT_ROOT)