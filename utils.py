import ast
import hashlib
import os
import re
import subprocess

from PIL import Image, ImageSequence


def file_hash(path, algo="sha256", chunk_size=8192):
    """Compute a hash (default SHA-256) of a file's content."""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def get_slide_hash(slide_data):
    """Unique hash based on the text and associated video."""
    h = hashlib.sha256()
    h.update(slide_data["transcript"].encode("utf-8"))
    h.update(slide_data["best_hash"].encode("utf-8"))
    if "mp4_file" in slide_data and slide_data["mp4_file"]:
        video_path = slide_data["mp4_file"]
        try:
            video_hash = file_hash(video_path)
            h.update(video_hash.encode("utf-8"))
        except FileNotFoundError:
            print(f"⚠️ Video file not found: {video_path}")
    return h.hexdigest()[:12]


def exec_python_script_from_venv(abs_repo_path, wd, venv, script_path, *args):
    cwd = os.getcwd()
    interpreter = "%s/%s/bin/python" % (abs_repo_path, venv)
    command = [interpreter, script_path] + list(args)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=wd,
        env={**os.environ, "MPLBACKEND": "agg"},
    )
    if len(result.stdout) > 0:
        print("stdout:", result.stdout)
    if len(result.stderr) > 0:
        print("stderr:", result.stderr)
    os.chdir(cwd)


def rewrite_webp_with_original_fps(webp_image: Image.Image, output_path: str):
    """
    Rewrites an animated WebP file (input_path) into a new file (output_path),
    preserving all frames and their original durations (FPS equivalent).

    Args:
        webp_image (Image.Image): The original animated WebP image.
        output_path (str): Path where the rewritten WebP will be saved.
    """
    if os.path.exists(output_path):
        os.remove(output_path)

    # Lists to store each frame and its corresponding duration
    frames = []
    durations = []

    # Iterate over all frames in the animation
    for frame in ImageSequence.Iterator(webp_image):
        # Copy the frame to avoid referencing internal data
        frames.append(frame.copy())

        # Retrieve the duration (in milliseconds) from the frame metadata
        # Default to 100 ms if not specified (≈10 FPS)
        durations.append(frame.info.get("duration", 100))

    # Save the animation as WebP, preserving all frames and durations
    frames[0].save(
        output_path,
        save_all=True,  # Enables saving multiple frames
        append_images=frames[1:],  # Add all other frames after the first one
        duration=durations,  # Preserve per-frame timing
        loop=0,  # 0 = infinite loop
        disposal=0,  # Keep previous frame (important for smooth animation)
    )

    print(f"Animated WebP successfully rewritten to: {output_path}")


def parse_call(line: str):
    """
    Parse une ligne de type :
      - "ping"
      - "square(4)"
      - "square(  4 )"
    Retourne (nom_fonction, tuple_args)
    """
    s = line.strip()
    m = re.match(r"^([A-Za-z_]\w*)\s*(?:\((.*)\))?$", s)
    if not m:
        raise ValueError(f"Impossible de parser la ligne: {line!r}")

    name = m.group(1)
    args_src = m.group(2)

    args = []
    if args_src and args_src.strip():
        expr = ast.parse(f"f({args_src})", mode="eval")
        for a in expr.body.args:
            args.append(ast.literal_eval(a))
    return name, tuple(args)


def call_function_by_name(name: str, module_globals, args=()):
    func = module_globals.get(name)
    if not callable(func):
        raise PermissionError(f"Fonction inconnue ou non autorisée: {name!r}")
    return func(*args)


def format_srt_time(seconds: float) -> str:
    """
    Convert seconds (float) into the SRT time format: hh:mm:ss,mmm
    Example: 65.432 -> "00:01:05,432"
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def assemble_slides(slide_files, output_file="final_video.mp4"):
    with open("inputs.txt", "w") as f:
        for path in slide_files:
            f.write(f"file '{path}'\n")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "inputs.txt",
            "-c",
            "copy",
            "-threads",
            "0",
            output_file,
        ],
        check=True,
    )

    os.remove("inputs.txt")


# Opens the audio file in VSCode for playback.
def play_vscode(wav_path: str):
    import subprocess

    subprocess.run(["code", wav_path])
    subprocess.run(["code", wav_path])
