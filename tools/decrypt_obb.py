"""
FF4 TAY OBB Decryptor - Full implementation
"""
import struct
import gzip
import io
import os

obb_path = r'C:\Users\Hakuhiro\AppData\Local\Temp\opencode\ff4_apk\assets\main.obb'
out_dir = r'C:\Users\Hakuhiro\AppData\Local\Temp\opencode\ff4_decrypted'

with open(obb_path, 'rb') as f:
    data = bytearray(f.read())

a = 0x41C64E6D
c = 0x3039
init_state = 0xE0152233

# Verify header decryption
state = init_state & 0xFFFFFFFF
dec_header = bytearray()
for i in range(16):
    state = (state * a + c) & 0xFFFFFFFF
    xor_byte = (state >> 24) & 0xFF
    dec_header.append(data[i] ^ xor_byte)

print('Decrypted header:', dec_header.hex())
magic = struct.unpack_from('<I', dec_header, 0)[0]
print(f'Magic: 0x{magic:08X} (expected 0x31415941)')
assert magic == 0x31415941, "Magic mismatch!"

offset = struct.unpack_from('<I', dec_header, 8)[0]
size = struct.unpack_from('<I', dec_header, 12)[0]
print(f'Index: offset={offset}, size={size}')

# Now try to decrypt the index
# We need to find the init_state for the index data
# The index is encrypted with key = offset + 98910408
# But we need to find the mapping from key to init_state

print(f'\nKey for index: {offset + 98910408}')

# For the header: key=98910408 -> init_state=0xE0152233
# Let's try to find this mapping by testing

# Maybe init_state is simply XOR with a constant?
xform_const = init_state ^ 98910408
print(f'Transform constant (XOR): 0x{xform_const:08X}')
# Test: init_state_index = (offset + 98910408) ^ xform_const
test_init_index = (offset + 98910408) ^ xform_const
print(f'Test init_state for index: 0x{test_init_index:08X}')

# Try decrypting the index
enc_index = data[offset:offset + size]
state = test_init_index & 0xFFFFFFFF
dec_index = bytearray()
for i in range(len(enc_index)):
    state = (state * a + c) & 0xFFFFFFFF
    xor_byte = (state >> 24) & 0xFF
    dec_index.append(enc_index[i] ^ xor_byte)

print(f'Decrypted index first 16 bytes: {dec_index[:16].hex()}')

# Check if it starts with a valid GZIP-sized header
# Format: [4 bytes decompressed size] [GZIP data starting with 0x1F 0x8B]
decomp_size = struct.unpack_from('<I', dec_index, 0)[0]
print(f'Decompressed size: {decomp_size}')
print(f'Bytes at [4:6]: {dec_index[4]:02X} {dec_index[5]:02X} (expected 1F 8B for GZIP)')

if dec_index[4] == 0x1F and dec_index[5] == 0x8B:
    print('GZIP magic found! Attempting decompression...')
    try:
        gzip_data = bytes(dec_index[4:])
        decompressed = gzip.decompress(gzip_data)
        print(f'Decompressed successfully! Size: {len(decompressed)} bytes')
        print(f'First 100 bytes: {decompressed[:100]}')
        
        # Save decompressed index
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'index.bin'), 'wb') as f:
            f.write(decompressed)
        print(f'Saved index to {out_dir}/index.bin')
        
        # Now parse the index to extract individual files
        # Index format: each entry is 12 bytes
        # [0-3]: file offset? [4-7]: ? [8-11]: ?
        # Actually from Java: entries have filename + metadata
        # Each entry starts with a null-terminated filename
        print('\n=== Index Structure ===')
        print(f'Total index size: {len(decompressed)} bytes')
        num_entries = struct.unpack_from('<I', decompressed, 0)[0]
        print(f'Number of entries: {num_entries}')
        
        # Parse entries
        entries = []
        for i in range(num_entries):
            entry_offset = 4 + i * 12  # Each entry is 12 bytes
            if entry_offset + 12 > len(decompressed):
                break
            val0 = struct.unpack_from('<I', decompressed, entry_offset)[0]
            val4 = struct.unpack_from('<I', decompressed, entry_offset + 4)[0]
            val8 = struct.unpack_from('<I', decompressed, entry_offset + 8)[0]
            entries.append((val0, val4, val8))
        
        print(f'\nParsed {len(entries)} entries:')
        for idx, (v0, v4, v8) in enumerate(entries[:20]):
            print(f'  [{idx}] offset=0x{v0:08X} ({v0}), field4={v4}, field8={v8}')
        
        # Now we can extract individual files!
        # From Java code (i method): v0 = file offset, v4 = file size (?)
        # Actually looking at i() method more carefully:
        # e(F, i2) = file offset, e(F, i2+4) = file size
        # So v0 = offset, v4 = size
        
        print(f'\n=== Extracting files ===')
        xform_index = (offset + 98910408) ^ xform_const
        for idx, (file_off, file_size, _) in enumerate(entries[:5]):
            print(f'\nFile {idx}: offset=0x{file_off:08X}, size={file_size}')
            
            # Read encrypted file data
            if file_off + file_size > len(data):
                print(f'  SKIP: out of bounds')
                continue
            enc_file = data[file_off:file_off + file_size]
            
            # Decrypt with key = file_off + 98910408
            file_init = (file_off + 98910408) ^ xform_const
            state = file_init & 0xFFFFFFFF
            dec_file = bytearray()
            for j in range(len(enc_file)):
                state = (state * a + c) & 0xFFFFFFFF
                xor_byte = (state >> 24) & 0xFF
                dec_file.append(enc_file[j] ^ xor_byte)
            
            # Check for GZIP header
            if len(dec_file) > 6 and dec_file[4] == 0x1F and dec_file[5] == 0x8B:
                try:
                    gzip_data = bytes(dec_file[4:])
                    decompressed = gzip.decompress(gzip_data)
                    print(f'  Decompressed size: {len(decompressed)} bytes')
                    print(f'  First 64 bytes: {decompressed[:64]}')
                    # Save
                    fname = f'file_{idx:04d}.bin'
                    with open(os.path.join(out_dir, fname), 'wb') as f:
                        f.write(decompressed)
                    print(f'  Saved to {fname}')
                except Exception as e:
                    print(f'  GZIP decompression failed: {e}')
            else:
                print(f'  Raw decrypted first 16: {dec_file[:16].hex()}')
    except Exception as e:
        print(f'GZIP decompression failed: {e}')
        print(f'Raw first 64 bytes: {dec_index[:64].hex()}')
else:
    print('No GZIP magic found - trying different init_state transforms...')
    
    # Try different transforms
    for transform_name, transform_fn in [
        ('XOR with const', lambda k: k ^ xform_const),
        ('XOR with const+offset', lambda k: k ^ (xform_const + k - 98910408)),
        ('Same as header', lambda k: init_state),
    ]:
        test = transform_fn(offset + 98910408) & 0xFFFFFFFF
        state = test
        dec = bytearray()
        for i in range(min(len(enc_index), 32)):
            state = (state * a + c) & 0xFFFFFFFF
            dec.append(enc_index[i] ^ ((state >> 24) & 0xFF))
        print(f'  {transform_name}: init=0x{test:08X}, first bytes={dec[:8].hex()}')
