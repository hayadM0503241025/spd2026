"""Create a source-only ZIP without reference workbooks, sessions or environments."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
output=root/'outputs'/'studio-dashboard-desa.zip'
output.parent.mkdir(exist_ok=True)
files=[root/name for name in ('app.py','requirements.txt','requirements-dev.txt','.gitignore','README.md','TESTING.md','.streamlit/config.toml','.streamlit/secrets.example.toml')]
for directory in ('studio','data','tests'):
    files.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.extend(root/'tools'/name for name in ('prepare_shared.py','create_examples.py','configure_access.py','package_project.py'))
with ZipFile(output,'w',ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path,path.relative_to(root).as_posix())
with ZipFile(output) as archive:
    assert archive.testzip() is None
    assert not any(name.endswith(('.xlsx','.pptx','.pyc')) for name in archive.namelist())
    assert '.streamlit/secrets.toml' not in archive.namelist()
    assert not any(name.startswith('runtime/') or name.endswith(('.db','.sqlite3')) for name in archive.namelist())
print(f'{output.name}: {len(files)} berkas, {output.stat().st_size} byte')
