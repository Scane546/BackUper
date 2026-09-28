import struct
import io
from PIL import Image

SRC = "asets/img_10982.png"   # исходник (256/512 px, с прозрачностью)
OUT = "Backuper.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def make_ico(src, out, sizes):
    img = Image.open(src).convert("RGBA")
    entries = []
    for s in sizes:
        im = img.resize((s, s), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        entries.append((s, buf.getvalue()))

    out_bytes = struct.pack("<HHH", 0, 1, len(entries))
    pos = 6 + 16 * len(entries)
    for s, png in entries:
        out_bytes += struct.pack(
            "<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(png), pos
        )
        pos += len(png)
    for s, png in entries:
        out_bytes += png

    with open(out, "wb") as f:
        f.write(out_bytes)
    print("saved", out, "sizes:", sizes)


if __name__ == "__main__":
    make_ico(SRC, OUT, SIZES)
