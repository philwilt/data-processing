#!/usr/bin/env python3
"""
Batch convert RAW images (CR2, DNG) → JPEG/PNG/WebP with progress bar.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Mapping

import rawpy
from PIL import Image
import typer
from tqdm import tqdm


app = typer.Typer(help="Batch convert RAW (CR2, DNG) files recursively.")
RAW_EXT: frozenset[str] = {".cr2", ".dng"}


def _build_save_kwargs(fmt: str, quality: int) -> Mapping[str, object]:
    """Return Pillow ``save`` kwargs based on format."""
    return {"quality": quality, "optimize": True} if fmt == "jpeg" else {}


def process_raw(
    input_path: Path,
    output_path: Path,
    *,
    resize: int | None = None,
    quality: int = 92,
    fmt: str = "jpeg",
) -> None:
    """Convert a single RAW file to the requested format."""
    with rawpy.imread(str(input_path)) as raw:
        rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=8)

    img = Image.fromarray(rgb)
    if resize and resize > 0:
        img.thumbnail((resize, resize), Image.Resampling.LANCZOS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format=fmt.upper(), **_build_save_kwargs(fmt.lower(), quality))


# --------------------------------------------------------------------------- #
#  Default command (callback) – this will be called when no sub‑command is
#  supplied. It simply forwards to the original `convert` logic.
# --------------------------------------------------------------------------- #
@app.callback(invoke_without_command=True)
def main(
    input_dir: Path = typer.Argument(..., help="Input directory containing RAW files"),
    output_dir: Path = typer.Argument(..., help="Output directory for converted images"),
    fmt: str = typer.Option("jpeg", "--format", "-f", help="Output format: jpeg, png, webp"),
    resize: int | None = typer.Option(384, "--resize", "-r", help="Max dimension (longest side). 0 = no resize"),
    quality: int = typer.Option(92, "--quality", "-q", help="JPEG/WebP quality (1–100)"),
):
    """
    Batch convert RAW images from INPUT_DIR to OUTPUT_DIR.
    If you want the old sub‑command syntax, keep `convert` below.
    """
    # The real work is done in this helper function
    _do_convert(input_dir, output_dir, fmt=fmt, resize=resize, quality=quality)


# --------------------------------------------------------------------------- #
#  Actual conversion logic (kept separate so it can be called from the
#  callback *and* as a real sub‑command if you want to keep that style).
# --------------------------------------------------------------------------- #
def _do_convert(
    input_dir: Path,
    output_dir: Path,
    *,
    fmt: str,
    resize: int | None,
    quality: int,
) -> None:
    raw_files = [p for p in input_dir.rglob("*") if p.suffix.lower() in RAW_EXT]
    if not raw_files:
        typer.echo("❌ No RAW files found.")
        raise typer.Exit(1)

    total, skips, start_ts = len(raw_files), 0, time.time()

    with tqdm(total=total, desc="Processing", unit="file") as pbar:
        for raw_file in raw_files:
            rel_path: Path = raw_file.relative_to(input_dir)
            output_path = output_dir / rel_path.with_suffix(f".{fmt.lower()}")

            if output_path.exists():
                skips += 1
                typer.echo(
                    f"⚠️  Skipping {raw_file} → {output_path} (already exists)\n",
                    nl=False,
                )
                pbar.update(1)
                continue

            # Show what we’re doing
            typer.echo(f"➡️  Converting {raw_file} → {output_path}\n", nl=False)

            process_raw(
                raw_file, output_path, resize=resize, quality=quality, fmt=fmt
            )
            pbar.update(1)

    elapsed = time.time() - start_ts
    typer.echo(
        f"\n✅ Done! {total} files processed in {elapsed:.2f}s "
        f"({skips} skipped)"
    )


# --------------------------------------------------------------------------- #
#  Keep the old sub‑command if you still want it – otherwise comment out.
# --------------------------------------------------------------------------- #
@app.command(name="convert")
def convert(
    input_dir: Path,
    output_dir: Path,
    *,
    fmt: str = "jpeg",
    resize: int | None = 384,
    quality: int = 92,
):
    """Alias that forwards to the default logic."""
    _do_convert(input_dir, output_dir, fmt=fmt, resize=resize, quality=quality)


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    app()