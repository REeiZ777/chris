#!/usr/bin/env python3
"""Turn a reference video or GIF into frames you can inspect.

Usage: python3 extract_frames.py <video> <outdir> [--fps 2] [--crop W:H:X:Y] [--zoom 2]
                                 [--region W:H:X:Y] [--region-fps 6]

Produces in <outdir>:
  frames/NNN.jpg     frames at --fps, 400 px wide (for an overview)
  sheet.jpg          contact sheet of those frames (see what changes over time)
  crop_<t>.png       full-resolution crops at 3 moments, enlarged with nearest-neighbour
                     (read individual pixels; pass --crop to frame the scene)
  region_NN.jpg      with --region: 5x5 sheets of one area sampled at --region-fps
                     (read a character's animation pose by pose)
Prints duration and resolution. Uses ffmpeg from PATH, else installs imageio-ffmpeg.
"""
import argparse, glob, math, os, re, shutil, subprocess, sys


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg"], check=True)
        import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("outdir")
    ap.add_argument("--fps", type=float, default=2)
    ap.add_argument("--crop", help="W:H:X:Y region of the source containing the scene")
    ap.add_argument("--zoom", type=int, default=2, help="nearest-neighbour enlargement of crops")
    ap.add_argument("--region", help="W:H:X:Y area to sample densely (e.g. an animated character)")
    ap.add_argument("--region-fps", type=float, default=6)
    a = ap.parse_args()
    ff = find_ffmpeg()
    os.makedirs(os.path.join(a.outdir, "frames"), exist_ok=True)

    info = subprocess.run([ff, "-i", a.video], capture_output=True, text=True).stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    seconds = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0
    size = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", info)
    print(f"duration: {seconds:.2f}s  size: {size.group(1)}x{size.group(2)}" if size else f"duration: {seconds:.2f}s")

    q = ["-loglevel", "error", "-y"]
    subprocess.run([ff, *q, "-i", a.video, "-vf", f"fps={a.fps},scale=400:-1",
                    os.path.join(a.outdir, "frames", "%03d.jpg")], check=True)
    n = len(glob.glob(os.path.join(a.outdir, "frames", "*.jpg")))
    cols = min(7, max(1, n)); rows = math.ceil(n / cols)
    subprocess.run([ff, *q, "-i", os.path.join(a.outdir, "frames", "%03d.jpg"),
                    "-vf", f"scale=300:-1,tile={cols}x{rows}", "-frames:v", "1",
                    os.path.join(a.outdir, "sheet.jpg")], check=True)

    vf = (f"crop={a.crop}," if a.crop else "") + f"scale=iw*{a.zoom}:-1:flags=neighbor"
    for t in ([seconds * 0.1, seconds * 0.5, seconds * 0.85] if seconds else [0]):
        subprocess.run([ff, *q, "-ss", f"{t:.2f}", "-i", a.video, "-frames:v", "1", "-vf", vf,
                        os.path.join(a.outdir, f"crop_{t:05.2f}.png")], check=True)
    if a.region:
        rdir = os.path.join(a.outdir, "region"); os.makedirs(rdir, exist_ok=True)
        subprocess.run([ff, *q, "-i", a.video, "-vf", f"fps={a.region_fps},crop={a.region}",
                        os.path.join(rdir, "%03d.png")], check=True)
        rn = len(glob.glob(os.path.join(rdir, "*.png")))
        for k in range(0, rn, 25):
            subprocess.run([ff, *q, "-start_number", str(k + 1), "-i", os.path.join(rdir, "%03d.png"),
                            "-vf", "scale=250:-1,tile=5x5", "-frames:v", "1",
                            os.path.join(a.outdir, f"region_{k // 25:02d}.jpg")], check=True)
        print(f"{rn} region frames at {a.region_fps} fps -> region_NN.jpg (read left-to-right, top-to-bottom)")
    print(f"{n} frames, sheet.jpg and crops written to {a.outdir}")


if __name__ == "__main__":
    main()
