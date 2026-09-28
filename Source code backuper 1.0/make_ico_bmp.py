import struct
from PIL import Image

SRC = "asets/Backuper.ico"
OUT = "Backuper.ico"
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def bmp_rgba(img):
    w, h = img.size
    px = img.load()
    xor = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = px[x, y]
            xor += bytes((b, g, r, a))
    stride = ((w + 31) // 32) * 4
    mask = bytearray()
    cur = 0
    cnt = 0
    for y in range(h - 1, -1, -1):
        for x in range(w):
            bit = 0 if px[x, y][3] < 128 else 1
            cur = (cur << 1) | bit
            cnt += 1
            if cnt == 8:
                mask.append(cur & 0xFF)
                cur = 0
                cnt = 0
        if cnt:
            mask.append((cur << (8 - cnt)) & 0xFF)
            cur = 0
            cnt = 0
        while len(mask) % stride != 0:
            mask.append(0)
    header = struct.pack(
        "<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0
    )
    return header + bytes(xor), bytes(mask)


img = Image.open(SRC).convert("RGBA")
entries = []
for s in SIZES:
    im = img.resize((s, s), Image.LANCZOS)
    entries.append((s, bmp_rgba(im)[0] + bmp_rgba(im)[1]))

out = struct.pack("<HHH", 0, 1, len(entries))
pos = 6 + 16 * len(entries)
for s, blob in entries:
    out += struct.pack(
        "<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(blob), pos
    )
    pos += len(blob)
for s, blob in entries:
    out += blob

with open(OUT, "wb") as f:
    f.write(out)
print("wrote", OUT, "sizes", SIZES)
