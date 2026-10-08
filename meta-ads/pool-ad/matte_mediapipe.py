"""Person matte with MediaPipe selfie_multiclass -> work/matte/<take>_alpha.mp4 (gray, source size, 30 fps)."""
import sys, subprocess, numpy as np, cv2
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
src, out = sys.argv[1], sys.argv[2]
W, H, FPS = 720, 1280, 30
opts = vision.ImageSegmenterOptions(base_options=mpt.BaseOptions(model_asset_path="work/models/selfie_multiclass_256x256.tflite"),
                                    running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True)
seg = vision.ImageSegmenter.create_from_options(opts)
rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
prev = None; i = 0
while True:
    buf = rd.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    res = seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)), int(i * 1000 / FPS))
    bg = res.confidence_masks[0].numpy_view()
    a = 1.0 - cv2.resize(bg, (W, H), interpolation=cv2.INTER_CUBIC)
    # edge-aware refine: guide the soft mask with the image, then tighten
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    try:
        a = cv2.ximgproc.guidedFilter(g, a.astype(np.float32), 6, 1e-3)
    except Exception:
        a = cv2.bilateralFilter(a.astype(np.float32), 9, 0.1, 5)
    a = np.clip((a - 0.5) * 2.2 + 0.5, 0, 1)
    if prev is not None: a = 0.6 * a + 0.4 * prev      # temporal smoothing against flicker
    prev = a
    wr.stdin.write((a * 255).astype(np.uint8).tobytes()); i += 1
wr.stdin.close(); wr.wait(); print("frames", i, "->", out)
