"""
FF4: The After Years OBB Extractor
==================================
Decrypts and extracts ALL 9,373 files from the Android APK's main.obb archive.

Encryption: LCG XOR stream cipher (glibc rand constants)
  seed = (98910408 + offset)
  seed = seed * 0x41C64E6D + 12345 (mod 2^32)
  byte ^= (seed >> 24) & 0xFF

Archive format: [4B BE size] + [GZip data]

Usage:
  python extract_obb.py <main.obb> [output_dir]
"""
import struct, zlib, os, sys

# ── Crypto ──────────────────────────────────────────────────────────────────

OBB_SEED_BASE = 98910408
OBB_LCG_MUL   = 0x41C64E6D
OBB_LCG_ADD   = 12345
OBB_MAGIC     = 0x31435241  # "ARC1"

def obb_decode(buf, seed):
    data = bytearray(buf)
    for i in range(len(data)):
        seed = (seed * OBB_LCG_MUL + OBB_LCG_ADD) & 0xFFFFFFFF
        data[i] ^= (seed >> 24) & 0xFF
    return bytes(data)

def rd_le32(p): return struct.unpack_from('<I', p, 0)[0]
def rd_be32(p): return struct.unpack_from('>I', p, 0)[0]

def unwrap(blob):
    """Decompress [BE32 size][gzip]"""
    if len(blob) < 4:
        return None
    return zlib.decompress(bytes(blob[4:]), 16 + zlib.MAX_WBITS)

# ── Main ────────────────────────────────────────────────────────────────────

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

obb_path = sys.argv[1]
out_root = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(obb_path)[0] + '_extracted'

print(f"OBB: {obb_path}")
print(f"Output: {out_root}")

with open(obb_path, 'rb') as f:
    # Header: 16 bytes, XOR with seed = BASE + 0
    hdr = obb_decode(f.read(16), OBB_SEED_BASE)
    assert rd_le32(hdr) == OBB_MAGIC, f"Bad magic: 0x{rd_le32(hdr):08X}"
    toc_off = rd_le32(hdr[8:12])
    toc_len = rd_le32(hdr[12:16])
    print(f"TOC at offset {toc_off}, {toc_len} bytes")

    # TOC: XOR with seed = BASE + toc_off, then GZip
    toc_raw = f.read(toc_len)
    f.seek(toc_off)
    toc_raw = f.read(toc_len)
    toc = unwrap(obb_decode(toc_raw, OBB_SEED_BASE + toc_off))
    assert toc, "TOC decompression failed"
    count = rd_le32(toc)
    print(f"{count} entries in TOC")

    # Parse entries: {name_off(LE32), file_off(LE32), file_len(LE32)}
    entries = []
    for i in range(count):
        e = 4 + i * 12
        name_off = rd_le32(toc[e:e+4])
        file_off = rd_le32(toc[e+4:e+8])
        file_len = rd_le32(toc[e+8:e+12])
        end = toc.index(b'\0', name_off)
        name = toc[name_off:end].decode('utf-8', errors='replace')
        entries.append((name, file_off, file_len))

    # Directory stats
    dirs = {}
    langs = {}
    for name, off, length in entries:
        d = os.path.dirname(name)
        dirs[d] = dirs.get(d, 0) + 1
        parts = name.replace('\\', '/').split('/')
        for p in parts:
            if p.endswith('.lproj'):
                lang = p.replace('.lproj', '')
                langs[lang] = langs.get(lang, 0) + 1

    print(f"\nDirectories: {len(dirs)}")
    for d, n in sorted(dirs.items(), key=lambda x: x[0]):
        print(f"  {d}/  ({n} files)")

    print(f"\nLanguages found: {len(langs)}")
    for lang, n in sorted(langs.items()):
        print(f"  {lang}: {n} files")

    # Extract all files
    extracted = 0
    failed = 0
    for name, off, length in entries:
        out_path = os.path.join(out_root, name.replace('\\', '/'))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        try:
            f.seek(off)
            raw = f.read(length)
            decoded = unwrap(obb_decode(raw, OBB_SEED_BASE + off))
            if decoded:
                with open(out_path, 'wb') as of:
                    of.write(decoded)
                extracted += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1

        if extracted % 1000 == 0:
            print(f"  {extracted}/{count} files...", end='\r')

    print(f"\n\nDone: {extracted} extracted, {failed} failed")
    print(f"Output: {out_root}")
