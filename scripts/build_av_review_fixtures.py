"""Build local symbolic AV review fixtures using supplied speech and existing ArcReel tools."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lib.final_cut.render_plan import OutputProfile
from lib.final_cut.subtitles import BurnedSubtitle, ass_document
from lib.infra.ffmpeg import ffmpeg_executable, local_file_input
from lib.infra.media_probe import probe_video_frame_times
from lib.subtitle_style.font import SUBTITLE_FONT_FILE
from lib.video_review.contact_sheet import build_contact_sheets
from lib.video_review.signals import detect_signals

PHRASE = "Bom dia, Ana! O pão acabou, mas o café está quentinho."


def build_fixtures(output: Path, good_audio: Path, wrong_audio: Path) -> None:
    output = output.resolve()
    good_audio, wrong_audio = good_audio.resolve(strict=True), wrong_audio.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=False)
    ffmpeg = ffmpeg_executable()
    for name, source in (("good", good_audio), ("wrong", wrong_audio)):
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                *local_file_input(source),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(output / f"{name}.wav"),
            ],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-t",
            "4.5",
            "-c:a",
            "pcm_s16le",
            str(output / "missing.wav"),
        ],
        check=True,
        capture_output=True,
    )
    (output / "expected.json").write_text(
        json.dumps([{"segment_id": "E1U01", "start": 0, "end": 4.5, "text": PHRASE}], ensure_ascii=False),
        encoding="utf-8",
    )
    fonts = output / "fonts"
    fonts.mkdir()
    shutil.copyfile(SUBTITLE_FONT_FILE, fonts / SUBTITLE_FONT_FILE.name)
    font = ImageFont.truetype(str(SUBTITLE_FONT_FILE), 40)
    for name, person, shirt, prop in (
        ("reference", "ANA", "blue", "mug"),
        ("identity-story-error", "BRUNO", "red", "box"),
    ):
        image = Image.new("RGB", (540, 960), "#dddddd")
        draw = ImageDraw.Draw(image)
        draw.text((30, 50), person, fill="black", font=font)
        draw.ellipse((180, 180, 350, 350), fill="#bd8d68")
        draw.rectangle((145, 350, 390, 700), fill=shirt)
        if prop == "mug":
            draw.rectangle((345, 470, 430, 565), fill="white", outline="black", width=4)
            draw.arc((405, 480, 460, 550), 270, 90, fill="black", width=8)
        else:
            draw.rectangle((320, 470, 455, 600), fill="#835533", outline="black", width=4)
        image.save(output / f"{name}.png")
    for name, visual, start, end in (
        ("good-av", "reference", 100_000, 4_320_000),
        ("subtitle-delayed", "reference", 5_000_000, 9_000_000),
        ("identity-story-error", "identity-story-error", 100_000, 4_320_000),
    ):
        (output / f"{name}.ass").write_text(
            ass_document([BurnedSubtitle(start, end, PHRASE)], OutputProfile(540, 960, 25)), encoding="utf-8"
        )
        (output / f"{name}-cues.json").write_text(
            json.dumps(
                [{"start_microseconds": start, "duration_microseconds": end - start, "text": PHRASE}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-loop",
                "1",
                "-i",
                f"{visual}.png",
                "-i",
                "good.wav",
                "-vf",
                f"subtitles={name}.ass:fontsdir=fonts",
                "-af",
                "apad",
                "-t",
                "9",
                "-r",
                "25",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                f"{name}.mp4",
            ],
            cwd=output,
            check=True,
            capture_output=True,
        )
        asyncio.run(collect_visual_evidence(output, name))


async def collect_visual_evidence(output: Path, name: str) -> None:
    video = output / f"{name}.mp4"
    times = await probe_video_frame_times(video)
    signals = await detect_signals(video, times)
    # This CLI owns its output directory and does not run on a server event loop.
    await asyncio.to_thread((output / f"{name}-signals.json").write_text, json.dumps(asdict(signals)), encoding="utf-8")
    sheets = await build_contact_sheets(video, unit_id=name, version=1, frames=6, frame_times=times, signals=signals)
    for number, sheet in enumerate(sheets):
        await asyncio.to_thread((output / f"{name}-sheet-{number}.jpg").write_bytes, sheet.jpeg)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--good-audio", type=Path, required=True, help=f"Local recording of: {PHRASE}")
    parser.add_argument(
        "--wrong-audio", type=Path, required=True, help="Local recording with intentionally different speech"
    )
    args = parser.parse_args()
    build_fixtures(args.output, args.good_audio, args.wrong_audio)


if __name__ == "__main__":
    main()
