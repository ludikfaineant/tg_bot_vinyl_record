import os
import subprocess
from typing import Dict, Optional
from aiogram import Bot


async def download_file(bot: Bot, file_id: str, file_name: str) -> str:
    file = await bot.get_file(file_id)
    file_path = f"./temp/{file_name}"
    await bot.download_file(file.file_path, file_path)  # type: ignore
    return file_path


async def create_rotating_media_video(
    media_path: str,
    media_type: str,
    audio_path: str,
    timecodes: Optional[Dict[str, int]] = None,
) -> str:
    circle_size = 360  # Размер круга для телеграм-кружочка
    output_path = f"./temp/output_{os.path.basename(media_path)}.mp4"
    fps = 25

    # Обрезка аудиофайла с использованием ffmpeg
    start_time = timecodes.get("start", 0) if timecodes else 0
    end_time = min(
        timecodes.get("end", float("inf")) if timecodes else float("inf"),
        start_time + 60,  # Максимум 60 секунд
    )

    # Создаем временный обрезанный аудиофайл с помощью ffmpeg
    audio_temp_path = f"./temp/audio_temp_{os.path.basename(audio_path)}.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            audio_path,
            "-ss",
            str(start_time),
            "-to",
            str(end_time),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "4",  # Используем mp3 с хорошим качеством
            audio_temp_path,
        ],
        check=True,
    )

    # Проверяем длительность медиафайла и задаем финальную длительность
    media_duration = None
    if media_type in ["video", "video_note"]:
        media_duration = float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    media_path,
                ]
            ).strip()
        )
    video_duration = (
        min(end_time - start_time, media_duration)
        if media_duration
        else end_time - start_time
    )

    # Подготовка команды FFmpeg с удалением оригинального аудио
    common_ffmpeg_args = [
        "ffmpeg",
        "-i",
        media_path,
        "-i",
        audio_temp_path,
        "-map",
        "0:v",
        "-map",
        "1:a",  # Используем видео из исходного файла и аудио из обрезанного файла
        "-vf",
        f"crop=min(in_w\\,in_h):min(in_w\\,in_h),scale={circle_size}:{circle_size},"
        f"rotate=t*PI/10:c=black:ow=rotw(0):oh=roth(0),format=yuv420p",
        "-t",
        str(video_duration),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-r",
        str(fps),
        "-shortest",
        output_path,
    ]

    # Если тип - фото, зацикливаем изображение
    if media_type == "photo":
        common_ffmpeg_args.insert(1, "-loop")
        common_ffmpeg_args.insert(2, "1")

    # Запуск команды FFmpeg
    subprocess.run(common_ffmpeg_args, check=True)

    # Удаляем временный аудиофайл
    os.remove(audio_temp_path)

    return output_path
