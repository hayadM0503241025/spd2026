"""Only trusted, versioned prepared files can become the shared baseline."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import hashlib
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _matches_csv_hash(payload: bytes, expected: str) -> bool:
    """Accept Git's LF/CRLF checkout conversion while checking all CSV content."""
    lf_payload = payload.replace(b'\r\n', b'\n')
    crlf_payload = lf_payload.replace(b'\n', b'\r\n')
    return any(
        hashlib.sha256(candidate).hexdigest() == expected
        for candidate in (payload, lf_payload, crlf_payload)
    )


class DatasetError(ValueError):
    pass


@dataclass(frozen=True)
class SharedBundle:
    # Immutable bytes, not globally shared mutable DataFrames.
    metadata_json: str
    payloads: tuple[tuple[str, bytes], ...]

    @property
    def manifest(self):
        return json.loads(self.metadata_json)

    @property
    def version(self):
        return self.manifest['version']

    @property
    def ids(self):
        return tuple(k for k, _ in self.payloads)

    def frame(self, dataset: str) -> pd.DataFrame:
        payload = next((v for k, v in self.payloads if k == dataset), None)
        if payload is None:
            raise DatasetError(f'Dataset {dataset} tidak tersedia pada versi ini.')
        spec = self.manifest['datasets'][dataset]
        frame = pd.read_csv(BytesIO(payload), dtype=spec['dtypes'])
        for column in spec['dates']:
            frame[column] = pd.to_datetime(frame[column], errors='coerce')
        return frame


def registry():
    return json.loads((ROOT / 'data' / 'registry.json').read_text(encoding='utf-8'))


def load_shared(version: str | None = None) -> SharedBundle:
    catalog = registry()
    version = version or catalog['current']
    if version not in catalog['versions']:
        raise DatasetError(f'Versi dataset {version} belum dipasang. Minta fasilitator memasang versi yang sesuai; data tidak diganti otomatis.')
    folder_name = catalog['versions'][version]
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', folder_name):
        raise DatasetError('Lokasi dataset tidak sah.')
    folder = ROOT / 'data' / 'shared' / folder_name
    manifest_text = (folder / 'manifest.json').read_text(encoding='utf-8')
    manifest = json.loads(manifest_text)
    if manifest['version'] != version:
        raise DatasetError('Versi pada manifest berbeda dari katalog.')
    payloads = []
    for dataset, spec in manifest['datasets'].items():
        if not re.fullmatch(r'[a-z]+\.csv', spec['file']):
            raise DatasetError('Nama berkas dataset tidak sah.')
        payload = (folder / spec['file']).read_bytes()
        if not _matches_csv_hash(payload, spec['sha256']):
            raise DatasetError(f'Integritas dataset {dataset} berubah. Siapkan versi baru; jangan menimpa versi lama.')
        payloads.append((dataset, payload))
    return SharedBundle(manifest_text, tuple(payloads))
