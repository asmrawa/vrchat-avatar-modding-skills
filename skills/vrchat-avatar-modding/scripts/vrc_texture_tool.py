"""Compare, recolor, composite, or clean UV textures using source-space masks."""

import argparse
from pathlib import Path
import re
import sys

try:
    from PIL import Image, ImageChops, ImageOps
except ImportError:
    raise SystemExit("Pillow is required. Install it in your Python environment before running this tool.")


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(1, f"{self.prog}: {message}\n")


def load(path: Path, mode: str) -> Image.Image:
    with Image.open(path) as image:
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError(f"{path.name}: multi-frame images are unsupported")
        if mode == "L" and image.mode not in {"L", "1"}:
            raise ValueError(f"{path.name}: use a grayscale mask")
        return image.convert(mode)


def mask_for(path: Path, size: tuple[int, int]) -> Image.Image:
    mask = load(path, "L")
    if mask.size != size:
        raise ValueError(f"mask size {mask.size} differs from texture size {size}")
    return mask


def png_color_metadata(path: Path) -> dict:
    with Image.open(path) as image:
        if image.format != "PNG":
            raise ValueError(f"{path.name}: color metadata checks require PNG inputs")
        image.load()
        return {key: image.info[key] for key in ("icc_profile", "srgb", "gamma", "chromaticity")
                if key in image.info}


def compare(reference: Image.Image, candidate: Image.Image, mask: Image.Image | None,
            require_visible_change: bool = False) -> int:
    if reference.size != candidate.size:
        print(f"Size changed: {reference.size} -> {candidate.size}")
        return 2
    difference = ImageChops.difference(reference, candidate)
    red, green, blue, alpha = difference.split()
    changed = ImageChops.lighter(ImageChops.lighter(red, green), ImageChops.lighter(blue, alpha))
    changed_pixels = reference.width * reference.height - changed.histogram()[0]
    alpha_pixels = reference.width * reference.height - alpha.histogram()[0]
    outside = 0
    if mask is not None:
        protected = mask.point(lambda pixel: 255 if pixel == 0 else 0)
        outside = sum(ImageChops.multiply(protected, changed).histogram()[1:])
    print(f"{reference.width}x{reference.height} | changed={changed_pixels} | outside_mask={outside} | alpha_changed={alpha_pixels}")
    if require_visible_change:
        visible = reference.getchannel("A").point(lambda a: 255 if a else 0)
        if mask is not None:
            visible = ImageChops.multiply(visible, mask.point(lambda m: 255 if m else 0))
        rgb_difference = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        if ImageChops.multiply(visible, rgb_difference).getbbox() is None:
            print("No selected nontransparent source pixel changed RGB.")
            return 2
    return 2 if alpha_pixels or outside else 0


def color(value: str) -> str:
    if not re.fullmatch(r"#[\da-fA-F]{6}", value):
        raise argparse.ArgumentTypeError("expected #RRGGBB")
    return value


def background_mask(source, reference_color, tolerance):
    if reference_color is None:
        if tolerance:
            raise ValueError("--tolerance requires --background")
        return source.getchannel("A").point(lambda a: 255 if a == 0 else 0)
    if not 0 <= tolerance <= 255:
        raise ValueError("--tolerance must be between 0 and 255")
    reference = Image.new("RGB", source.size, reference_color)
    r, g, b = ImageChops.difference(source.convert("RGB"), reference).split()
    distance = ImageChops.lighter(ImageChops.lighter(r, g), b)
    return distance.point(lambda d: 255 if d <= tolerance else 0)


def aligned_rgb(path, size):
    candidate = load(path, "RGB")
    if candidate.width * size[1] != size[0] * candidate.height:
        raise ValueError("aspect ratio changed; recover the full atlas before compositing")
    if candidate.size != size:
        candidate = candidate.resize(size, Image.Resampling.LANCZOS)
    return candidate


def main() -> int:
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("compare", help="Check dimensions, alpha, and optional protected pixels.")
    check.add_argument("source", type=Path)
    check.add_argument("candidate", type=Path)
    check.add_argument("--mask", type=Path, help="Grayscale mask. Black pixels must match exactly.")
    check.add_argument("--require-visible-change", action="store_true",
                       help="Require an RGB change where source alpha and selection are nonzero.")
    check.add_argument("--check-color-metadata", action="store_true",
                       help="Require matching PNG ICC, sRGB, gamma, and chromaticity metadata.")
    tint = commands.add_parser("recolor", help="Map source luminance to a tonal ramp inside a grayscale mask.")
    tint.add_argument("source", type=Path)
    tint.add_argument("mask", type=Path, help="Black preserves source, white applies ramp, gray blends.")
    tint.add_argument("output", type=Path)
    tint.add_argument("--shadow", type=color, required=True)
    tint.add_argument("--highlight", type=color, required=True)
    tint.add_argument("--midtone", type=color)
    merge = commands.add_parser("composite", help="Blend an edited atlas into source pixels under a grayscale mask.")
    merge.add_argument("source", type=Path)
    merge.add_argument("candidate", type=Path)
    merge.add_argument("mask", type=Path)
    merge.add_argument("output", type=Path)
    merge.add_argument("--decal", action="store_true",
                       help="Blend a source-sized RGBA overlay using its alpha times the selection.")
    clean = commands.add_parser("clean-bg", help="Restore original background pixels on an edited atlas.")
    clean.add_argument("source", type=Path)
    clean.add_argument("candidate", type=Path)
    clean.add_argument("output", type=Path)
    clean.add_argument("--background", type=color, help="Match source RGB instead of source alpha=0.")
    clean.add_argument("--tolerance", type=int, default=0, help="Maximum difference per RGB channel (0-255).")
    clean.add_argument("--mask", type=Path, help="Limit cleanup to a source-sized background selection.")
    args = parser.parse_args()
    try:
        if args.command in {"composite", "clean-bg"}:
            with args.source.open("rb") as stream:
                header = stream.read(25)
            if not header.startswith(b"\x89PNG\r\n\x1a\n") or header[24:] != b"\x08":
                raise ValueError("use an 8-bit PNG source atlas to preserve channel precision")
        original = load(args.source, "RGBA")
        mask = mask_for(args.mask, original.size) if args.mask else None
        if args.command == "compare":
            candidate = load(args.candidate, "RGBA")
            if args.check_color_metadata:
                source_tags = png_color_metadata(args.source)
                candidate_tags = png_color_metadata(args.candidate)
                changed_tags = sorted(key for key in source_tags.keys() | candidate_tags.keys()
                                      if source_tags.get(key) != candidate_tags.get(key))
                if changed_tags:
                    print(f"PNG color metadata changed: {', '.join(changed_tags)}")
                    return 2
            return compare(original, candidate, mask, args.require_visible_change)
        if args.output.suffix.lower() != ".png":
            raise ValueError("use a new .png output path")
        source_rgb = original.convert("RGB")
        if args.command == "clean-bg":
            selection = background_mask(original, args.background, args.tolerance)
            if mask is not None:
                selection = ImageChops.multiply(selection, mask)
            if selection.getbbox() is None:
                raise ValueError("no matching source background pixels")
            edited = aligned_rgb(args.candidate, original.size)
            result = Image.composite(source_rgb, edited, selection)
            # A compare against the source must lock the restored background.
            mask = ImageOps.invert(selection)
        else:
            if mask.getbbox() is None:
                raise ValueError("the mask selects no pixels")
            if args.command == "composite" and args.decal:
                with Image.open(args.candidate) as layer:
                    if layer.mode != "RGBA" or layer.size != original.size or layer.n_frames != 1:
                        raise ValueError("--decal needs a single source-sized RGBA layer")
                    mask = ImageChops.multiply(mask, layer.getchannel("A"))
                    if mask.getbbox() is None:
                        raise ValueError("decal has no coverage in the selection")
                    edited = layer.convert("RGB")
            elif args.command == "composite":
                edited = aligned_rgb(args.candidate, original.size)
            else:
                edited = ImageOps.colorize(ImageOps.grayscale(original), args.shadow, args.highlight, args.midtone)
            result = Image.composite(edited, source_rgb, mask)
        result.putalpha(original.getchannel("A"))
        with args.output.open("xb") as stream:
            result.save(stream, format="PNG")
        return compare(original, load(args.output, "RGBA"), mask)
    except (OSError, ValueError) as error:
        print(f"Texture check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
