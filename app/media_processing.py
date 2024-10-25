from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips
from app.bot_instance import bot
import os
from PIL import Image, ImageDraw
import numpy as np


async def download_file(file_id, file_name):
    file = await bot.get_file(file_id)
    file_path = f"./temp/{file_name}"
    await bot.download_file(file.file_path, file_path)
    return file_path

# Функция для создания видео из фото или вращения видео
async def create_rotating_media_video(media_path, media_type, audio_path, timecodes=None):
    fps = 24
    
    if media_type == 'photo':
        img = Image.open(media_path)
        img_size = min(img.size)
        img = img.crop((0, 0, img_size, img_size))
        img_array = np.array(img)
        mask = make_circle_mask(img.size)
        
        # Загружаем аудио файл
        audio_clip = AudioFileClip(audio_path)
        
        # Если указаны тайм-коды, обрезаем аудио
        if timecodes:
            start_time = timecodes.get('start', 0)
            end_time = timecodes.get('end', audio_clip.duration)
            if 0 <= start_time < end_time <= audio_clip.duration:
                audio_clip = audio_clip.subclip(start_time, end_time)
            else:
                return  # Некорректные тайм-коды, остановка обработки

        video_duration = audio_clip.duration

        def make_frame(t):
            """Обрабатываем каждый кадр по отдельности, применяя вращение и маску."""
            angle = -360 * (t / 25)
            rotated_img = img.rotate(angle, resample=Image.BICUBIC)
            return np.array(rotated_img) * mask[..., np.newaxis]

        # Потоковая обработка видео из кадров
        image_clip = ImageClip(img_array, duration=video_duration)
        image_clip = image_clip.set_make_frame(make_frame).set_duration(video_duration)
        video = image_clip.set_audio(audio_clip)
        
        # Запись в файл
        video_path = f"./temp/output_{os.path.basename(media_path)}.mp4"
        video.write_videofile(video_path, fps=fps, codec='libx264')

    elif media_type in ['video', 'video_note']:
        video_clip = VideoFileClip(media_path)
        audio_clip = AudioFileClip(audio_path)
        # Если указаны тайм-коды, обрезаем аудио
        if timecodes:
            start_time = timecodes.get('start', 0)
            end_time = timecodes.get('end', audio_clip.duration)
            if 0 <= start_time < end_time <= audio_clip.duration:
                audio_clip = audio_clip.subclip(start_time, end_time)
            else:
                return
        # Обрезаем или повторяем видео в зависимости от длительности аудио
        if audio_clip.duration > video_clip.duration:
            repeat_count = int(np.ceil(audio_clip.duration / video_clip.duration))
            video_clip = concatenate_videoclips([video_clip] * repeat_count).subclip(0, audio_clip.duration)
        elif audio_clip.duration < video_clip.duration:
            video_clip = video_clip.subclip(0, audio_clip.duration)

        

        min_size = min(video_clip.w, video_clip.h)
        mask_size = (min_size, min_size)  # Размер маски круга
        mask = make_circle_mask(mask_size)

        # Применение маски и вращения кадр за кадром
        def process_frame(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame)
            
            # Обрезаем кадр до квадрата
            min_side = min(img.width, img.height)
            left = (img.width - min_side) / 2
            top = (img.height - min_side) / 2
            right = (img.width + min_side) / 2
            bottom = (img.height + min_side) / 2

            img_cropped = img.crop((0, 0, min_side, min_side))
            #img_cropped = img.crop((left, top, right, bottom))
            
            # Применяем вращение и маску
            total_frames = int(video_clip.duration * fps)
            angle = -(360 / 25) * (t)
            img_rotated = img_cropped.rotate(angle, resample=Image.BICUBIC)
            return apply_circle_mask(np.array(img_rotated), mask)

        rotated_clip = video_clip.fl(process_frame)
        video = rotated_clip.set_audio(audio_clip)
        
        # Запись в файл
        video_path = f"./temp/output_{os.path.basename(media_path)}.mp4"
        video.write_videofile(video_path, fps=fps, codec='libx264')
    
    return video_path


# Функция для создания маски круга
def make_circle_mask(size):
    """Создание круговой маски для кадра."""
    mask_img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask_img)
    diameter = min(size)
    draw.ellipse((0, 0, diameter, diameter), fill=255)
    return np.array(mask_img) / 255

def apply_circle_mask(frame, mask):
    return (frame * mask[..., np.newaxis]).astype(np.uint8)
