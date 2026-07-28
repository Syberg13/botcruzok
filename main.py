import asyncio
import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile

# Токен вашего бота
TOKEN = "8907817588:AAGJYOr-iO1rA3gKX_73YHquvgaH7gnBPsU"

bot = Bot(token=TOKEN)
dp = Dispatcher()


def convert_to_video_note(input_path: str, output_path: str) -> bool:
    """Обкадрирует видео по центру в квадрат (540x540) и конвертирует для кружка."""
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vf",
        r"crop=min(iw\,ih):min(iw\,ih),scale=540:540",  # Добавлена r для raw-строки
        "-t",
        "60",
        "-c:v",
        "libx264",
        "-crf",
        "26",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-strict",
        "experimental",
        output_path,
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Ошибка при обработке FFmpeg: {e}")
        return False


# Использование правильного фильтра CommandStart()
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "Привет! Отправь мне видео в формате, и я сделаю из него кружок!"
    )


@dp.message(F.video | F.document)
async def handle_video(message: Message):
    # Проверяем, что если отправлен документ, то это MP4/видео
    if message.document and not (
        message.document.mime_type and "video" in message.document.mime_type
    ):
        await message.answer("Пожалуйста, отправь видеофайлы формата MP4.")
        return

    status_msg = await message.answer("Пошла возня...")

    input_path = f"input_{message.from_user.id}.mp4"
    output_path = f"circle_{message.from_user.id}.mp4"

    try:
        file_id = message.video.file_id if message.video else message.document.file_id

        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, input_path)

        await status_msg.edit_text("Преобразую в кружок...")

        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(
            None, convert_to_video_note, input_path, output_path
        )

        if success and os.path.exists(output_path):
            await status_msg.edit_text("Отправляю...")
            video_note = FSInputFile(output_path)
            await message.answer_video_note(video_note)
            await status_msg.delete()
        else:
            await status_msg.edit_text(
                "Не удалось обработать видео. Проверьте формат видео."
            )

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text("Произошла ошибка при обработке видео.")

    finally:
        for path in (input_path, output_path):
            if os.path.exists(path):
                os.remove(path)


async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())