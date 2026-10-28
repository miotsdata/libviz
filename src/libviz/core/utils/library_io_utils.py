from collections.abc import Generator
from pathlib import Path


def parse_msp(file_path: Path, progress=None) -> Generator[dict, None, None]:
    """Yield one dict per MSP entry. ``progress(done, total)`` (optional)
    is called every 50k lines with approximate characters read / file size."""
    total = Path(file_path).stat().st_size if progress else 0
    done = 0
    with open(file_path, "r", encoding="utf-8") as f:
        entry_lines = []

        for n, line in enumerate(f, start=1):
            if progress:
                done += len(line)
                if n % 50_000 == 0:
                    progress(min(done, total), total)
            line = line.rstrip()

            if line == "":  # blank line = end of entry
                if entry_lines:
                    yield _parse_entry(entry_lines)
                    entry_lines = []
            else:
                entry_lines.append(line)

        # last entry (EOF without blank line)
        if entry_lines:
            yield _parse_entry(entry_lines)


def _parse_entry(lines):
    data = {}
    peaks = []
    in_peaks = False

    for line in lines:
        if in_peaks:
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    peaks.append((parts[0], parts[1]))
            continue

        # MSP uses both : and = as separators
        for sep in (":", "="):
            if sep in line:
                key, value = line.split(sep, 1)
                key = key.strip().upper()
                value = value.strip()
                if key in ("NUM PEAKS", "NUMPEAKS", "NUM_PEAKS"):
                    in_peaks = True
                else:
                    data[key] = value
                break

    if peaks:
        data["peaks"] = peaks

    return data
