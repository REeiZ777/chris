---
name: pixel-art
description: Build detailed, animated pixel-art scenes and characters that run in the browser (single HTML file, canvas, no dependencies) with a cinematic finish — rain, fire, glowing windows, fog, bloom, lightning, water reflections, particles, animated characters casting spells or performing actions. Use this skill whenever the user wants pixel art, a retro/8-bit/16-bit look, a cozy or atmospheric animated scene, a "lo-fi" background, a Stardew/Celeste/Terraria-like vignette, an animated wallpaper, an animated sprite or character (wizard, knight, creature) doing an action, or asks to reproduce a pixel-art image, GIF or screen recording "with the same level of detail and animation" — including in French ("pixel art", "scène animée", "reproduis la même chose", "même niveau de détail"). Also use it to improve or add effects to an existing canvas pixel-art scene.
---

# Pixel art scenes

This skill produces hand-crafted-looking pixel-art scenes that are drawn procedurally
on a `<canvas>` and animated in real time. The result is one self-contained `.html`
file the user can open in a browser (and publish as an Artifact when that tool exists).

The quality bar is "looks like a professional pixel artist made it, and it feels alive":
every object has shading and texture, many small things move at different rhythms,
and light sources actually light the scene.

## Files in this skill

- `assets/template.html` — starter engine: layered low-res buffers, helpers, glow/bloom/fog/grain,
  resize, loop, controls. **Start every new scene from a copy of it.**
- `assets/example-floating-island.html` — complete reference scene (floating island at night in
  the rain: house, campfire, pond, waterfall, fireflies, lightning). Read the relevant part when
  you need a proven recipe (clouds, roof tiles, fire, rain collisions, water, etc.).
- `assets/example-wizard.html` — complete character piece: a wizard sprite whose staff and arms are
  posed by keyframes, a looping charge → fire → recover spell with particles, a bolt, rim light and
  light spilling on stones, plus click-to-cast and sound effects. Read it for any animated character.
- `references/techniques.md` — recipe book: pixel-art rules, palettes, and code patterns for
  each effect. Read the sections you need before drawing.
- `scripts/extract_frames.py` — turn a reference video/GIF into frames, a contact sheet and
  enlarged crops you can look at.
- `scripts/screenshot.js` — render the page headless once, save a PNG, report JS errors.

## Workflow

### 1. Understand the target

If the user gives a reference (image, GIF, screen recording), study it before writing code —
the details are what make the result convincing, and you can only reproduce what you noticed.

- Video/GIF: `python3 scripts/extract_frames.py <file> <outdir>` (installs a bundled ffmpeg
  through `imageio-ffmpeg` if none is present). Look at the contact sheet first to see what
  changes over time, then at the enlarged crops to read individual pixels.
- Screen recordings of social posts contain UI around the art: find the scene rectangle in one
  full frame first, then pass it as `--crop W:H:X:Y` so the crops show only the art.
- Anything that animates (a character, a spell): rerun with `--region W:H:X:Y --region-fps 6` and
  read the `region_NN.jpg` sheets pose by pose. Write down the **timeline**: each pose, when it
  starts, how long it holds, what effect happens at each moment, and the cycle length.
- Make an inventory: every object, its colour, its position, and **what moves and how**
  (direction, speed, rhythm). Note the light sources and what they illuminate.
- Convert positions to the low-res grid: measure in the enlarged crop, multiply by
  `gridWidth / cropWidth`. Writing these coordinates down first keeps the layout faithful.

Without a reference, decide a concept with one focal light (a fire, a window, a lamp), a
contrasting cool ambient (night blue, dusk purple), and 10–20 small animated details.

### 2. Pick the grid

Work at a small internal resolution and upscale with nearest-neighbour: 320×180 or
384×216 (16:9) are good defaults. Smaller = chunkier pixels; larger = more detail but
more work per object. Everything is positioned in grid units.

With a reference, **match its pixel size and aspect ratio instead**: measure one art pixel in
the enlarged crop (a hat edge, a star), divide the scene width and height by it, and use that
grid (the wizard reference gave 150×112). Update the stage's CSS `aspect-ratio` and width
formula to the same ratio.

### 3. Build in layers (copy `assets/template.html`)

The template's pipeline is the backbone; keep it:

1. **Background buffer** (low-res): sky gradient with Bayer dithering, stars, moon, clouds,
   distant hills, far rain.
2. **Foreground buffer** (low-res, transparent, a few rows taller than the grid): the main
   subject and everything attached to it. Can be composited with a sub-pixel offset
   (e.g. a floating island that bobs).
3. **Near buffer** (low-res, transparent): near rain, splashes — anything in front.
4. **Screen pass** (full resolution, on the visible canvas): nearest-neighbour upscale of the
   three buffers, then additive radial glows for every light, flattened light pools on the
   ground, bloom, fog, foreground bokeh, vignette, film grain.

Static things (terrain texture, buildings, trees) are rendered **once** into offscreen canvases
with seeded randomness; only moving things are drawn every frame. This keeps it fast and
stops textures from shimmering.

### 4. Draw like a pixel artist

The full rules are in `references/techniques.md`; the ones that matter most:

- Limited, hue-shifted palette: shadows shift toward blue/purple, highlights toward yellow.
  Never pure grey. Pick ~4 values per material.
- Every shape gets: a highlight edge on the side facing the main light, a dark outline or
  shadow row at the bottom, texture (noise, planks, tiles, bricks) that follows a pattern.
- Dither gradients with a 4×4 Bayer matrix, then quantise colours — that's what makes
  it read as pixel art instead of a blurry gradient.
- Use deterministic `hash(x, y)` / seeded `rng()` for texture and placement, never
  `Math.random()` in static layers.
- Tiny sprites as string arrays (`'.XX.'`) with a palette map — fast to write and edit.
- Details sell the scene: a cat in the window, a door left ajar with light leaking,
  a fossil in the ground, a crystal that pulses, grass tufts, flowers, a mug that steams.

### 5. Make it alive

Aim for many independent motions at different speeds so nothing looks looped:
twinkling stars (per-star phase), drifting clouds, particle fire + rising sparks, chimney
smoke, rain that collides with surfaces and splashes (ripples on water), fireflies on
Lissajous paths, bobbing lanterns/boats, flickering windows, occasional events on timers
(a shadow passing a window every 14 s, a lamp flicker every 11 s, a shooting star, distant
lightning). Recipes for each are in `references/techniques.md`.

### 5b. Animated characters and action sequences

Characters look hand-animated when the body is a string-array sprite and only the moving parts
(arms, held items) are drawn procedurally from a pose:
- Pose = hand position + held-item angle + extra limbs; keyframes `[time, x, y, angle, ...]`
  interpolated with smoothstep. The held item and sleeves are drawn as outline stamps then a
  1–2 px core along the line, so any angle still reads as pixel art.
- Drive everything from one cycle clock (`c = (T - cycle0) % P`) and fire events when `c`
  crosses a threshold (start charge, release). A button, a click on the scene and a key
  (e.g. `E`, listened on `window`, ignoring repeats and text fields) jump the clock to the start
  of the action, so the viewer can trigger it. Make the stage focusable (`tabindex="0"`) and
  focus it on load and on click: inside an embedded frame, keys only arrive once the page has focus.
- Sell the action with anticipation (raise/charge), a fast release (short swing, 1 px recoil)
  and a follow-through (hold, then ease back); idle gets breathing (upper rows shift 1 px),
  blinking and a few ambient particles.
- Spell/impact recipes (orbiting charge sparks, vortex, sparkle burst, expanding ring, bolt with
  broken trail, debris) are in `references/techniques.md` §10.
- Magic light lands on things: rim-light the sprite's up/right outline pixels, recolour the
  ground's top row under the light, add screen-pass glows and pools.

### 6. Cinematic finish

This is what turned a good scene into a great one in practice:
- Additive glow per light source + flattened light pools where light hits the ground.
- Bloom: bright-pass a quarter-size copy, blur by repeated halving, add back.
- Rain tinted by nearby lights (drops turn warm as they pass the fire or the lamp).
- Fog layers behind and in front of the subject; moonbeams; silver cloud edges near the moon.
- Reflections of lights in water (broken, shimmering streaks).
- Vignette + subtle film grain.
Keep effects subtle — alphas of 0.03–0.4. If the moon or a white object blows out under
bloom, damp the bloom locally rather than dimming the whole effect.

### 7. Controls and accessibility

Include: pause/play, a toggle for the main weather/effect intensity, fullscreen, and optional
synthesised ambient sound (Web Audio noise; sound must start from a click). Respect
`prefers-reduced-motion`: slow the animation down and **disable flashes** (lightning) —
flashing can hurt photosensitive viewers. Give the canvas an `aria-label` describing the scene.
Match the UI language to the user's language.

### 8. Check once, then deliver

Run `node scripts/screenshot.js <file.html> <out.png> [waitMs]` once, choosing `waitMs` so the
shot lands on the most informative moment (e.g. mid-charge for a spell, so both the sprite and
the effect are visible) (uses the preinstalled
Playwright/Chromium; set `NODE_PATH=$(npm root -g)` if the module isn't found). Look at the
image, compare it to the reference, fix what's off in one pass (proportions, a blown-out
highlight, an effect that's too faint), and deliver. Don't build a screenshot loop.
Font-loading errors from Google Fonts in a sandbox are expected and harmless.

Deliver the `.html` file; if an Artifact tool is available, also publish it (strip the
`<!doctype>`, `<html>`, `<head>`, `<body>` wrapper lines, since the Artifact skeleton adds its own),
so the user can open it with one click. Tell the user what's animated and what the controls do.
