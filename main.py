import asyncio
import logging
import static_ffmpeg
static_ffmpeg.add_paths()
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
    Конвертация в квадратный кружок Telegram без синтаксических ошибок FFmpeg.
    """
    command = [
        "ffmpeg",
        "-y",
        "-ss", "0",
        "-t", "60",
        "-i", input_path,
        # Задаем обрезку явными переменными w и h, чтобы FFmpeg не путал двоеточия
        "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=540:540,format=yuv420p",
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        output_path,
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ ОШИБКА FFMPEG STDERR:\n{e.stderr}")
        return False
    except Exception as e:
        logging.error(f"❌ Общая ошибка: {e}")
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