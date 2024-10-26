from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip
from app.bot_instance import bot
from PIL import Image, ImageDraw
import numpy as np
import io
import os

async def download_file(file_id, file_name):
    file = await bot.get_file(file_id)
    file_path = f"./temp/{file_name}"
    await bot.download_file(file.file_path, file_path)

    return file_path

async def create_rotating_media_video(media_path, media_type, audio_path, timecodes=None):
    fps = 24
    circle_size = 360  # Целевой размер круга для телеграмм-кружочка

    # Создаём круглую маску
    def make_circle_mask(size):
        mask_img = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask_img)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        return np.array(mask_img) / 255

    # Загружаем аудиоклип и обрезаем по тайм-кодам
    audio_clip = AudioFileClip(audio_path)
    if timecodes:
        start_time = timecodes.get('start', 0)
        end_time = timecodes.get('end', audio_clip.duration)
        if 0 <= start_time < end_time <= audio_clip.duration:
            if end_time-start_time>60:
                audio_clip = audio_clip.subclip(start_time, start_time+60)
            else:
                audio_clip = audio_clip.subclip(start_time, end_time)
        else:
            return  # Некорректные тайм-коды
    else:
        audio_clip = audio_clip.subclip(0,60)

    video_duration = audio_clip.duration

    if media_type == 'photo':
        # Открываем и обрезаем изображение под квадрат
        img = Image.open(media_path).convert("RGB")
        img_size = min(img.size)
        img = img.crop((0, 0, img_size, img_size))
        img = img.resize((circle_size, circle_size), Image.LANCZOS)  # Масштабируем под круг
        mask = make_circle_mask((circle_size, circle_size))

        # Создаем базовый клип из изображения
        base_image_clip = ImageClip(np.array(img)).set_duration(video_duration)

        # Функция для поворота и наложения маски
        def rotate_and_mask_frame(get_frame, t):
            angle = -360 * (t / video_duration)  # Плавное вращение
            rotated_img = img.rotate(float(angle), resample=Image.BICUBIC)
            rotated_img_array = np.array(rotated_img)
            return (rotated_img_array * mask[..., np.newaxis]).astype(np.uint8)

        rotating_clip = base_image_clip.fl(rotate_and_mask_frame, apply_to='mask')

        # Применяем маску и создаем финальное видео
        output_video = rotating_clip.set_audio(audio_clip)
    
    elif media_type in ['video', 'video_note']:
        # Обрезаем или повторяем видео для совпадения с длиной аудио
        video_clip = VideoFileClip(media_path)
        if audio_clip.duration > video_clip.duration:
            repeat_count = int(np.ceil(audio_clip.duration / video_clip.duration))
            video_clip = concatenate_videoclips([video_clip] * repeat_count).subclip(0, audio_clip.duration)
        elif audio_clip.duration < video_clip.duration:
            video_clip = video_clip.subclip(0, audio_clip.duration)

        # Масштабируем и создаем маску
        min_size = min(video_clip.w, video_clip.h)
        video_clip = video_clip.crop(x_center=video_clip.w / 2, y_center=video_clip.h / 2, width=min_size, height=min_size)
        video_clip = video_clip.resize((circle_size, circle_size))
        mask = make_circle_mask((circle_size, circle_size))

        # Функция для поворота и маскирования
        def process_frame(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame).convert("RGB")
            angle = -360 * (t / video_clip.duration)
            img_rotated = img.rotate(float(angle), resample=Image.BICUBIC)
            masked_frame = (np.array(img_rotated) * mask[..., np.newaxis]).astype(np.uint8)
            return convert_to_jpeg(masked_frame)

        rotating_clip = video_clip.fl(process_frame, apply_to='mask')
        output_video = rotating_clip.set_audio(audio_clip)

    # Сохраняем видео с корректным цветовым пространством для Telegram
    video_path = f"./temp/output_{os.path.basename(media_path)}.mp4"
    output_video.write_videofile(video_path, fps=fps, codec='libx264', ffmpeg_params=["-pix_fmt", "yuv420p"])

    return video_path

def convert_to_jpeg(masked_frame):
    if masked_frame.dtype != np.uint8:
        masked_frame = (masked_frame * 255).astype(np.uint8)

    if masked_frame.ndim == 3 and masked_frame.shape[2] == 4:
        masked_frame = masked_frame[:, :, :3]  # Убираем альфа-канал, если он есть

    image = Image.fromarray(masked_frame)

    img_buffered = io.BytesIO()
    image.save(img_buffered, format="JPEG", quality=70)  # Увеличиваем качество для четкости
    img_buffered.seek(0)

    return np.array(Image.open(img_buffered))
