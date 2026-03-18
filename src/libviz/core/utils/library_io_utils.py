from pathlib import Path


def parse_msp(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        entry_lines = []

        for line in f:
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

    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
        else:
            peaks.append(line.strip().split())

    if peaks:
        data["peaks"] = peaks

    return data
