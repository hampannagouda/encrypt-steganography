"""
stego.py — DCT-domain steganography (Mid+High Frequency Band)
=============================================================
Usage:
    python stego.py encode  <enc_bin>   <cover_tpython -m pip install numpy opencv-python torch torchvision pillow tifffile scikit-imageif>  <output_dir>
    python stego.py decode  <stego_dir> <output_bin>
    python stego.py verify  <original_bin> <extracted_bin>
    python stego.py metrics <cover_tif>    <stego_tif>
"""

import sys
import os
import math
import struct
import gc
import glob
import re
import hashlib
import argparse

import numpy as np
import cv2
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

try:
    import tifffile
except ImportError:
    raise SystemExit("ERROR: Run 'pip install tifffile' first.")

try:
    from skimage.metrics import structural_similarity as ssim
except ImportError:
    ssim = None  # metrics command will warn if missing

Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------------------
# Global settings (Goldilocks mid-frequency band for >0.95 SSIM)
# ---------------------------------------------------------------------------
BLOCK_SIZE       = 8
CHUNK_SIZE       = 5120
COEFF_POSITIONS  = [(r, c) for r in range(4, 7) for c in range(4, 7)]  # 9 coeffs
BITS_PER_BLOCK   = len(COEFF_POSITIONS) * 3
QUANTIZATION_STEP = 12


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def get_dct_matrix(N: int = 8, device: torch.device = None) -> torch.Tensor:
    C = np.zeros((N, N), dtype=np.float32)
    for k in range(N):
        for n in range(N):
            C[k, n] = (
                1.0 / np.sqrt(N) if k == 0
                else np.sqrt(2.0 / N) * np.cos(np.pi * k * (2.0 * n + 1.0) / (2.0 * N))
            )
    return torch.tensor(C, device=device)


def build_feature_extractor(device: torch.device):
    """Load ResNet50 and strip the last 3 children to get a feature map."""
    print("Loading ResNet50 feature extractor...")
    resnet = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2).to(device)
    resnet.eval()
    extractor = torch.nn.Sequential(*list(resnet.children())[:-3]).to(device)
    preprocess = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return extractor, preprocess


def get_attention_blocks(chunk, chunk_h, chunk_w, mid_w,
                          feature_extractor, preprocess, device):
    """
    Run the AI on the pristine left half of a chunk and return a sorted list
    of (row, col) block positions in the right half, ordered by attention score.
    """
    control_crop = chunk[:, :mid_w]
    control_uint8 = (control_crop * 255.0).astype(np.uint8)
    inp = preprocess(Image.fromarray(control_uint8)).unsqueeze(0).to(device)

    with torch.no_grad():
        fmap = feature_extractor(inp).squeeze(0).cpu().numpy()

    heat = np.mean(fmap, axis=0)
    heat_resized = cv2.resize(heat, (control_crop.shape[1], control_crop.shape[0]))

    blocks = []
    for i in range(0, chunk_h, BLOCK_SIZE):
        for j in range(0, mid_w, BLOCK_SIZE):
            target_j = mid_w + j          # mirror location in right half
            if i + BLOCK_SIZE <= chunk_h and target_j + BLOCK_SIZE <= chunk_w:
                score = float(np.mean(heat_resized[i:i + BLOCK_SIZE, j:j + BLOCK_SIZE]))
                blocks.append(((i, target_j), score))

    blocks.sort(key=lambda b: (b[1], -b[0][0], -b[0][1]), reverse=True)
    return blocks


def format_size(size_in_bytes: int) -> str:
    mb = size_in_bytes / (1024 * 1024)
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.2f} MB"


# ---------------------------------------------------------------------------
# Bit I/O classes
# ---------------------------------------------------------------------------

class BitStreamer:
    """Read a binary file and stream bits (with 8-byte length header)."""

    def __init__(self, filepath: str):
        self.file = open(filepath, "rb")
        payload_len = os.path.getsize(filepath)
        header_bytes = struct.pack(">Q", payload_len)
        self.buffer = np.unpackbits(np.frombuffer(header_bytes, dtype=np.uint8)).tolist()
        self.total_bits = (8 + payload_len) * 8
        self.bits_read = 0

    def get_bits(self, count: int) -> list:
        while len(self.buffer) < count:
            chunk = self.file.read(1024 * 1024)
            if not chunk:
                break
            self.buffer.extend(np.unpackbits(np.frombuffer(chunk, dtype=np.uint8)).tolist())
        extracted = self.buffer[:count]
        self.buffer = self.buffer[count:]
        self.bits_read += len(extracted)
        return extracted

    def is_empty(self) -> bool:
        return self.bits_read >= self.total_bits

    def close(self):
        self.file.close()


class BitWriter:
    """Collect extracted bits and write the reconstructed payload to a file."""

    def __init__(self, filepath: str):
        self.file = open(filepath, "wb")
        self.buffer = []
        self.payload_len = None
        self.bytes_written = 0
        self.header_bits = 64

    def push_bits(self, bits: list):
        self.buffer.extend(bits)

        # Decode header on first 64 bits
        if self.payload_len is None and len(self.buffer) >= self.header_bits:
            header_bits = self.buffer[:self.header_bits]
            self.buffer = self.buffer[self.header_bits:]
            self.payload_len = struct.unpack(">Q", np.packbits(header_bits).tobytes())[0]
            print(f"  Header decoded: expecting {self.payload_len:,} bytes of payload.")

        if self.payload_len is not None:
            needed_bytes = self.payload_len - self.bytes_written
            bytes_to_write = min(needed_bytes, len(self.buffer) // 8)
            if bytes_to_write > 0:
                bits_to_pack = self.buffer[:bytes_to_write * 8]
                self.buffer = self.buffer[bytes_to_write * 8:]
                self.file.write(np.packbits(bits_to_pack).tobytes())
                self.bytes_written += bytes_to_write

    def is_done(self) -> bool:
        return self.payload_len is not None and self.bytes_written >= self.payload_len

    def close(self):
        self.file.close()


# ---------------------------------------------------------------------------
# ENCODE
# ---------------------------------------------------------------------------

def encode(enc_file: str, cover_file: str, output_dir: str):
    """
    Embed the encrypted binary into the cover TIFF using DCT steganography.
    Outputs one or more stego TIF parts into output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    stego_out_pattern = os.path.join(output_dir, "dct_stego_part_{}.tif")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    C_mat = get_dct_matrix(8, device)
    C_mat_T = C_mat.t()
    feature_extractor, preprocess = build_feature_extractor(device)

    streamer = BitStreamer(enc_file)
    cover_np = tifffile.imread(cover_file)
    if cover_np.ndim == 2:
        cover_np = np.stack([cover_np] * 3, axis=-1)
    elif cover_np.ndim == 3 and cover_np.shape[-1] == 1:
        cover_np = np.concatenate([cover_np] * 3, axis=-1)
    elif cover_np.ndim == 3 and cover_np.shape[-1] == 4:
        cover_np = cover_np[:, :, :3]
    
    H, W, _ = cover_np.shape
    print(f"Cover image: {W}x{H} px  |  Payload: {format_size(os.path.getsize(enc_file))}")

    pos_r = [p[0] for p in COEFF_POSITIONS]
    pos_c = [p[1] for p in COEFF_POSITIONS]

    part = 1
    while not streamer.is_empty():
        out_name = stego_out_pattern.format(part)
        print(f"\n--- Creating {out_name} ---")
        out_mmap = tifffile.memmap(out_name, shape=(H, W, 3),
                                   dtype=np.float32, photometric="rgb")

        for y in range(0, H, CHUNK_SIZE):
            for x in range(0, W, CHUNK_SIZE):
                chunk_h = min(CHUNK_SIZE, H - y)
                chunk_w = min(CHUNK_SIZE, W - x)
                chunk = cover_np[y:y + chunk_h, x:x + chunk_w].copy()

                if streamer.is_empty():
                    out_mmap[y:y + chunk_h, x:x + chunk_w] = chunk
                    continue

                mid_w = (chunk_w // 2 // BLOCK_SIZE) * BLOCK_SIZE
                if mid_w == 0:
                    continue

                blocks = get_attention_blocks(chunk, chunk_h, chunk_w, mid_w,
                                              feature_extractor, preprocess, device)

                stego_chunk = chunk.copy()
                B = len(blocks)
                needed_bits = B * BITS_PER_BLOCK
                bits = streamer.get_bits(needed_bits)
                actual_bits = len(bits)

                if actual_bits > 0:
                    if actual_bits < needed_bits:
                        bits = bits + [0] * (needed_bits - actual_bits)

                    bits_t = torch.tensor(bits, dtype=torch.int32,
                                          device=device).view(B, 3, -1)
                    r_coords = np.array([blk[0][0] for blk in blocks])
                    c_coords = np.array([blk[0][1] for blk in blocks])

                    X_np = np.zeros((B, 3, 8, 8), dtype=np.float32)
                    for i in range(B):
                        X_np[i] = (stego_chunk[r_coords[i]:r_coords[i] + 8,
                                               c_coords[i]:c_coords[i] + 8]
                                   .transpose(2, 0, 1) * 255.0)

                    X_t = torch.tensor(X_np, device=device)
                    Y_t = C_mat @ X_t @ C_mat_T

                    coeffs = Y_t[:, :, pos_r, pos_c]
                    q_val  = torch.round(coeffs / QUANTIZATION_STEP).to(torch.int32)
                    Y_t[:, :, pos_r, pos_c] = (
                        ((q_val & ~1) | bits_t) * QUANTIZATION_STEP
                    ).to(torch.float32)

                    X_new_np = (C_mat_T @ Y_t @ C_mat).cpu().numpy().transpose(0, 2, 3, 1)
                    for i in range(B):
                        stego_chunk[r_coords[i]:r_coords[i] + 8,
                                    c_coords[i]:c_coords[i] + 8] = X_new_np[i] / 255.0

                    del X_np, X_t, Y_t, X_new_np

                out_mmap[y:y + chunk_h, x:x + chunk_w] = stego_chunk
                out_mmap.flush()

                del chunk, stego_chunk, bits
                gc.collect()
                torch.cuda.empty_cache()

        print(f"Part {part} done. Bits embedded so far: {streamer.bits_read:,}")
        part += 1

    streamer.close()
    del cover_np
    gc.collect()
    print("\n✅ ENCODE COMPLETE")


# ---------------------------------------------------------------------------
# DECODE
# ---------------------------------------------------------------------------

def decode(stego_dir: str, output_bin: str):
    """
    Extract the hidden payload from all stego TIF parts in stego_dir
    and write the reassembled binary to output_bin.
    """
    stego_files = sorted(
        glob.glob(os.path.join(stego_dir, "dct_stego_part_*.tif")),
        key=lambda x: int(re.search(r"part_(\d+)", x).group(1)),
    )
    if not stego_files:
        raise FileNotFoundError(f"No stego parts found in: {stego_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}  |  Found {len(stego_files)} stego part(s)")

    C_mat = get_dct_matrix(8, device)
    C_mat_T = C_mat.t()
    feature_extractor, preprocess = build_feature_extractor(device)

    pos_r = [p[0] for p in COEFF_POSITIONS]
    pos_c = [p[1] for p in COEFF_POSITIONS]

    writer = BitWriter(output_bin)

    for stego_file in stego_files:
        if writer.is_done():
            break

        print(f"\nExtracting from {os.path.basename(stego_file)}...")
        stego_mmap = tifffile.memmap(stego_file)
        H, W, _ = stego_mmap.shape

        for y in range(0, H, CHUNK_SIZE):
            if writer.is_done():
                break
            for x in range(0, W, CHUNK_SIZE):
                if writer.is_done():
                    break

                chunk_h = min(CHUNK_SIZE, H - y)
                chunk_w = min(CHUNK_SIZE, W - x)
                chunk_float = stego_mmap[y:y + chunk_h, x:x + chunk_w].copy()

                mid_w = (chunk_w // 2 // BLOCK_SIZE) * BLOCK_SIZE
                if mid_w == 0:
                    continue

                blocks = get_attention_blocks(chunk_float, chunk_h, chunk_w, mid_w,
                                              feature_extractor, preprocess, device)

                B = len(blocks)
                r_coords = np.array([blk[0][0] for blk in blocks])
                c_coords = np.array([blk[0][1] for blk in blocks])

                X_np = np.zeros((B, 3, 8, 8), dtype=np.float32)
                for i in range(B):
                    X_np[i] = (chunk_float[r_coords[i]:r_coords[i] + 8,
                                            c_coords[i]:c_coords[i] + 8]
                               .transpose(2, 0, 1) * 255.0)

                X_t = torch.tensor(X_np, device=device)
                Y_t = C_mat @ X_t @ C_mat_T

                coeffs = Y_t[:, :, pos_r, pos_c]
                q_val  = torch.round(coeffs / QUANTIZATION_STEP).to(torch.int32)
                extracted_bits = (q_val & 1).view(-1).cpu().numpy().tolist()
                writer.push_bits(extracted_bits)

                del chunk_float, X_np, X_t, Y_t, coeffs, q_val
                gc.collect()
                torch.cuda.empty_cache()

    writer.close()
    print(f"\n✅ DECODE COMPLETE — saved to: {output_bin}")


# ---------------------------------------------------------------------------
# VERIFY
# ---------------------------------------------------------------------------

def verify(original_bin: str, extracted_bin: str):
    """SHA-256 integrity check between the original and extracted binary."""

    def sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                h.update(block)
        return h.hexdigest()

    print("🔐 CRYPTOGRAPHIC INTEGRITY CHECK")
    print("-" * 65)
    h_orig = sha256(original_bin)
    h_extr = sha256(extracted_bin)
    print(f"Original Hash:  {h_orig}")
    print(f"Extracted Hash: {h_extr}")
    print("-" * 65)

    if h_orig == h_extr:
        print("✅ PERFECT MATCH — payload recovered with 0% error.")
    else:
        print("❌ MISMATCH — bit corruption detected.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------

def metrics(cover_file: str, stego_file: str, crop_size: int = 1000):
    """
    Compute MSE, PSNR, and SSIM on a 2000×2000 centre crop of
    the cover vs. the first stego part.
    """
    if ssim is None:
        raise SystemExit("ERROR: Run 'pip install scikit-image' first.")

    print("Memory-mapping images...")
    cover_mmap = tifffile.memmap(cover_file)
    stego_mmap = tifffile.memmap(stego_file)

    H, W = cover_mmap.shape[:2]
    cy, cx = H // 2, W // 2
    print(f"Extracting {crop_size * 2}×{crop_size * 2} centre crop...")
    cover_crop = cover_mmap[cy - crop_size:cy + crop_size,
                            cx - crop_size:cx + crop_size].copy()
    
    if cover_crop.ndim == 2:
        cover_crop = np.stack([cover_crop] * 3, axis=-1)
    elif cover_crop.ndim == 3 and cover_crop.shape[-1] == 1:
        cover_crop = np.concatenate([cover_crop] * 3, axis=-1)
    elif cover_crop.ndim == 3 and cover_crop.shape[-1] == 4:
        cover_crop = cover_crop[:, :, :3]

    stego_crop = stego_mmap[cy - crop_size:cy + crop_size,
                            cx - crop_size:cx + crop_size].copy()

    mse  = np.mean((cover_crop - stego_crop) ** 2)
    psnr = float("inf") if mse == 0 else 20 * math.log10(1.0 / math.sqrt(mse))
    ssim_val = ssim(cover_crop, stego_crop, data_range=1.0, channel_axis=-1)

    print("\n" + "=" * 40)
    print("METRICS REPORT (centre crop)")
    print("=" * 40)
    print(f"MSE  : {mse:.8f}")
    print(f"PSNR : {psnr:.2f} dB")
    print(f"SSIM : {ssim_val:.4f}")
    print("=" * 40)

    del cover_mmap, stego_mmap, cover_crop, stego_crop


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DCT steganography — encode, decode, verify, or measure quality."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # encode
    p_enc = sub.add_parser("encode", help="Embed a binary payload into a cover TIFF")
    p_enc.add_argument("enc_bin",    help="Path to the encrypted payload (.bin)")
    p_enc.add_argument("cover_tif",  help="Path to the cover image (.tif, float32)")
    p_enc.add_argument("output_dir", help="Directory where stego TIF parts are saved")

    # decode
    p_dec = sub.add_parser("decode", help="Extract the hidden payload from stego TIFs")
    p_dec.add_argument("stego_dir",  help="Directory containing dct_stego_part_*.tif files")
    p_dec.add_argument("output_bin", help="Path for the reconstructed binary output")

    # verify
    p_ver = sub.add_parser("verify", help="SHA-256 integrity check")
    p_ver.add_argument("original_bin",  help="Original encrypted binary")
    p_ver.add_argument("extracted_bin", help="Extracted binary from decoder")

    # metrics
    p_met = sub.add_parser("metrics", help="Compute MSE / PSNR / SSIM")
    p_met.add_argument("cover_tif", help="Original cover TIFF")
    p_met.add_argument("stego_tif", help="Stego TIFF (first part)")

    args = parser.parse_args()

    if args.command == "encode":
        encode(args.enc_bin, args.cover_tif, args.output_dir)
    elif args.command == "decode":
        decode(args.stego_dir, args.output_bin)
    elif args.command == "verify":
        verify(args.original_bin, args.extracted_bin)
    elif args.command == "metrics":
        metrics(args.cover_tif, args.stego_tif)


if __name__ == "__main__":
    main()