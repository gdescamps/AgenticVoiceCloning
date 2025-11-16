import hashlib
import os
import subprocess


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
