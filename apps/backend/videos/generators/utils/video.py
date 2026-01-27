"""Video processing utilities."""

import tempfile
from pathlib import Path
from urllib.request import urlopen

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from .logging import log, log_separator

LAST_CTA_DURATION = 2.0


def _download_to_temp(url: str, suffix: str) -> Path:
    """URL에서 파일을 다운로드하여 임시 파일로 저장.

    Returns:
        임시 파일 경로 (호출자가 정리 책임)
    """
    log(f"Downloading asset from: {url}")
    with urlopen(url) as response:
        data = response.read()

    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_file.write(data)
    temp_file.close()
    log(f"Downloaded to temp file: {temp_file.name} ({len(data)} bytes)")
    return Path(temp_file.name)


def concatenate_segments(
    segment_paths: list[Path],
    out_path: Path,
    last_cta_image_url: str | None = None,
    sound_effect_url: str | None = None,
) -> Path:
    """Concatenate video segments into a single video with transitions and CTA."""
    log_separator("Video concatenation started")

    log(f"Input files: {len(segment_paths)}")
    for i, p in enumerate(segment_paths, 1):
        log(f"  [{i}] {p}")

    log("Loading VideoFileClips...")
    clips = [VideoFileClip(str(p)) for p in segment_paths]

    for i, clip in enumerate(clips, 1):
        log(f"  Clip {i}: {clip.duration:.2f}s, {clip.fps} FPS, {clip.size}")

    target_fps = clips[0].fps or 24
    target_size = clips[0].size
    log(f"Target FPS: {target_fps}, Size: {target_size}")

    # Load sound effect for transitions (from S3)
    sound_effect = None
    if sound_effect_url:
        try:
            sound_effect_path = _download_to_temp(sound_effect_url, ".wav")
            log(f"Loading sound effect from S3: {sound_effect_url}")
            sound_effect = AudioFileClip(str(sound_effect_path))
        except Exception as e:
            log(f"Failed to download sound effect: {e}", "WARNING")
    else:
        log("Sound effect URL not provided", "WARNING")

    # Add last CTA image as final clip (from S3)
    cta_image_path = None
    if last_cta_image_url:
        try:
            cta_image_path = _download_to_temp(last_cta_image_url, ".png")
            log(f"Adding last CTA image from S3: {last_cta_image_url} ({LAST_CTA_DURATION}s)")
        except Exception as e:
            log(f"Failed to download CTA image: {e}", "WARNING")
    else:
        log("Last CTA image URL not provided", "WARNING")

    if cta_image_path:
        cta_clip = ImageClip(str(cta_image_path), duration=LAST_CTA_DURATION)
        cta_clip = cta_clip.resized(target_size)
        cta_clip = cta_clip.with_fps(target_fps)
        log(f"CTA clip duration: {cta_clip.duration}s")
        clips.append(cta_clip)
    else:
        log("Last CTA image not available", "WARNING")

    log("Concatenating clips...")
    result = concatenate_videoclips(clips, method="compose")
    log(f"Concatenated video duration: {result.duration:.2f}s")

    # Add sound effect at last transition (before CTA)
    if sound_effect:
        # Calculate transition time: sum of all video segments (before CTA)
        transition_time = sum(clip.duration for clip in clips[:-1])

        log(f"Sound effect at transition point: {transition_time}s")

        audio_clips = []
        if result.audio:
            audio_clips.append(result.audio)

        # Place sound effect exactly at 16s (CTA transition point)
        start_time = transition_time
        log(f"Sound effect starts at: {start_time}s")
        audio_clips.append(sound_effect.with_start(start_time))

        result = result.with_audio(CompositeAudioClip(audio_clips))

    log(f"Encoding final video... (output: {out_path})")
    result.write_videofile(
        str(out_path),
        codec="libx264",
        audio_codec="aac",
        fps=target_fps,
        preset="medium",
        threads=0,
        logger="bar",
    )

    for c in clips:
        c.close()
    if sound_effect:
        sound_effect.close()

    log(f"Final video saved: {out_path}")
    return out_path
