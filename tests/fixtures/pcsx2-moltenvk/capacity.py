"""Account for Xcode CAS sparse reservations without ignoring allocated blocks."""
from pathlib import Path
import shutil


def budgeted_size(relative, logical, allocated):
    """Only the two observed CAS reservation files use allocated-byte accounting."""
    path = Path(relative)
    expected = {"v8.index": 8 * 1024**3, "v8.data": 16 * 1024**3}
    recognized = (
        path.parts[-4:-1] == ("CompilationCache.noindex", "generic", "v1.1")
        and path.name in expected
        and logical == expected.get(path.name)
        and 0 <= allocated < logical
    )
    return (allocated, True) if recognized else (max(logical, allocated), False)


def measure(root):
    raw = allocated = budget = sparse = 0
    for path in root.rglob("*"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            info = path.stat()
            disk = info.st_blocks * 512
            charged, recognized = budgeted_size(path.relative_to(root), info.st_size, disk)
            raw += info.st_size
            allocated += disk
            budget += charged
            sparse += int(recognized)
        except FileNotFoundError:
            continue
    return {"free_bytes": shutil.disk_usage(root).free, "logical_bytes": budget,
            "allocated_bytes": allocated, "raw_logical_bytes": raw,
            "recognized_sparse_files": sparse}
