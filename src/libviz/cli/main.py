"""``libviz`` command line: the core operations without the GUI
(convert, build, export, merge, info)."""
import argparse
import logging
import sys
from pathlib import Path

from libviz.core import builder
from libviz.core.library import Library
from libviz.core.writers import write_msp
from libviz.core.utils.logging_utils import configure_logging


def _progress(label: str):
    def report(done: int, total: int):
        if total:
            print(f"\r{label}: {done / total:6.1%}", end="", file=sys.stderr, flush=True)
    return report


def _open_or_create(path: Path, name: str | None) -> Library:
    if path.exists():
        return Library.load_from_db(path)
    lib = Library.create(path, name=name or path.stem)
    lib.is_temp = False
    return lib


def cmd_convert(args) -> int:
    out = args.output or args.msp.with_suffix(".db")
    if out.exists() and not args.force:
        print(f"{out} exists (use --force to overwrite)", file=sys.stderr)
        return 1
    lib = Library.load_from_msp(args.msp, default_precursor_type=args.default_adduct,
                                progress=_progress("Importing"))
    print(file=sys.stderr)
    if args.name:
        lib.rename_library(args.name)
    lib.save_as_db(out)
    print(f"{out}: {lib.n_compounds} compounds, {lib.n_spectra} spectra")
    lib.close()
    return 0


def cmd_build(args) -> int:
    targets = builder.parse_targets(args.targets)
    params = builder.BuildParams(
        ppm=args.ppm,
        positive_adducts=tuple(args.positive_adducts),
        negative_adducts=tuple(args.negative_adducts),
        dia_min_width=args.dia_min_width,
        min_relative_intensity=args.min_relative_intensity / 100,
        remove_precursor=args.remove_precursor,
        min_peaks=args.min_peaks,
        normalize=not args.no_normalize,
        rank_by=args.rank_by,
    )
    result = builder.find_candidates(targets, args.mzml, params, progress=_progress("Scanning"))
    print(file=sys.stderr)
    if not args.include_multiplexed:
        for group in result.groups:
            if group.chosen is not None and group.candidates[group.chosen].multiplexed:
                group.chosen = None
    found = {g.target_index for g in result.groups if g.chosen is not None}
    print(f"{result.n_ms2} MS2 scans, {result.n_chosen} spectra for {len(found)}/{len(targets)} targets")
    for i, target in enumerate(targets):
        if i not in found:
            print(f"  no MS2: {target.name}")
    if args.dry_run:
        return 0
    lib = _open_or_create(args.output, args.name)
    counts = builder.commit(lib, result, on_conflict="replace" if args.replace else "skip")
    print(f"{args.output}: added {counts['added']}, replaced {counts['replaced']}, skipped {counts['skipped']}")
    return 0


def cmd_export(args) -> int:
    lib = Library.load_from_db(args.library)
    out = args.output or args.library.with_suffix(".msp")
    n = write_msp(lib, out, progress=_progress("Exporting"))
    print(file=sys.stderr)
    print(f"{out}: {n} spectra")
    return 0


def cmd_merge(args) -> int:
    lib = _open_or_create(args.target, None)
    for source in args.sources:
        counts = lib.merge_from(source)
        print(f"{source}: +{counts['spectra_added']} spectra (+{counts['compounds_added']} compounds), "
              f"{counts['spectra_skipped']} identical skipped")
    print(f"{args.target}: {lib.n_compounds} compounds, {lib.n_spectra} spectra")
    return 0


def cmd_info(args) -> int:
    lib = Library.load_from_db(args.library)
    options = lib.filter_options()
    print(f"{lib.name}\n  {lib.n_compounds} compounds, {lib.n_spectra} spectra")
    print(f"  polarities: {', '.join(options['polarities']) or '-'}")
    print(f"  adducts: {', '.join(options['adducts']) or '-'}")
    print(f"  collision energies: {', '.join(f'{e:g}' for e in options['collision_energies']) or '-'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="libviz", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert", help="MSP file -> LibViz .db")
    p.add_argument("msp", type=Path)
    p.add_argument("-o", "--output", type=Path, help="default: next to the MSP, .db")
    p.add_argument("--name", help="library name (default: file name)")
    p.add_argument("--default-adduct", default="[M+H]+", help="for entries without PRECURSORTYPE")
    p.add_argument("-f", "--force", action="store_true", help="overwrite the output")
    p.set_defaults(func=cmd_convert)

    defaults = builder.BuildParams()
    p = sub.add_parser("build", help="target list + mzML files -> library spectra (best scan per compound/adduct/CE)")
    p.add_argument("targets", type=Path, help="CSV/TSV: name, formula, inchikey [, smiles, pubchem_id, adducts, rt | rt_min, rt_max]")
    p.add_argument("mzml", type=Path, nargs="+")
    p.add_argument("-o", "--output", type=Path, required=True, help="library .db (created if missing)")
    p.add_argument("--name", help="name of a newly created library")
    p.add_argument("--ppm", type=float, default=defaults.ppm)
    p.add_argument("--positive-adducts", nargs="+", default=list(defaults.positive_adducts))
    p.add_argument("--negative-adducts", nargs="+", default=list(defaults.negative_adducts))
    p.add_argument("--dia-min-width", type=float, default=defaults.dia_min_width,
                   help="isolation windows at least this wide (m/z) are treated as DIA")
    p.add_argument("--include-multiplexed", action="store_true", help="also add DIA (multiplexed) spectra")
    p.add_argument("--min-relative-intensity", type=float, default=defaults.min_relative_intensity * 100,
                   help="percent of the base peak")
    p.add_argument("--remove-precursor", action="store_true")
    p.add_argument("--min-peaks", type=int, default=defaults.min_peaks)
    p.add_argument("--no-normalize", action="store_true", help="keep raw intensities")
    p.add_argument("--rank-by", choices=builder.RANK_BY, default=defaults.rank_by)
    p.add_argument("--replace", action="store_true", help="replace existing spectra with the same key")
    p.add_argument("-n", "--dry-run", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("export", help="LibViz .db -> MSP")
    p.add_argument("library", type=Path)
    p.add_argument("-o", "--output", type=Path, help="default: next to the library, .msp")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("merge", help="copy libraries into TARGET (created if missing), skipping identical spectra")
    p.add_argument("target", type=Path)
    p.add_argument("sources", type=Path, nargs="+")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("info", help="summary of a library")
    p.add_argument("library", type=Path)
    p.set_defaults(func=cmd_info)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(level=logging.DEBUG if args.verbose else logging.WARNING)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
