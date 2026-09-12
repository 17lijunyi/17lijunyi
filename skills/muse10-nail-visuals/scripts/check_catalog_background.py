#!/usr/bin/env python3
"""Check a catalog master's canvas and shared background; never modify images."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw, ImageOps

DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/catalog/template.json'


def check(image_path, template_path, tolerance):
    if not 0 <= tolerance <= 255:
        raise ValueError('tolerance must be between 0 and 255')
    template_path = template_path.resolve(strict=True)
    spec = json.loads(template_path.read_text(encoding='utf-8'))
    expected = (spec['canvas']['width'], spec['canvas']['height'])
    background_path = (template_path.parent / spec['background']['path']).resolve(strict=True)
    with Image.open(image_path) as im:
        image = im.convert('RGB')
        alpha = im.convert('RGBA').getchannel('A')
    with Image.open(background_path) as im:
        background = im.convert('RGB')
    if image.size != expected or background.size != expected:
        return {'passed': False, 'reason': 'canvas_size_mismatch',
                'expected': expected, 'image': image.size, 'background': background.size}
    # These regions include nail plates and a narrow allowance for accessories.
    mask = Image.new('L', expected, 255)
    draw = ImageDraw.Draw(mask)
    padding = spec['background_check_padding']
    for nail in spec['nails']:
        x, y, w, h = [nail[k] for k in ('x', 'y', 'width', 'height')]
        draw.rectangle((x-padding,y-padding,x+w+padding-1,y+h+padding-1),fill=0)
    sample_count = mask.histogram()[255]
    if not sample_count:
        raise ValueError('template leaves no shared background to check')
    if ImageChops.multiply(ImageOps.invert(alpha), mask).getbbox():
        return {'passed': False, 'reason': 'shared_background_is_transparent'}
    difference = ImageChops.difference(image, background)
    histogram = difference.histogram(mask=mask)
    channel_hist = [sum(histogram[c*256+i] for c in range(3)) for i in range(256)]
    max_delta = max(i for i,n in enumerate(channel_hist) if n)
    mean_delta = sum(i*n for i,n in enumerate(channel_hist)) / (sample_count*3)
    changed = sum(channel_hist[tolerance+1:])
    return {'passed': not changed, 'canvas': expected, 'background_pixels_checked': sample_count,
            'max_channel_difference': max_delta, 'mean_channel_difference': round(mean_delta,6),
            'channel_samples_over_tolerance': changed, 'tolerance': tolerance,
            'scope': 'canvas and shared background only; inspect fingers, plate sizes and decorations visually'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--template', type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument('--tolerance', type=int, default=0)
    args = parser.parse_args()
    try:
        result = check(args.image, args.template, args.tolerance)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'passed': False, 'error': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
