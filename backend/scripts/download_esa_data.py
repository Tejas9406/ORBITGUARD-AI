import hashlib
import time
import urllib.request
from pathlib import Path

DEST_DIR = Path("data/external/esa_opssat")
DEST_DIR.mkdir(parents=True, exist_ok=True)

DATASET_CSV_URL = "https://zenodo.org/records/15108715/files/dataset.csv?download=1"
SEGMENTS_CSV_URL = "https://zenodo.org/records/15108715/files/segments.csv?download=1"

def download_file(url: str, dest_path: Path):
    print(f"Downloading {url} to {dest_path}...")
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "OrbitGuard-AI/1.0"})
    
    with urllib.request.urlopen(req, timeout=120) as resp:
        total_size = resp.headers.get("Content-Length")
        total_size = int(total_size) if total_size else None
        
        hasher = hashlib.sha256()
        bytes_read = 0
        
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                hasher.update(chunk)
                bytes_read += len(chunk)
                if total_size:
                    pct = (bytes_read / total_size) * 100
                    print(f"\r  Progress: {bytes_read:,} / {total_size:,} bytes ({pct:.1f}%)", end="", flush=True)
                else:
                    print(f"\r  Progress: {bytes_read:,} bytes", end="", flush=True)
                    
    elapsed = time.time() - t0
    sha256 = hasher.hexdigest()
    print(f"\n  Finished in {elapsed:.2f}s | Size: {bytes_read:,} bytes | SHA-256: {sha256}")
    return bytes_read, sha256

if __name__ == "__main__":
    # 1. Download dataset.csv (~507 KB)
    dataset_dest = DEST_DIR / "dataset.csv"
    if not dataset_dest.is_file() or dataset_dest.stat().st_size == 0:
        download_file(DATASET_CSV_URL, dataset_dest)
    else:
        print(f"dataset.csv already exists ({dataset_dest.stat().st_size:,} bytes).")

    # 2. Download segments.csv (~18.9 MB)
    segments_dest = DEST_DIR / "segments.csv"
    if not segments_dest.is_file() or segments_dest.stat().st_size == 0:
        download_file(SEGMENTS_CSV_URL, segments_dest)
    else:
        print(f"segments.csv already exists ({segments_dest.stat().st_size:,} bytes).")
