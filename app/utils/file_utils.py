from pathlib import Path


def safe_delete(path: Path) -> None:
    if path.exists():
        if path.is_file():
            path.unlink(missing_ok=True)
        else:
            for item in path.iterdir():
                if item.is_dir():
                    safe_delete(item)
                else:
                    item.unlink(missing_ok=True)
            path.rmdir()
