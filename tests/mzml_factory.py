"""Write small synthetic mzML files for builder tests (no extra deps)."""
import base64
from pathlib import Path

import numpy as np


def _array(values, accession, name):
    data = base64.b64encode(np.asarray(values, dtype="<f8").tobytes()).decode()
    return f"""<binaryDataArray encodedLength="{len(data)}">
<cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/>
<cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>
<cvParam cvRef="MS" accession="{accession}" name="{name}"/>
<binary>{data}</binary></binaryDataArray>"""


def spectrum_xml(index, *, ms_level=2, polarity="positive", rt_min=1.0, precursor_mz=None,
                 precursor_intensity=None, isolation=(0.5, 0.5), collision_energy=20.0,
                 mz=(100.0,), intensity=(1000.0,), centroid=True, tic=None):
    pol = ("MS:1000130", "positive scan") if polarity == "positive" else ("MS:1000129", "negative scan")
    mode = ("MS:1000127", "centroid spectrum") if centroid else ("MS:1000128", "profile spectrum")
    tic = float(np.sum(intensity)) if tic is None else tic
    precursor = ""
    if ms_level == 2:
        intensity_param = (f'<cvParam cvRef="MS" accession="MS:1000042" name="peak intensity" value="{precursor_intensity}"/>'
                           if precursor_intensity is not None else "")
        precursor = f"""<precursorList count="1"><precursor>
<isolationWindow>
<cvParam cvRef="MS" accession="MS:1000827" name="isolation window target m/z" value="{precursor_mz}"/>
<cvParam cvRef="MS" accession="MS:1000828" name="isolation window lower offset" value="{isolation[0]}"/>
<cvParam cvRef="MS" accession="MS:1000829" name="isolation window upper offset" value="{isolation[1]}"/>
</isolationWindow>
<selectedIonList count="1"><selectedIon>
<cvParam cvRef="MS" accession="MS:1000744" name="selected ion m/z" value="{precursor_mz}"/>{intensity_param}
</selectedIon></selectedIonList>
<activation><cvParam cvRef="MS" accession="MS:1000422" name="beam-type collision-induced dissociation"/>
<cvParam cvRef="MS" accession="MS:1000045" name="collision energy" value="{collision_energy}"/></activation>
</precursor></precursorList>"""
    return f"""<spectrum index="{index}" id="scan={index + 1}" defaultArrayLength="{len(mz)}">
<cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="{ms_level}"/>
<cvParam cvRef="MS" accession="{pol[0]}" name="{pol[1]}"/>
<cvParam cvRef="MS" accession="{mode[0]}" name="{mode[1]}"/>
<cvParam cvRef="MS" accession="MS:1000285" name="total ion current" value="{tic}"/>
<scanList count="1"><scan>
<cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="{rt_min}" unitCvRef="UO" unitAccession="UO:0000031" unitName="minute"/>
</scan></scanList>
{precursor}
<binaryDataArrayList count="2">
{_array(mz, "MS:1000514", "m/z array")}
{_array(intensity, "MS:1000515", "intensity array")}
</binaryDataArrayList></spectrum>"""


def write_mzml(path: Path, spectra: list[dict]) -> Path:
    """``spectra``: kwargs for :func:`spectrum_xml`, one dict per scan."""
    body = "\n".join(spectrum_xml(i, **s) for i, s in enumerate(spectra))
    Path(path).write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<mzML xmlns="http://psi.hupo.org/ms/mzml" version="1.1.0">
<cvList count="2"><cv id="MS" fullName="PSI-MS" URI="" version="4"/><cv id="UO" fullName="Unit" URI=""/></cvList>
<run id="r1"><spectrumList count="{len(spectra)}">
{body}
</spectrumList></run></mzML>""")
    return Path(path)
