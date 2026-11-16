#!/usr/bin/env node
/*
 * Render a resolved scene (scene.json from make_short.py) to a vertical MP4.
 *
 * Each frame is drawn by template.html at an exact time, captured from
 * headless Chromium, and piped into ffmpeg. The audio track is the
 * narration + sound-effect mix that make_short.py prepared. There is no music.
 *
 * Usage:
 *   node local/render.cjs <scene.json> <out.mp4> --audio <audio.wav>
 *   node local/render.cjs <scene.json> <dir> --stills 0.5,4,9.2   (PNG previews)
 */
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : fallback;
}

function loadIconSet() {
  const candidates = [];
  try { candidates.push(require.resolve('@iconify-json/fluent-emoji/icons.json', { paths: [__dirname] })); } catch (_) { /* not installed next to the script */ }
  if (process.env.FLUENT_EMOJI_JSON) candidates.push(process.env.FLUENT_EMOJI_JSON);
  for (const c of candidates) if (fs.existsSync(c)) return JSON.parse(fs.readFileSync(c, 'utf8'));
  throw new Error('Fluent Emoji icon set not found. Run "npm install" in local/ (see local/setup.sh).');
}

function iconMarkup(set, name) {
  let icon = set.icons[name];
  if (!icon && set.aliases && set.aliases[name]) icon = set.icons[set.aliases[name].parent];
  if (!icon) throw new Error(`Unknown icon "${name}". Browse names at https://icon-sets.iconify.design/fluent-emoji/`);
  const w = icon.width || set.width || 32;
  const h = icon.height || set.height || 32;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}">${icon.body}</svg>`;
}

async function main() {
  const [scenePath, outPath] = process.argv.slice(2);
  if (!scenePath || !outPath) {
    console.error('usage: render.cjs <scene.json> <out.mp4|dir> [--audio a.wav] [--stills t1,t2]');
    process.exit(2);
  }
  const scene = JSON.parse(fs.readFileSync(scenePath, 'utf8'));
  const fps = Number(arg('--fps', scene.fps || 30));
  const stills = arg('--stills', null);
  const audio = arg('--audio', null);

  const set = loadIconSet();
  const icons = {};
  for (const beat of scene.beats) {
    for (const el of beat.elements || []) {
      if (el.name) icons[el.name] = iconMarkup(set, el.name);
    }
  }

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'template.html'));
  const info = await page.evaluate(async ({ scene, icons }) => window.setup(scene, icons), { scene, icons });
  console.log(`[render] ${info.items} elements, ${info.chunks} caption chunks`);

  if (stills) {
    fs.mkdirSync(outPath, { recursive: true });
    for (const t of stills.split(',').map(Number)) {
      await page.evaluate(tt => window.renderFrame(tt), t);
      const file = path.join(outPath, `still_${t.toFixed(2)}.png`);
      await page.screenshot({ path: file });
      console.log(`[render] ${file}`);
    }
    await browser.close();
    return;
  }

  if (!audio) throw new Error('--audio is required for a video render');
  const frames = Math.ceil(scene.duration * fps);
  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-i', audio,
    '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-r', String(fps), '-g', String(fps * 2),
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
    '-movflags', '+faststart', '-shortest', outPath,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((resolve, reject) => ff.on('close', code => (code === 0 ? resolve() : reject(new Error(`ffmpeg exited with ${code}`)))));

  const started = Date.now();
  for (let i = 0; i < frames; i++) {
    await page.evaluate(tt => window.renderFrame(tt), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 90 === 0) process.stdout.write(`\r[render] frame ${i}/${frames}`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log(`\r[render] ${frames} frames in ${((Date.now() - started) / 1000).toFixed(0)}s -> ${outPath}`);
}

main().catch(err => { console.error(err); process.exit(1); });
