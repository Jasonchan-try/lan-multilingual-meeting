from pathlib import Path

from app.config import TEMP_DIR


class CleanupService:
    @staticmethod
    def clean_temp_dir() -> None:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        for p in TEMP_DIR.iterdir():
            try:
                if p.is_file():
                    p.unlink(missing_ok=True)
                else:
                    for f in p.rglob("*"):
                        if f.is_file():
                            f.unlink(missing_ok=True)
                    for d in sorted([d for d in p.rglob("*") if d.is_dir()], reverse=True):
                        d.rmdir()
                    p.rmdir()
            except Exception:
                continue

    @staticmethod
    def write_summary_file(room_id: str, text: str, ext: str = "md") -> Path:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        p = TEMP_DIR / f"summary_{room_id}.{ext}"
        p.write_text(text, encoding="utf-8")
        return p
