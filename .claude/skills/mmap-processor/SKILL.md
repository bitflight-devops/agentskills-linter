---
name: mmap-processor
description: Enforces memory-mapped file I/O for large file processing in Python. Use when reading, searching, or processing files larger than 100MB, or when performing delimiter/boundary searches without loading the entire file into RAM. Rejects pathlib.read_bytes(), read_text(), and f.read() on files of unknown or large size.
---

# High-Efficiency File Processing (mmap)

When writing Python code to read or search files, follow these mandatory rules:

1. **Reject Global Reads** — Never use `pathlib.read_bytes()`, `read_text()`, or `f.read()` on files of unknown or large size.
2. **Prefer Memory Mapping** — Use the `mmap` module. The OS handles demand paging; only accessed pages load into RAM.
3. **Delimiter Search** — Use `mm.find(delimiter)` or `mm.rfind()` instead of manual loops or regex on raw strings.
4. **Binary Mode** — Always open files in `rb` mode for mapping.
5. **Memory Safety** — Always use `with` statements for both the file object and the `mmap` object.

## Pattern: Read Until Delimiter

```python
import mmap
import os

def read_to_delimiter(file_path: str, delimiter: bytes = b'\n') -> bytes:
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return b""
    with open(file_path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            pos = mm.find(delimiter)
            return bytes(mm[:pos]) if pos != -1 else bytes(mm[:])
```

## Pattern: Search Without Loading

```python
def find_all_positions(file_path: str, needle: bytes) -> list[int]:
    positions = []
    with open(file_path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            start = 0
            while (pos := mm.find(needle, start)) != -1:
                positions.append(pos)
                start = pos + len(needle)
    return positions
```

## When mmap Is NOT Appropriate

- Files under ~1MB where full read is clearly acceptable
- Files opened for writing/appending (use `mmap.ACCESS_WRITE` only when in-place mutation is required)
- Network streams or pipes (mmap requires a real file descriptor with `fileno()`)
