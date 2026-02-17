import os

# -------------------------------------------------
# CONFIG (gitignore-style)
# -------------------------------------------------

ROOT_DIR = "."

# folder names to ignore completely
IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
}

# file patterns / extensions to ignore
IGNORE_EXTS = {
    ".pyc",
    ".pyo",
    ".log",
}

IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
}

# -------------------------------------------------
# LOGIC
# -------------------------------------------------

def should_ignore_file(filename: str) -> bool:
    name, ext = os.path.splitext(filename)
    return filename in IGNORE_FILES or ext.lower() in IGNORE_EXTS


def list_project_paths(root_dir=ROOT_DIR):
    paths = []

    for current_root, dirs, files in os.walk(root_dir):
        # 🚫 prune ignored directories (IMPORTANT)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        # add directory itself
        if current_root != root_dir:
            paths.append(os.path.abspath(current_root))

        # add files except ignored ones
        for f in files:
            if should_ignore_file(f):
                continue
            paths.append(os.path.abspath(os.path.join(current_root, f)))

    return paths


# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":
    for p in list_project_paths():
        print(p)
