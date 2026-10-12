"""الأرشيفات — فك ضغط وإعادة تجميع (ZIP / 7z / TAR / TAR.GZ) محليًا."""
import io
import os
import tempfile
import zipfile


def read_archive(data: bytes, src: str):
    files = []
    if src == "zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if not name.endswith("/"):
                    files.append((os.path.basename(name), z.read(name)))
    elif src in ("tar", "tar.gz", "tar.bz2", "tgz"):
        import tarfile
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
            for m in t.getmembers():
                f = t.extractfile(m)
                if m.isfile() and f:
                    files.append((os.path.basename(m.name), f.read()))
    elif src == "7z":
        import py7zr
        tmpdir = tempfile.mkdtemp(prefix="7z_")
        try:
            with py7zr.SevenZipFile(io.BytesIO(data)) as a:
                a.extractall(tmpdir)
            for root, _, fs in os.walk(tmpdir):
                for fn in fs:
                    p = os.path.join(root, fn)
                    with open(p, "rb") as f:
                        files.append((fn, f.read()))
        finally:
            for root, _, fs in os.walk(tmpdir, topdown=False):
                for fn in fs:
                    os.unlink(os.path.join(root, fn))
                os.rmdir(root)
    else:
        raise ValueError(f"أرشيف غير مدعوم: {src}")
    return files


def write_archive(files: list, dst: str) -> bytes:
    buf = io.BytesIO()
    if dst == "zip":
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files:
                z.writestr(name, data)
    elif dst in ("tar", "tar.gz", "tgz"):
        import tarfile
        mode = "w:gz" if "gz" in dst or dst == "tgz" else "w"
        with tarfile.open(fileobj=buf, mode=mode) as t:
            for name, data in files:
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
    elif dst == "7z":
        import py7zr
        tmpdir = tempfile.mkdtemp(prefix="arch_")
        try:
            paths = []
            for i, (name, data) in enumerate(files):
                safe = f"{i}-{os.path.basename(name)}"
                p = os.path.join(tmpdir, safe)
                with open(p, "wb") as f:
                    f.write(data)
                paths.append((p, safe))
            with py7zr.SevenZipFile(buf, "w") as a:
                for p, arcname in paths:
                    a.write(p, arcname)
        finally:
            for root, _, fs in os.walk(tmpdir, topdown=False):
                for f in fs:
                    os.unlink(os.path.join(root, f))
            os.rmdir(tmpdir)
    else:
        raise ValueError(f"صيغة أرشيف غير مدعومة: {dst}")
    return buf.getvalue()
