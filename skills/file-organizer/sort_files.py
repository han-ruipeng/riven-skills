#!/usr/bin/env python3
"""File Organizer - 按扩展名自动归类文件。

用法：
    python sort_files.py <目标文件夹路径>

示例：
    python sort_files.py ~/Downloads
    python sort_files.py .
"""

import sys
import shutil
from pathlib import Path

# ── 分类映射 ──────────────────────────────────────────
CATEGORY_MAP = {
    "images":     {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"},
    "documents":  {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv"},
    "archives":   {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "code":       {".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".go", ".rs", ".json", ".xml", ".yaml", ".yml"},
    "videos":     {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"},
    "audio":      {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"},
    "installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"},
}


def classify_file(file: Path) -> str:
    """返回文件应该归入的类别文件夹名称。"""
    ext = file.suffix.lower()
    for category, extensions in CATEGORY_MAP.items():
        if ext in extensions:
            return category
    return "others"


def main(target_dir: str):
    root = Path(target_dir).resolve()
    if not root.is_dir():
        print(f"[ERROR] 文件夹不存在: {root}")
        sys.exit(1)

    files = [f for f in root.iterdir() if f.is_file() and not f.name.startswith('.')]
    if not files:
        print("没有需要整理的文件。")
        return

    # 预览分类结果
    print(f"\n{'='*50}")
    print(f"📂 目标文件夹: {root}")
    print(f"📄 待整理文件: {len(files)} 个\n")

    categories: dict[str, list[Path]] = {}
    for f in files:
        cat = classify_file(f)
        categories.setdefault(cat, []).append(f)

    for cat, items in sorted(categories.items()):
        print(f"  [{cat}] → {len(items)} 个文件")
        for item in items:
            print(f"      • {item.name}")
    print(f"{'='*50}")

    # 确认
    confirm = input("\n确认执行移动？(y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("已取消。")
        return

    # 执行移动
    moved = 0
    for cat, items in categories.items():
        dest_dir = root / cat
        dest_dir.mkdir(exist_ok=True)
        for src in items:
            dest = dest_dir / src.name
            if dest.exists():
                print(f"[SKIP] 目标已存在，跳过: {src.name}")
                continue
            shutil.move(str(src), str(dest))
            moved += 1

    print(f"\n✅ 完成！移动了 {moved} 个文件到 {len(categories)} 个类别文件夹。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python sort_files.py <文件夹路径>")
        sys.exit(1)
    main(sys.argv[1])
