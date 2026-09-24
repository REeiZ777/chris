# Pixel-art techniques — recipe book

Every recipe below is implemented in a working scene in `assets/example-floating-island.html`;
search it by the function names given.

## Contents
1. Core helpers
2. Palette and shading rules
3. Static layers (sky, hills, terrain, buildings, trees, clouds, moon)
4. Sprites
5. Animated elements (fire, smoke, sparks, rain, water, waterfall, fireflies, lanterns, drips, leaves, characters)
6. Timed events (window shadow, lamp flicker, shooting star, lightning)
7. Screen pass (glow, light pools, bloom, fog, moonbeams, bokeh, vignette, grain)
8. Sound
9. Performance notes
10. Characters and spell effects

---

## 1. Core helpers

All in `assets/template.html`:

```js
rect(g, x, y, w, h, color)   // rounded fillRect on a low-res context
pix(g, x, y, color)          // one pixel
line(g, x0, y0, x1, y1, color, step)   // Bresenham; step=2 gives a dotted line
sprite(g, x, y, rows, palette)         // rows: ['.XX.', 'XooX'], palette: {X:'#..', o:'#..'}
hash(x, y, seed) -> [0,1)    // deterministic noise for textures
rng(seed) -> () => [0,1)     // seeded PRNG (mulberry32) for placement
bay(x, y) -> [-0.5, 0.5)     // 4x4 Bayer threshold for dithering
hex('#rrggbb') -> [r,g,b]; mix(a, b, t); css([r,g,b], alpha)
```

Draw functions use a module-level `let b` that points at the current layer context; switch
it (`b = fgx`) before drawing a layer so the same helpers work everywhere.

## 2. Palette and shading rules

- **Hue shifting**: darker shades rotate toward blue/purple, lighter ones toward yellow/orange.
  Example dirt: `#46374b` top → `#211a2b` deep; stone `#7a7896` / `#5d5b77` / `#44425a`.
- **Night scenes**: ambient is indigo (`#0a0b22` → `#2b2763` sky). Warm lights are
  `#ffe39a` (core), `#ffb02e`, `#e8802a` (edges). Magic/water accents in teal `#7fe6f2`.
  Warm vs cool contrast is the whole mood; keep saturated colours for lights only.
- **Each material ≈ 4 values**: highlight, base, shade, outline. Put the highlight on the edge
  facing the main light, the outline/shadow on the bottom row.
- **Dithered gradient**: for each pixel, `t = y/H + bay(x,y)*0.05`, interpolate between colour
  stops, then quantise each channel (`Math.round(c/3)*3`). Write to ImageData for speed.
- **Texture patterns**: planks — darker line every 3rd row plus seams at `(x + row*5) % 16`;
  roof tiles — dark row every 3 rows, light dot when `(x + tileRow*2) % 4 == 0`; bricks — mortar
  every 3rd row and staggered joints; plaster — sparse darker/lighter hash pixels.
- **Terrain mass**: fill a polygon on an offscreen canvas, read its alpha as a mask, then texture
  every masked pixel: depth gradient + strata `sin(y*0.55 + sin(x*0.05)*2)` + two-scale hash
  noise + Bayer, quantised. Edge pixels: bottom → near-black outline, light-facing side → lighter.
  Scatter stones (3-value ellipses with a shadow row) and pebbles with a seeded RNG.

## 3. Static layers

- **Hills**: per column, `y = base + A1*sin(x*f1+p1) + A2*sin(x*f2+p2) + A3*sin(x*f3)`; fill down.
  Two ranges: far (lighter, `#1c1a3e`) and near (darker). One lighter pixel on the ridge.
- **Clouds** (`makeCloud`): union of wide ellipses (`((x-bx)/1.7)^2 + (y-by)^2 < r^2`) on top of a
  flat rounded base. Shade: top edge highlight, row below it dithered, bottom edge dark, lower
  third dithered darker. Render a second "lit" version with bright edges and blend it in by
  proximity to the moon and during lightning.
- **Moon**: circle; shade the crescent where `hypot(dx+3, dy+3) > r` (light from upper-left);
  craters as small circles with a dark rim on the upper-left; 1px lighter rim.
- **House**: build bottom-up — foundation stones, plank wall, beam, plaster upper floor with
  half-timber beams (vertical posts + diagonal braces drawn with `line`), window frames with
  sills, door with panels and knob, roof rows with `halfWidth = (y-peak)*slope`, round attic
  window, chimney clipped to the roof line, cap. Window glass is drawn dynamically (it flickers).
- **Tree**: recursive `branch(x, y, angle, len, depth, thickness)` with a seeded RNG; collect tip
  positions for berries/leaves and for spawning falling leaves later.
- **Props**: umbrella as stacked rows with scalloped bottom and ribs; bench; firewood pile as
  log ends (dark ring, lit centre); campfire stones and crossed logs; grass tufts and flower
  pixels along the ground line using `hash(x, k)` thresholds.

## 4. Sprites

String-array sprites are ideal for anything under ~12×12: characters, animals in windows,
lanterns, crystals, fossils. Animate by swapping a few pixels (a tail, an arm, a head offset)
rather than redrawing whole frames. Example character sipping from a mug every 9 s:
`const sip = (t % 9) > 6.4 && (t % 9) < 8;` then move the mug/arm pixels and raise the head 1px.

## 5. Animated elements

- **Fire** (`spawnFire`, `drawFire`): each frame draw a jittery core (stacked rows, widths
  7,7,5,5,3,1, yellow → white) plus ~55 particles/s rising at 12–22 px/s, pulled toward the
  centre, 2px when young then 1px; colour by life: `#fff6c0` → `#ffd050` → `#ff8a20` → `#c83a18`.
  Flicker value `fire = 0.75 + 0.15 sin(9.1t) + 0.1 sin(23.7t) + noise` drives its glows.
- **Sparks**: ~7/s, rise 18–34 px/s with sinusoidal sideways wobble, fade over 1–3 s, own tiny glow.
- **Smoke**: ~14/s from the chimney top, drift up and sideways with wobble, size 1→3 px,
  alpha 0.7→0, colour from light to darker grey-violet.
- **Rain**: pool of ~340 drops with depth `z`. Far drops (z<0.42) are drawn on the background
  layer, dim and short; near drops on the near layer, brighter and longer. Near drops get a
  `stop` y from `surfaceAt(x)` (roof line, umbrella, water, ground) and on impact spawn two
  splash particles with gravity, or a ripple if they hit water. Tint near drops by distance to
  the light list (`LIGHTS`) so they glow warm near the fire and lamps. Rain intensity = how
  many drops of the pool are active.
- **Water** (`drawWater`): recompute a small ImageData every frame: vertical gradient +
  `sin(x*0.55 + t*1.1 + sin(y*0.45+t*0.7)*1.5) + sin(y*0.9 - t*0.9 + x*0.17)` thresholded into
  highlight/dark cells, animated surface row, glassy side column. Add reeds swaying with height
  weighting, a fish on a ping-pong path, expanding ripple pixels.
- **Reflections**: under each light over water, draw a broken vertical streak (hash-based gaps,
  sinusoidal sideways offset growing with depth, fading alpha). Mirror fireflies below the
  surface with the y distance compressed by ~0.45.
- **Waterfall**: per row, 2–3 pixels whose colour comes from `hash(x, floor(y - t*46))` so the
  pattern scrolls down; thin out and fade with distance.
- **Fireflies**: base point + two sines on each axis (Lissajous), blink `max(0, sin)^0.6`;
  2×2 bright pixel when strong, 1px otherwise; teal glow.
- **Floating lanterns / boats**: `y + round(sin(t*1.3 + i*2.1) * 1.4)`, each with its own phase.
- **Drips**: droplet brightens at a source for 1.4–3 s, then falls with gravity, then resets.
- **Falling leaves**: spawn at tree tips, sway down, land on `surfaceAt(x)`, fade after 3 s.
- **Stars**: 150+ with individual phase/speed; a few 4-point sparkles whose arms grow with the pulse.

## 6. Timed events

Put rare events on `t % period` windows or countdown timers with random intervals:
a silhouette walking past a window (`walk = (t % 14) / 2.6`, clipped to the glass), a street
lamp stutter (`t % 11` in [7.2, 7.5]), shooting star (every 9–18 s, 9-pixel fading trail),
lightning (every 16–32 s): intensity curve 0.9 → 0.2 → 0.75 → fade over 0.55 s; add a blue
wash to the sky layer, fade in the lit clouds, draw a jagged bolt with a branch **behind the
hills** at the screen edge, add a screen tint and a big soft glow, schedule thunder 0.7–1.7 s
later. Skip flashes under `prefers-reduced-motion`.

## 7. Screen pass

- **Glow**: radial gradient with stops `a`, `0.38a` at 35%, 0 at 100%, `globalCompositeOperation =
  'lighter'`. Typical radii (grid units): fire 48–54, lamp 22 + core 6, windows 17–20,
  lanterns 12, fireflies 8, crystals 14. Add the layer's offset (`gOff`) for moving layers.
- **Light pool**: same gradient, `ctx.scale(1, ry/rx)` to flatten it onto the ground.
- **Lamp cone**: trapezoid filled with a vertical linear gradient, alpha ~0.17 → 0.
- **Bloom**: draw layers into a 192×108 canvas, halve to 96×54, `getImageData`, keep only
  pixels with luminance > ~100 (smooth ramp), put back, halve to 48×27 and 24×14, then draw all
  three scaled up with smoothing on, additive, alphas ~0.3/0.38/0.42. Damp specific regions
  (e.g. multiply by 0.25 around a white moon) if they blow out.
- **Fog**: pre-render a wide texture of soft tinted radial blobs that wraps horizontally (draw
  each blob at x-w, x, x+w); scroll two copies. One layer behind the subject, a thinner one in
  front of its base. `source-over`, bluish tint.
- **Moonbeams**: 3–4 thin triangles from the moon with linear gradients, alpha 0.02–0.035,
  slowly breathing; plus a faint halo ring (radial gradient with a band).
- **Foreground bokeh rain**: ~16 long, wide, very faint streaks at screen resolution, fast.
- **Vignette**: radial gradient to `rgba(4,4,14,0.55)`.
- **Grain**: 192×192 noise canvas as a repeating pattern, random offset every frame, alpha ≤ 0.08.

## 8. Sound (optional, from a button)

Web Audio: a 2 s white-noise buffer looped through a lowpass (~1500 Hz) for rain, gain tied to
rain intensity; fire crackle = short bandpassed noise bursts on a 70 ms timer with random
gain; thunder = the noise through a 140 Hz lowpass with a 0.25 s attack and 3 s decay.

## 9. Performance notes

- Per-frame `fillRect` of single pixels is fine at 384×216 for a few thousand calls; move big
  per-pixel work (water) to a small ImageData.
- Pre-render anything that doesn't move. Keep particle arrays bounded (lifetimes).
- Cap `dt` at 0.05 s and set it to 0 when paused or `document.hidden`.
- Canvas backing size = CSS size × min(2, devicePixelRatio); scale `S = canvas.width / W`.

## 10. Characters and spell effects

Implemented in `assets/example-wizard.html` (search `drawWizard`, `drawArm`, `drawStaff`,
`pose`, `release`).

- **Body sprite**: ~22×34 string array, facing the action. Materials: robe (base, shade,
  highlight), trim bands in orange, skin (2 values), beard/hair (2 values + grey dots), outline
  `#2a0f1e`. A hat or hood with a curled tip, a trim band and a small emblem gives character.
- **Breathing**: when idle, draw rows 0–20 one row lower and skip row 21, so the upper body sinks
  1 px without leaving a gap. **Blink**: swap the eye colour for skin for ~0.13 s every ~4 s.
- **Limbs and held items**: `drawArm(shoulder, hand)` stamps 4×4 outline squares then 2×2 cloth
  along the segment, a highlight every other step, and a 2×2 hand at the end.
  `drawStaff(hand, angle)` extends 24 px ahead and 13 px behind the hand: 3×3 dark stamps, then
  a 1 px wood core with a lighter grain pixel every few steps, fork prongs on the perpendicular,
  and a cross-shaped gem that brightens (and grows arms) with the charge.
- **Keyframes**: `[t, handX, handY, angleDeg, backArm]`, e.g. idle (-90°) → raise (−80°, hand 13 px
  higher, 0.3 s) → hold while charging (1.4 s) → swing forward (−12°, 0.18 s) → hold 0.7 s →
  return 0.45 s. Add tremble when charge > 0.75 (hand ±1 px) and a 1 px recoil for 0.1 s on release.
- **Charge**: spawn 26→66 sparks/s on flattened orbits (`y = r·sin(a)·0.55`) around the gem, each
  with its own angular speed (some reversed), radius shrinking faster as charge grows; fast ones
  draw as a line from their previous position (motion dash). When one reaches the centre, flash a
  white pixel. Behind them, a rotating dotted purple ellipse (the vortex) grows with the charge.
- **Release**: (1) a sparkle sphere at the tip for 0.3 s: dotted circle growing `3 + 10·√k`, plus
  random interior pixels re-rolled each frame; (2) a sparse dotted shockwave ring growing to ~100 px
  over 0.9 s with ease-out, fading; (3) ~45 debris sparks with drag and slight gravity, some drawn
  as dashes; (4) leftover orbit sparks thrown outward; (5) a short screen tint (skip under reduced
  motion); (6) the sound: bandpassed noise burst + sine sweep 1300→90 Hz.
- **Bolt**: travels ~190 px/s; draw a 3×3 plus-shaped core with a white centre and a 25 px trail
  whose pixels drop out by `hash(i, floor(T·24))` more often further back, colours white → cyan →
  blue → violet; shed small sparks behind it.
- **Palette for magic**: `#ffffff`, `#c8f4ff`, `#7fd8ff`, `#5aa2ff`, `#7f6bff`, `#a58cff`. Blue-violet
  magic reads best against a warm red/orange character and a violet night sky.
- **Sky with visible bands** (common in pixel-art references): 4 flat band colours with a 3-row
  Bayer ramp (25/50/75 %) above each edge, rather than a smooth dithered gradient.
- **Moon under bloom**: multiply the bright-pass by ~0.12 inside the moon disc and keep its own
  glow ≤ 0.08, otherwise the craters vanish.
