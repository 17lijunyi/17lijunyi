#!/usr/bin/env node
// Build code-native window frames around the approved, unchanged artwork.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const option = name => { const index = args.indexOf(name); return index < 0 ? undefined : args[index + 1]; };
const moduleDirectory = option('--modules-dir');
const require = createRequire(moduleDirectory ? path.join(path.resolve(moduleDirectory), '_cover.cjs') : import.meta.url);
const sharp = require('sharp');
const {PNG} = require('pngjs');
const config = JSON.parse(await fs.readFile(path.join(root, 'projects.json'), 'utf8'));
const labels = {product: '产品', skill: 'Skills', document: '文档', repository: '其他'};
const themes = {
  lavender: ['#776287', '#eee7f5', '#62506f'],
  rose: ['#987084', '#f8e7ed', '#815e73'],
  blue: ['#6b80a3', '#e7edf8', '#526d96'],
  sage: ['#718a7d', '#e8f1eb', '#557465'],
  teal: ['#658d8c', '#e3f2f0', '#477c79'],
  peach: ['#a47d75', '#f9e9e3', '#8b645c'],
  amber: ['#a28e64', '#faf0d8', '#867144']
};
const escape = text => String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
function icon(category, color) {
  const start = `<g transform="translate(146 38)" fill="none" stroke="${color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">`;
  const paths = {
    product: '<rect x="0" y="0" width="54" height="54" rx="12"/><rect x="11" y="11" width="10" height="10" rx="2"/><rect x="33" y="11" width="10" height="10" rx="2"/><rect x="11" y="33" width="10" height="10" rx="2"/><rect x="33" y="33" width="10" height="10" rx="2"/>',
    skill: '<path d="M27 0 51 13v28L27 54 3 41V13Z M3 13l24 14 24-14 M27 27v27 M15 7l24 14"/>',
    document: '<path d="M6 0h28l14 14v40H6Z M34 0v14h14 M15 27h24 M15 38h24"/>',
    repository: '<path d="M2 13h19l6 7h26v29H2Z M2 13V6h21l6 7"/>'
  };
  return start + paths[category] + '</g>';
}
function ornaments(category, width, color) {
  const g = `<g fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" opacity=".65">`;
  if (category === 'skill') {
    return g + [0, 1, 2].map((i) => {
      const x = width - 290 + i * 88;
      const sign = i === 0 ? `<circle cx="${x + 24}" cy="65" r="5" fill="${color}"/>` : i === 1 ? `<path d="m${x + 12} 64 8 8 16-19"/>` : `<path d="M${x + 13} 59h22 M${x + 13} 71h22"/>`;
      const link = i < 2 ? `<path d="M${x + 48} 65h40 m-8-7 8 7-8 7"/>` : '';
      return `<rect x="${x}" y="41" width="48" height="48" rx="12"/>${sign}${link}`;
    }).join('') + '</g>';
  }
  if (category === 'document') {
    return g + `<path d="M${width - 275} 51h100 M${width - 275} 66h100 M${width - 275} 81h100"/>` + '</g>' + `<path d="M${width - 84} 17v74h67Z" fill="${color}" opacity=".12"/><path d="M${width - 84} 17v74h67" fill="none" stroke="${color}" stroke-width="3" opacity=".55"/>`;
  }
  return g + `<path d="M${width - 185} 82h40"/><rect x="${width - 117}" y="50" width="32" height="32" rx="5"/><path d="m${width - 58} 51 31 31 m0-31-31 31"/>` + '</g>';
}

const selected = option('--only');
const report = [];
for (const [id, item] of Object.entries(config.overrides)) {
  if (!item.artwork || (selected && id !== selected)) continue;
  const sourcePath = item.artwork;
  const outputPath = item.cover;
  if (!/^assets\/project-covers\/[a-zA-Z0-9._-]+\.png$/.test(sourcePath) ||
      !/^assets\/project-covers\/[a-zA-Z0-9._-]+-window\.png$/.test(outputPath) || sourcePath === outputPath) {
    throw new Error(`Invalid artwork/output path for ${id}`);
  }
  const category = id.startsWith('skill:') ? 'skill' : (item.category ?? 'repository');
  if (!labels[category]) throw new Error(`Invalid category for ${id}`);
  const theme = themes[item.window_theme ?? ({product: 'lavender', skill: 'sage', document: 'blue', repository: 'amber'}[category])];
  if (!theme) throw new Error(`Invalid window theme for ${id}`);
  const [border, header, text] = theme;
  const artwork = await fs.readFile(path.join(root, sourcePath));
  const original = PNG.sync.read(artwork);
  const left = 40, top = 146;
  const width = original.width + left * 2, height = original.height + top + 36;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<defs><clipPath id="window"><rect x="6" y="6" width="${width - 12}" height="${height - 12}" rx="38"/></clipPath></defs>
<rect width="${width}" height="${height}" fill="#ffffff"/>
<rect x="6" y="6" width="${width - 12}" height="${height - 12}" rx="38" fill="#fffdf8"/>
<path d="M6 6h${width - 12}v122H6Z" clip-path="url(#window)" fill="${header}"/>
<path d="M9 130h${width - 18}" stroke="${border}" stroke-opacity=".20" stroke-width="3"/>
<g fill="${border}" opacity=".75"><circle cx="49" cy="65" r="10"/><circle cx="81" cy="65" r="10"/><circle cx="113" cy="65" r="10"/></g>
${icon(category, text)}
<text x="228" y="91" font-family="Arial Unicode MS, PingFang SC, sans-serif" font-size="80" font-weight="600" fill="${text}">${escape(labels[category])}</text>
${ornaments(category, width, border)}
<rect x="6" y="6" width="${width - 12}" height="${height - 12}" rx="38" fill="none" stroke="${border}" stroke-width="5"/>
</svg>`;
  const window = await sharp(Buffer.from(svg)).ensureAlpha().raw().toBuffer();
  // Place original pixels at integer coordinates: no rescaling, redraw or color conversion.
  for (let y = 0; y < original.height; y++) {
    const start = ((y + top) * width + left) * 4;
    window.set(original.data.subarray(y * original.width * 4, (y + 1) * original.width * 4), start);
  }
  const encoded = PNG.sync.write({width, height, data: window});
  const decoded = PNG.sync.read(encoded);
  for (let y = 0; y < original.height; y++) {
    const start = ((y + top) * width + left) * 4;
    if (!decoded.data.subarray(start, start + original.width * 4).equals(original.data.subarray(y * original.width * 4, (y + 1) * original.width * 4))) {
      throw new Error(`Artwork pixels changed for ${id}`);
    }
  }
  await fs.writeFile(path.join(root, outputPath), encoded);
  report.push({id, category: labels[category], artwork: sourcePath, cover: outputPath, width, height, artworkPixelsPreserved: true});
}
if (!report.length) throw new Error('No artwork configured or --only did not match a project');
console.log(JSON.stringify(report, null, 2));
