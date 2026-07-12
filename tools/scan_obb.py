import struct, gzip

obb_path = r'C:\Users\Hakuhiro\AppData\Local\Temp\opencode\ff4_apk_v13\assets\main.obb'
with open(obb_path, 'rb') as f:
    data = f.read()

a = 0x41C64E6D; c = 0x3039
BASE_KEY = 98910408
init_state = 0xE0152233
xform = init_state ^ 98910408

def decrypt(data_bytes, init):
    state = init & 0xFFFFFFFF
    result = bytearray()
    for b in data_bytes:
        state = (state * a + c) & 0xFFFFFFFF
        result.append(b ^ ((state >> 24) & 0xFF))
    return bytes(result)

print('=== Decrypting header ===')
dec_header = decrypt(data[:16], init_state)
print(f'Header hex: {dec_header.hex()}')
magic = struct.unpack_from('<I', dec_header, 0)[0]
print(f'Magic: 0x{magic:08X}')

# Print all possible interpretations
for name, fmt, pos in [
    ('[4-7] LE int', '<I', 4), ('[8-11] LE int', '<I', 8), ('[12-15] LE int', '<I', 12),
    ('[4-5] LE short', '<H', 4), ('[6-7] LE short', '<H', 6),
    ('[8-9] LE short', '<H', 8), ('[10-11] LE short', '<H', 10),
    ('[12-13] LE short', '<H', 12), ('[14-15] LE short', '<H', 14),
    ('[0-3] BE int', '>I', 0), ('[4-7] BE int', '>I', 4),
    ('[8-11] BE int', '>I', 8), ('[12-15] BE int', '>I', 12),
]:
    val = struct.unpack_from(fmt, dec_header, pos)[0]
    print(f'  {name}: 0x{val:08X} ({val})')

# Try decrypting at various positions with various init formulas
print('\n=== Scanning for GZIP headers in first 100KB ===')
found = []
for off in range(0, 100000, 16):
    for name, init_fn in [
        ('init=key+off', lambda o: (BASE_KEY + o) & 0xFFFFFFFF),
        ('init=key', lambda o: BASE_KEY & 0xFFFFFFFF),
        ('init=(key+off)^xform', lambda o: ((BASE_KEY + o) ^ xform) & 0xFFFFFFFF),
        ('init=0xE0152233', lambda o: 0xE0152233),
    ]:
        init = init_fn(off)
        chunk = decrypt(data[off:off+64], init)
        if len(chunk) >= 6 and chunk[4] == 0x1F and chunk[5] == 0x8B:
            try:
                decomp = gzip.decompress(chunk[4:])
                found.append((off, name, init, len(decomp), decomp[:80]))
            except:
                pass

if found:
    print(f'Found {len(found)} GZIP streams:')
    for off, name, init, dlen, preview in found:
        print(f'  off={off} ({off:#x}), {name}, init=0x{init:08X}, decomp_size={dlen}')
        print(f'    Preview: {preview}')
else:
    print('No GZIP streams found in first 100KB')
    
    # Last resort: try different transforms systematically  
    print('\n=== Trying all init_state transforms at offset 16 ===')
    test_off = 16
    for transform in range(256):
        # Try: init = ((key+off) + transform) % 2^32
        init = ((BASE_KEY + test_off + transform * 256 * 256 * 256)) & 0xFFFFFFFF
        chunk = decrypt(data[test_off:test_off+64], init)
        if len(chunk) >= 6 and chunk[4] == 0x1F and chunk[5] == 0x8B:
            print(f'  TRANSFORM FOUND: add={transform * 256**3}, init=0x{init:08X}')
            try:
                decomp = gzip.decompress(chunk[4:])
                print(f'  Decompressed: {len(decomp)} bytes: {decomp[:100]}')
            except Exception as e:
                print(f'  GZIP failed: {e}')
            break
    else:
        print('  No transform found')
