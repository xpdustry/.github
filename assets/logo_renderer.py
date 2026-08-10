#!/usr/bin/env python3
"""
Programatically renders the xpdustry logo.
The original logo was done manually in inkscape, but it's annoying to make tweaks.
So I made this sloppy script. Had to steer codex a lot but I got a satisfactory result at the end.

PS: The produced logo is NOT optimized. You will need to flatten it manually in inkscape
and/or use an online tool such as https://svgomg.net/.

Current official parameters are:

- for the fully colored one
> ./logo_renderer.py \
  --svg logo.svg \
  --png logo.png

- for the flat colored one
> ./logo_renderer.py \
  --svg logo-flat.svg \
  --png logo-flat.png \
  --depth 0 \
  --outline-width 0

- for the monochrome one
> ./logo_renderer.py \
  --svg logo-monochrome.svg \
  --png logo-monochrome.png \
  --depth 0 \
  --outline-width 0 \
  --color '#000000' \
  --x-color '#000000'
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from dataclasses import dataclass, fields
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.sax.saxutils import escape


CENTRE = 0.5
DEPTH_STEP = 0.001
GEOMETRY_FIELDS = {
    "outline_width",
    "depth",
    "cog_radius",
    "hole_radius",
    "axis_tooth_height",
    "axis_tooth_width",
    "axis_tooth_taper",
    "axis_tip_radius",
    "diagonal_tooth_height",
    "diagonal_tooth_width",
    "diagonal_tip_radius",
    "x_height",
    "x_width",
    "x_gap",
    "x_tip_radius",
}


def number(value: float) -> str:
    """Return compact, stable SVG coordinates."""
    if abs(value) < 0.0000005:
        value = 0.0
    return f"{value:.6f}".rstrip("0").rstrip(".")


def hundredth(value: float) -> float:
    """Keep the public geometry controls on the logo's 0.01 design grid."""
    if not math.isfinite(value):
        raise ValueError("geometry values must be finite")
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def xml_colour(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def tangent_point(
    corner: tuple[float, float],
    neighbour: tuple[float, float],
    distance: float,
) -> tuple[float, float]:
    dx, dy = neighbour[0] - corner[0], neighbour[1] - corner[1]
    length = math.hypot(dx, dy)
    return corner[0] + dx * distance / length, corner[1] + dy * distance / length


def corner_tangents(
    previous: tuple[float, float],
    corner: tuple[float, float],
    following: tuple[float, float],
    radius: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    incoming = (previous[0] - corner[0], previous[1] - corner[1])
    outgoing = (following[0] - corner[0], following[1] - corner[1])
    incoming_length = math.hypot(*incoming)
    outgoing_length = math.hypot(*outgoing)
    cosine = (incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) / (
        incoming_length * outgoing_length
    )
    angle = math.acos(max(-1.0, min(1.0, cosine)))
    trim = radius / math.tan(angle / 2)
    return tangent_point(corner, previous, trim), tangent_point(corner, following, trim)


def rounded_axis_tooth(options: "RenderOptions") -> str:
    """Draw one right-facing tapered tooth; SVG rotations create the other three."""
    root_half = options.axis_tooth_width / 2
    tip_half = (options.axis_tooth_width - options.axis_tooth_taper) / 2
    root_x = CENTRE + math.sqrt(options.cog_radius**2 - root_half**2)
    tip_x = CENTRE + options.axis_tooth_height
    corners = (
        (root_x, CENTRE - root_half),
        (tip_x, CENTRE - tip_half),
        (tip_x, CENTRE + tip_half),
        (root_x, CENTRE + root_half),
    )

    if options.axis_tip_radius == 0:
        return "M " + " L ".join(f"{number(x)} {number(y)}" for x, y in corners) + " Z"

    # Tangent points let SVG's A command round the slanted tip with a true,
    # constant-radius arc instead of approximating it with sampled points.
    top_in, top_out = corner_tangents(*corners[:3], options.axis_tip_radius)
    bottom_in, bottom_out = corner_tangents(*corners[1:], options.axis_tip_radius)

    return " ".join(
        (
            f"M {number(corners[0][0])} {number(corners[0][1])}",
            f"L {number(top_in[0])} {number(top_in[1])}",
            f"A {number(options.axis_tip_radius)} {number(options.axis_tip_radius)} "
            f"0 0 1 {number(top_out[0])} {number(top_out[1])}",
            f"L {number(bottom_in[0])} {number(bottom_in[1])}",
            f"A {number(options.axis_tip_radius)} {number(options.axis_tip_radius)} "
            f"0 0 1 {number(bottom_out[0])} {number(bottom_out[1])}",
            f"L {number(corners[3][0])} {number(corners[3][1])} Z",
        )
    )


@dataclass(frozen=True)
class RenderOptions:
    size: int = 2048
    cog_colour: str = "#00fff1"
    x_colour: str = "#ffffff"
    cog_depth_colour: str = "#007f79"
    x_depth_colour: str = "#808080"
    outline_colour: str = "#30363b"
    outline_width: float = 0.02
    depth: float = 0.03
    cog_radius: float = 0.30
    hole_radius: float = 0.24
    axis_tooth_height: float = 0.36
    axis_tooth_width: float = 0.12
    axis_tooth_taper: float = 0.02
    axis_tip_radius: float = 0.01
    axis_crop: bool = True
    diagonal_tooth_height: float = 0.33
    diagonal_tooth_width: float = 0.30
    diagonal_tip_radius: float = 0.05
    diagonal_crop: bool = True
    x_height: float = 0.42
    x_width: float = 0.12
    x_gap: float = 0.04
    x_tip_radius: float = 0.02
    x_crop: bool = True

    def __post_init__(self) -> None:
        for field in fields(self):
            if field.name in GEOMETRY_FIELDS:
                object.__setattr__(self, field.name, hundredth(getattr(self, field.name)))


def bar(bar_id: str, height: float, width: float, radius: float) -> str:
    return (
        f'    <rect id="{bar_id}" x="{number(CENTRE - height)}" '
        f'y="{number(CENTRE - width / 2)}" width="{number(2 * height)}" '
        f'height="{number(width)}" rx="{number(radius)}"/>'
    )


def circle_clip(clip_id: str, radius: float) -> str:
    return (
        f'    <clipPath id="{clip_id}">'
        f'<circle cx="{CENTRE}" cy="{CENTRE}" r="{number(radius)}"/>'
        "</clipPath>"
    )


def clip(enabled: bool, clip_id: str) -> str:
    return f' clip-path="url(#{clip_id})"' if enabled else ""


def depth_sweep(shape_id: str, colour: str, depth: float) -> str:
    """Stack the exact vector silhouette densely enough to read as an extrusion."""
    steps = max(1, math.ceil(depth / DEPTH_STEP))
    copies = "\n".join(
        f'        <use href="#{shape_id}" '
        f'transform="translate(0 {number(depth * step / steps)})"/>'
        for step in range(steps, -1, -1)
    )
    # SVG has no directional vector-dilation primitive. Reusing the masked
    # silhouette avoids detached shadows and raster filter artefacts.
    return f'''      <g fill="{xml_colour(colour)}">
{copies}
      </g>'''


def outline_filter(options: RenderOptions) -> str:
    # A blurred alpha edge threshold gives a genuinely round expansion; plain
    # feMorphology uses a rectangular kernel and leaves boxy outside corners.
    padding = options.outline_width
    # A discrete table splits alpha into one bucket per entry. With 40 entries,
    # only alpha below 1/40 (0.025) stays transparent; the other 39 buckets are
    # fully opaque. A short "0 1" table would cut at 0.5 and lose the outline.
    hard_threshold = "0 " + " ".join(["1"] * 39)
    return f'''    <filter id="outline-filter" x="{number(-padding)}" y="{number(-padding)}"
            width="{number(1 + 2 * padding)}" height="{number(1 + 2 * padding)}"
            filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse"
            color-interpolation-filters="sRGB">
      <feGaussianBlur in="SourceAlpha"
                      stdDeviation="{number(options.outline_width / 2)}" result="soft-edge"/>
      <feComponentTransfer in="soft-edge" result="expanded-alpha">
        <feFuncA type="discrete" tableValues="{hard_threshold}"/>
      </feComponentTransfer>
      <feFlood flood-color="{xml_colour(options.outline_colour)}" result="colour"/>
      <feComposite in="colour" in2="expanded-alpha" operator="in"/>
    </filter>'''


def svg_document(options: RenderOptions) -> str:
    """Build a standalone SVG document."""
    validate(options)
    axis_clip = clip(options.axis_crop, "axis-limit")
    diagonal_clip = clip(options.diagonal_crop, "diagonal-limit")
    x_clip = clip(options.x_crop, "x-limit")
    gap_clip = clip(options.x_crop, "gap-limit")

    definitions = [
        bar(
            "diagonal-bar",
            options.diagonal_tooth_height,
            options.diagonal_tooth_width,
            options.diagonal_tip_radius,
        ),
        bar("x-bar", options.x_height, options.x_width, options.x_tip_radius),
        bar(
            "gap-bar",
            options.x_height + options.x_gap,
            options.x_width + 2 * options.x_gap,
            options.x_tip_radius + options.x_gap if options.x_tip_radius else 0,
        ),
    ]
    if options.axis_crop:
        definitions.append(circle_clip("axis-limit", options.axis_tooth_height))
    if options.diagonal_crop:
        definitions.append(circle_clip("diagonal-limit", options.diagonal_tooth_height))
    if options.x_crop:
        definitions.extend(
            (
                circle_clip("x-limit", options.x_height),
                circle_clip("gap-limit", options.x_height + options.x_gap),
            )
        )

    depth_layers = ""
    if options.depth:
        depth_layers = "\n" + "\n".join(
            (
                depth_sweep("cog-shape", options.cog_depth_colour, options.depth),
                depth_sweep("x-shape", options.x_depth_colour, options.depth),
            )
        )

    outline_def = outline_filter(options) if options.outline_width else ""
    outline_layer = (
        '  <use href="#complete-logo" filter="url(#outline-filter)"/>\n'
        if options.outline_width
        else ""
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{options.size}" height="{options.size}" viewBox="0 0 1 1">
  <title>Xpdustry cog</title>
  <defs>
{chr(10).join(definitions)}
    <path id="axis-tooth" d="{rounded_axis_tooth(options)}"/>
    <g id="axis-teeth"{axis_clip}>
      <use href="#axis-tooth"/>
      <use href="#axis-tooth" transform="rotate(90 .5 .5)"/>
      <use href="#axis-tooth" transform="rotate(180 .5 .5)"/>
      <use href="#axis-tooth" transform="rotate(270 .5 .5)"/>
    </g>
    <g id="diagonal-teeth"{diagonal_clip}>
      <use href="#diagonal-bar" transform="rotate(45 .5 .5)"/>
      <use href="#diagonal-bar" transform="rotate(-45 .5 .5)"/>
    </g>
    <g id="x-shape"{x_clip}>
      <use href="#x-bar" transform="rotate(45 .5 .5)"/>
      <use href="#x-bar" transform="rotate(-45 .5 .5)"/>
    </g>
    <g id="gap-shape"{gap_clip}>
      <use href="#gap-bar" transform="rotate(45 .5 .5)"/>
      <use href="#gap-bar" transform="rotate(-45 .5 .5)"/>
    </g>
    <mask id="cog-cutouts" x="0" y="0" width="1" height="1"
          maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" mask-type="luminance">
      <rect width="1" height="1" fill="white"/>
      <circle cx=".5" cy=".5" r="{number(options.hole_radius)}" fill="black"/>
      <use href="#gap-shape" fill="black"/>
    </mask>
    <g id="cog-shape" mask="url(#cog-cutouts)">
      <circle cx=".5" cy=".5" r="{number(options.cog_radius)}"/>
      <use href="#axis-teeth"/>
      <use href="#diagonal-teeth"/>
    </g>
{outline_def}
    <g id="complete-logo">{depth_layers}
      <use href="#cog-shape" fill="{xml_colour(options.cog_colour)}"/>
      <use href="#x-shape" fill="{xml_colour(options.x_colour)}"/>
    </g>
  </defs>
{outline_layer}  <use href="#complete-logo"/>
</svg>
'''


def visible_radius(height: float, width: float, cropped: bool) -> float:
    return height if cropped else math.hypot(height, width / 2)


def tapered_radius_limit(options: RenderOptions) -> float:
    root_half = options.axis_tooth_width / 2
    tip_half = (options.axis_tooth_width - options.axis_tooth_taper) / 2
    root_x = math.sqrt(options.cog_radius**2 - root_half**2)
    side = (root_x - options.axis_tooth_height, tip_half - root_half)
    side_length = math.hypot(*side)
    corner_angle = math.acos(side[1] / side_length)
    return min(side_length, tip_half) * math.tan(corner_angle / 2)


def validate(options: RenderOptions) -> None:
    if options.size <= 0:
        raise ValueError("size must be positive")

    positive = {
        "cog radius": options.cog_radius,
        "hole radius": options.hole_radius,
        "axis tooth height": options.axis_tooth_height,
        "axis tooth width": options.axis_tooth_width,
        "diagonal tooth height": options.diagonal_tooth_height,
        "diagonal tooth width": options.diagonal_tooth_width,
        "X height": options.x_height,
        "X width": options.x_width,
    }
    bad = [name for name, value in positive.items() if value <= 0]
    if bad:
        raise ValueError(f"{', '.join(bad)} must be positive")
    if options.hole_radius >= options.cog_radius:
        raise ValueError("hole radius must be smaller than cog radius")
    if min(options.axis_tooth_height, options.diagonal_tooth_height) <= options.cog_radius:
        raise ValueError("tooth heights must be greater than cog radius")
    if options.axis_tooth_width / 2 >= options.cog_radius:
        raise ValueError("axis tooth half-width must be smaller than cog radius")
    if not 0 <= options.axis_tooth_taper < options.axis_tooth_width:
        raise ValueError("axis tooth taper must be non-negative and smaller than its width")

    non_negative = {
        "depth": options.depth,
        "outline width": options.outline_width,
        "X gap": options.x_gap,
        "axis tip radius": options.axis_tip_radius,
        "diagonal tip radius": options.diagonal_tip_radius,
        "X tip radius": options.x_tip_radius,
    }
    bad = [name for name, value in non_negative.items() if value < 0]
    if bad:
        raise ValueError(f"{', '.join(bad)} must be zero or positive")

    radii = {
        "axis tip radius": (options.axis_tip_radius, tapered_radius_limit(options)),
        "diagonal tip radius": (
            options.diagonal_tip_radius,
            min(options.diagonal_tooth_height, options.diagonal_tooth_width / 2),
        ),
        "X tip radius": (options.x_tip_radius, min(options.x_height, options.x_width / 2)),
    }
    bad = [name for name, (value, limit) in radii.items() if value > limit + 1e-9]
    if bad:
        details = ", ".join(
            f"{name} ({value:g}, maximum {limit:g})"
            for name, (value, limit) in radii.items()
            if name in bad
        )
        raise ValueError(f"tip radius is too large: {details}")

    extents = (
        options.cog_radius,
        visible_radius(
            options.axis_tooth_height,
            options.axis_tooth_width - options.axis_tooth_taper,
            options.axis_crop,
        ),
        visible_radius(
            options.diagonal_tooth_height,
            options.diagonal_tooth_width,
            options.diagonal_crop,
        ),
        visible_radius(options.x_height, options.x_width, options.x_crop),
    )
    furthest = max(extents) + options.depth + options.outline_width
    if furthest > 0.5:
        raise ValueError(f"depth and outline extend beyond the canvas ({number(furthest)})")


def parser() -> argparse.ArgumentParser:
    defaults = RenderOptions()
    result = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    result.add_argument("--svg", type=Path, default=Path("cog-v9.svg"))
    result.add_argument("--png", type=Path, help="also export a transparent PNG with Inkscape")
    result.add_argument("--size", type=int, default=defaults.size, help="SVG and PNG dimensions in pixels")
    result.add_argument("--color", dest="cog_colour", default=defaults.cog_colour, help="cog face colour")
    result.add_argument("--x-color", dest="x_colour", default=defaults.x_colour, help="X face colour")
    result.add_argument("--cog-depth-color", dest="cog_depth_colour", default=defaults.cog_depth_colour)
    result.add_argument("--x-depth-color", dest="x_depth_colour", default=defaults.x_depth_colour)
    result.add_argument("--outline-color", dest="outline_colour", default=defaults.outline_colour)
    result.add_argument("--outline-width", type=float, default=defaults.outline_width)
    result.add_argument("--depth", type=float, default=defaults.depth)
    result.add_argument("--cog-radius", type=float, default=defaults.cog_radius)
    result.add_argument("--hole-radius", type=float, default=defaults.hole_radius)
    result.add_argument("--axis-tooth-height", type=float, default=defaults.axis_tooth_height)
    result.add_argument("--axis-tooth-width", type=float, default=defaults.axis_tooth_width)
    result.add_argument("--axis-tooth-taper", type=float, default=defaults.axis_tooth_taper)
    result.add_argument("--axis-tip-radius", type=float, default=defaults.axis_tip_radius)
    result.add_argument("--axis-crop", action=argparse.BooleanOptionalAction, default=defaults.axis_crop)
    result.add_argument("--diagonal-tooth-height", type=float, default=defaults.diagonal_tooth_height)
    result.add_argument("--diagonal-tooth-width", type=float, default=defaults.diagonal_tooth_width)
    result.add_argument("--diagonal-tip-radius", type=float, default=defaults.diagonal_tip_radius)
    result.add_argument("--diagonal-crop", action=argparse.BooleanOptionalAction, default=defaults.diagonal_crop)
    result.add_argument("--x-height", type=float, default=defaults.x_height)
    result.add_argument("--x-width", type=float, default=defaults.x_width)
    result.add_argument("--x-gap", type=float, default=defaults.x_gap)
    result.add_argument("--x-tip-radius", type=float, default=defaults.x_tip_radius)
    result.add_argument("--x-crop", action=argparse.BooleanOptionalAction, default=defaults.x_crop)
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        options = RenderOptions(
            **{field.name: getattr(args, field.name) for field in fields(RenderOptions)}
        )
        svg = svg_document(options)
    except ValueError as error:
        raise SystemExit(error) from error

    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(svg, encoding="utf-8")
    print(f"wrote {args.svg}")

    if args.png:
        inkscape = shutil.which("inkscape")
        if not inkscape:
            raise SystemExit("PNG export requested, but Inkscape is not on PATH")
        args.png.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            (
                inkscape,
                str(args.svg.resolve()),
                f"--export-filename={args.png.resolve()}",
                f"--export-width={options.size}",
                f"--export-height={options.size}",
                "--export-background-opacity=0",
            ),
            check=True,
        )
        print(f"wrote {args.png}")


if __name__ == "__main__":
    main()
