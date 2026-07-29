import asyncio
import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile

TOKEN = "8907817588:AAGJYOr-iO1rA3gKX_73YHquvgaH7gnBPsU"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Максимальный размер файла для скачивания через Bot API (20 МБ)
MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024


def compress_and_convert_to_circle(input_path: str, output_path: str) -> bool:
    """
    Сжимает видео, обрезает до первых 60 секунд и делает из него круглый формат 540x540.
    """
    command = [
        "ffmpeg",
        "-y",
        "-ss", "0",  # Старт с 0 секунды
        "-t", "60",  # Ограничение по времени 60 сек
        "-i", input_path,
        # Кадрируем в квадрат по меньше стороне и сжимаем до 540x540
        "-vf", r"crop=min(iw\,ih):min(iw\,ih),scale=540:540",
        "-c:v", "libx264",
        "-crf", "30",  # Сжатие качества (30 дает хороший баланс размера и качества)
        "-preset", "ultrafast",  # Максимально быстрая обработка
        "-b:v", "750k",  # Ограничение битрейта видео, чтобы файл гарантированно весил мало
        "-maxrate", "1000k",
        "-bufsize", "1500k",
        "-c:a", "aac",  # Перекодирование аудио в легкий формат
        "-b:a", "64k",
        "-strict", "experimental",
        output_path,
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        logging.error(f"Ошибка FFmpeg при сжатии: {e}")
        return False


@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "Привет! Отправь мне абсолютно любое видео, "
        "и я тебе сделаю кружок."
    )


@dp.message(F.video | F.document)
async def handle_video(message: Message):
    # Если отправлен документ — проверяем, что это видео (по MIME или расширению)
    if message.document:
        mime = message.document.mime_type or ""
        file_name = message.document.file_name or ""
        is_video_ext = file_name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.3gp'))

        if not ("video" in mime or is_video_ext):
            await message.answer("⚠️ Отправь, пожалуйста, видеофайл (MP4, MOV, AVI и т.д.).")
            return

    # Проверка размера на ограничение скачивания Telegram (20 МБ)
    file_size = message.video.file_size if message.video else message.document.file_size
    if file_size and file_size > MAX_DOWNLOAD_SIZE:
        await message.answer(
            "⚠️ Файл превышает 20 МБ!\n"
            "Сервера Telegram не позволяют ботам скачивать файлы больше 20 МБ. "
            "Пожалуйста, отправь видео меньшего размера, либо 720p, либо 480p."
        )
        return

    status_msg = await message.answer("Пошла возня...")

    input_path = f"input_{message.from_user.id}.mp4"
    output_path = f"circle_{message.from_user.id}.mp4"

    try:
        file_id = message.video.file_id if message.video else message.document.file_id

        # Скачиваем оригинальный файл
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, input_path)

        await status_msg.edit_text("Уже на подходе...")

        # Запускаем оптимизированный FFmpeg в отдельном потоке
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(
            None, compress_and_convert_to_circle, input_path, output_path
        )

        if success and os.path.exists(output_path):
            await status_msg.edit_text("Оп оп щас...")
            video_note = FSInputFile(output_path)
            await message.answer_video_note(video_note)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Ошибка при конвертации видео. Убедитесь, что файл не повреждён.")

    except Exception as e:
        logging.error(f"Ошибка в процессе: {e}")
        await status_msg.edit_text("❌ Не удалось обработать файл. \nПопробуй отправить видео не ровно на 1 минуту,\nа на 58-59 секунд.")

    finally:
        # Чистим временные файлы
        for path in (input_path, output_path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен и готов сжимать видео!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())