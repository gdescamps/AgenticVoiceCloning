# Computes the pitch adjustment needed to reach a target characters-per-minute rate for the given audio and text.
import hashlib
import os
import shutil
import subprocess

from llm import save_cache, wavtext2text
from utils import exec_python_script_from_venv


# Function to compute the pitch adjustment required to achieve a target characters-per-minute (CPM) rate.
def compute_speech_pitch(wav_path: str, transcript: str, target_cpm: int = 900) -> int:
    # Returns the duration of the audio file in seconds using ffprobe.
    def get_audio_duration(path):
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        return float(result.stdout.strip())

    duration = get_audio_duration(wav_path)

    n_chars = len(transcript)
    if n_chars == 0:
        return 0

    # Calculate characters per minute based on audio duration.
    chars_per_min = n_chars / (duration / 60)

    # Compute the adjustment factor to match the target CPM.
    factor = target_cpm / chars_per_min

    # Convert the factor to a pitch value.
    pitch_float = factor - 1.0
    pitch = 100.0 * pitch_float
    pitch = int(round(pitch))
    return pitch


# Applies the computed pitch adjustment to the audio file using ffmpeg.
def apply_speech_pitch(wav_path: str, pitch: int) -> str:
    if pitch == 0:
        return wav_path

    # Calculate the tempo adjustment factor.
    factor = float(100 + pitch) / 100.0

    # Build the ffmpeg filter string.
    tempo_filter = f"atempo={factor:.2f}"
    temp_path = wav_path + f".{pitch}.wav"

    if not os.path.exists(temp_path):
        # Run ffmpeg to apply the tempo filter and save the result.
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-filter:a", tempo_filter, temp_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return temp_path


# Evaluates the quality of the speech audio by prompting an LLM and returns a score from 1 to 1000.
def evaluate_speech_quality(wav_path: str, transcript: str) -> int:

    # Prepare the prompt for the LLM to rate the speech quality.
    prompt = f"""
    You are an evaluator of English speech quality.
    Rate the speech from 1 to 1000.

    1000 = perfectly natural, fluent English speech with an ideal balance of speed and clarity, matching the expected transcription.
    1 = completely unclear, robotic, or not aligned with the transcription.

    Deduct points for hesitation, unnatural pacing, robotic tone, text-to-speech artifacts, long pauses, or if the speech sounds drunk or intoxicated.

    Respond with a single integer only, no words or explanations.

    Expected transcription:
    {transcript}
    """
    response, _ = wavtext2text(wav_path, prompt)
    save_cache()
    ret = 500
    try:
        # Try to parse the integer score from the LLM response.
        ret = int(response.strip())
    except Exception:
        pass
    return ret


def agentic_voice_cloning_loop(
    gpu: int = 0,
    transcript: str = "",
    attempts: int = 5,
    wav_sample="./my_voice_sample.wav",
    txt_sample="./my_voice_sample.txt",
):
    pitch = "0"
    temperature = "0.2"
    seeds = [str(seed) for seed in range(123, 123 + attempts)]

    # Ensure cache directory exists
    os.makedirs("./cache", exist_ok=True)
    # Copy voice sample files to Higgs Audio expected location
    shutil.copy2(wav_sample, "./higgs-audio/examples/voice_prompts/my_voice_sample.wav")
    shutil.copy2(txt_sample, "./higgs-audio/examples/voice_prompts/my_voice_sample.txt")

    abs_current_dir = os.path.dirname(os.path.abspath(__file__))

    best_score = -1
    best_scores = []
    best_wav_path = None

    for s in seeds:

        hash_object = hashlib.md5((transcript + s + temperature).encode())
        hash = hash_object.hexdigest()
        cache_wav_path = f"./cache/{hash}.wav"

        if not os.path.exists(cache_wav_path):
            exec_python_script_from_venv(
                abs_current_dir,
                "./higgs-audio",
                "venv",
                "./examples/generation.py",
                "--scene_prompt",
                "scene_prompts/reading_blog.txt",
                "--transcript",
                f"{transcript}",
                "--ref_audio",
                "my_voice_sample",
                "--temperature",
                temperature,
                "--device_id",
                str(gpu),
                "--seed",
                s,
                "--out_path",
                f".{cache_wav_path}",
            )

        pitch = compute_speech_pitch(cache_wav_path, transcript)
        pitch = max(0, int(pitch))
        pitch = min(10, pitch)

        cache_wav_pitched_path = apply_speech_pitch(cache_wav_path, int(pitch))
        score = evaluate_speech_quality(cache_wav_pitched_path, transcript)
        if (score - int(pitch)) >= best_score:
            best_score = score - int(pitch)
            best_wav_path = cache_wav_pitched_path
            best_scores.append(best_score)
        if best_score >= 1000:
            break
        if len(best_scores) >= 3:
            break
    return best_wav_path


if __name__ == "__main__":
    # Example usage: change transcript and attempts as needed
    result_wav = agentic_voice_cloning_loop(
        gpu=0,
        transcript="This is a sample transcript for voice cloning.",
        attempts=5,
        wav_sample="./my_voice_sample.wav",
        txt_sample="./my_voice_sample.txt",
    )
    shutil.copy(result_wav, "./my_voice_cloned.wav")
    print("WAV path:", result_wav)
