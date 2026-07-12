"""
OBB Decryption Script for FF4: The After Years Android
Based on decompiled Java code analysis:
- MainActivity.g() reads OBB header, calls encode(header, 98910408)
- Expected magic: 826495553 = 0x31415941 = [0x41, 0x59, 0x41, 0x31] ("AYA1")
- encode() is a native XOR function
"""
import struct
import sys

obb_path = r'C:\Users\Hakuhiro\AppData\Local\Temp\opencode\ff4_apk\assets\main.obb'
key = 98910408  # 0x05E53F28

with open(obb_path, 'rb') as f:
    data = bytearray(f.read())

# First 16 encrypted bytes
enc_header = data[:16]
print("Encrypted header (hex):", enc_header.hex())

# Expected after XOR: 0x41, 0x59, 0x41, 0x31 ("AYA1")
expected_header_start = bytes([0x41, 0x59, 0x41, 0x31])
print("Expected first 4 bytes:", expected_header_start.hex())

# Derive XOR bytes from encrypt+expected
xor_derived = bytes([enc_header[i] ^ expected_header_start[i] for i in range(4)])
print("Derived XOR (first 4):", xor_derived.hex())

# Try to find pattern between key and derived XOR
key_bytes_le = struct.pack('<I', key)
key_bytes_be = struct.pack('>I', key)
print(f"Key (LE bytes): {key_bytes_le.hex()} (int={key}, hex=0x{key:08X})")
print(f"Key (BE bytes): {key_bytes_be.hex()}")

# Test 1: LCG-based XOR (common in game engines)
# LCG parameters from glibc: a=1103515245, c=12345
print("\n=== Test 1: LCG XOR (glibc rand) ===")
def xor_lcg(data, seed, length):
    result = bytearray(data)
    a = 1103515245
    c = 12345
    state = seed & 0xFFFFFFFF
    for i in range(length):
        state = (state * a + c) & 0xFFFFFFFF
        result[i] ^= (state >> 16) & 0xFF
    return result

test = xor_lcg(enc_header, key, 16)
print("LCG XOR result:", bytes(test[:4]).hex())
if bytes(test[:4]) == expected_header_start:
    print("MATCH! LCG XOR works!")
else:
    print("No match")

# Test 2: LCG with different shift
print("\n=== Test 2: LCG XOR with different shifts ===")
for shift in range(0, 32, 8):
    def xor_lcg_shift(data, seed, length, sh):
        result = bytearray(data)
        a = 1103515245
        c = 12345
        state = seed & 0xFFFFFFFF
        for i in range(length):
            state = (state * a + c) & 0xFFFFFFFF
            result[i] ^= (state >> sh) & 0xFF
        return result
    test = xor_lcg_shift(enc_header, key, 16, shift)
    if bytes(test[:4]) == expected_header_start:
        print(f"MATCH! shift={shift}")
        break
else:
    print("No match with any shift")

# Test 3: Repeated 4-byte XOR (little-endian key)
print("\n=== Test 3: 4-byte LE repeated XOR ===")
def xor_repeat_le(data, key_bytes, length):
    result = bytearray(data)
    for i in range(length):
        result[i] ^= key_bytes[i % 4]
    return result
test = xor_repeat_le(enc_header, key_bytes_le, 16)
print("LE XOR result:", bytes(test[:4]).hex())
if bytes(test[:4]) == expected_header_start:
    print("MATCH!")
else:
    print("No match")

# Test 4: Repeated 4-byte XOR (big-endian key)
print("\n=== Test 4: 4-byte BE repeated XOR ===")
test = xor_repeat_le(enc_header, key_bytes_be, 16)
print("BE XOR result:", bytes(test[:4]).hex())
if bytes(test[:4]) == expected_header_start:
    print("MATCH!")
else:
    print("No match")

# Test 5: XOR with derived key as repeating pattern
print("\n=== Test 5: Derived key as repeating XOR ===")
test = xor_repeat_le(enc_header, xor_derived, 16)
print("Derived XOR result:", bytes(test[:4]).hex())
if bytes(test[:4]) == expected_header_start:
    print("MATCH!")
else:
    print("No match")

# Test 6: LCG with different LCG constants
print("\n=== Test 6: Try different LCG constants ===")
lcg_params = [
    (1103515245, 12345),    # glibc
    (214013, 2531011),      # MSVC
    (1664525, 1013904223),  # Numerical Recipes  
    (134775813, 1),         # Borland
]
for a, c in lcg_params:
    def test_lcg(data, seed, length, a_val, c_val):
        result = bytearray(data)
        state = seed & 0xFFFFFFFF
        for i in range(length):
            state = (state * a_val + c_val) & 0xFFFFFFFF
            result[i] ^= (state >> 16) & 0xFF
        return result
    for shift in [0, 8, 16, 24]:
        test = test_lcg(enc_header, key, 16, a, c)
        # modify for different shifts
        if bytes(test[:4]) == expected_header_start:
            print(f"MATCH! a={a}, c={c}, shift={shift}")
            break

# Test 7: Try XOR with key repeated per-byte (0x28, 0x28, 0x28...)
print("\n=== Test 7: Single byte repeated XOR ===")
for kb in key_bytes_le:
    test = bytearray(enc_header)
    for i in range(16):
        test[i] ^= kb
    if bytes(test[:4]) == expected_header_start:
        print(f"MATCH! byte=0x{kb:02X}")
        break
else:
    print("No match")

# Test 8: LCG but seed changes per-position
print("\n=== Test 8: LCG with reseeding ===")
for init_seed in range(256):
    state = (key + init_seed) & 0xFFFFFFFF
    a = 1103515245; c = 12345
    result = bytearray()
    for i in range(4):
        state = (state * a + c) & 0xFFFFFFFF
        b = enc_header[i] ^ ((state >> 16) & 0xFF)
        result.append(b)
    if bytes(result) == expected_header_start:
        print(f"MATCH! init_seed={init_seed}")
        break
else:
    print("No match")
