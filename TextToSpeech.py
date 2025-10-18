import asyncio
import os
from pathlib import Path
from openai import AsyncOpenAI

# --- Конфиг -----------------------------------------------------------------------------------------------------------

# Используйте переменную окружения OPENAI_API_KEY в реальных проектах и CI/CD:
apiKey = ""
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", apiKey))

textsDir = Path("texts").resolve()  # Directory with input .txt/.md files.
outputDir = Path("audio").resolve()  # Directory for rendered audio files.
outputDir.mkdir(parents=True, exist_ok=True)

# Паспорт голоса спикера (инструкции для стиля голоса):
passport = (
    "Русский текст говори только по-русски, другой текст произноси на языке оригинала с нужным акцентом; "
    "академичный тон опытного преподавателя. "
    "В конце предложения — лёгкая каденция вниз, мягкое подчёркивание ключевого термина. "
    "Артикуляция чёткая; темп чтения энергично и быстрее на 30-40%; числа, фамилии и иностранные термины — медленнее на 5–10%. "
    "Делай короткие паузы перед определениями. Не добавляй эмоций, кроме лёгкой доброжелательности."
    "Чёткая дикция; фамилии и термины произносить медленнее. Даты произносить полным числом, а не по две цифры. "
    "Соблюдай орфоэпию: Евкли́д, Архиме́д, Ферма́, Пуа́нкаре́ и т.п."
)

# Голоса:
# ballad — мужской, средний темп, выразительный, слегка торжественный: повествовательный/narrative вайб; удобно для озвучки статей/подкастов.
# marin — женский, молодой, выразительные акценты, новое поколение, максимально «человечная» речь, отличная дикция, гибко подчиняется инструкциям; рекомендован для ассистентов, но может быть доступен только в Realtime.
# coral — женский, выразительный, с придыханием, вбуривающий голос, «яркий» стиль; подходит для промо-реплик, туториалов, «энергичных» ассистентов.
# verse — мужской, чёткий, пробивной, выразительный «читающий» стиль; заходит на презентациях и дикторских подводках.
# sage — женский, достаточно медленный, торжественный, спокойный/уравновешенный тон; хорошо для саппорта, справочных подсказок и корпоративных сценариев.
# alloy — женский, универсальный «дефолт», сбалансированный, хорошо держит деловой и нейтральный тон. Часто используется в примерах доков.
# echo — мужской, средний тем, средний возраст, чёткая дикция и нейтральная подача; удобно для цифр/инструкций/IVR. (Исторически один из ранних Realtime-голосов.)
# shimmer — женский, выразительный, средних лет, более «живой» пресет, подходит для дружественных ассистентов и маркетинговых текстов.
# ash — мужской, очень медленный, пожилого возраста, новая волна Realtime-голосов (поколение 2024-10) с более выразимой интонацией. Хорош для диалогов, где нужна эмоция.
voices = ["ballad", "marin"]  # ["ballad", "marin", "coral", "verse", "sage", "alloy", "echo", "shimmer", "ash"]
fileFormat = "flac"  # Поддерживаются: "wav", "mp3", "flac", "aac", "opus", "pcm".

# Лимиты для конкурентных задач по синтезу речи, чтобы избежать рейт-лимитов API:
CONCURRENCY = 5
semaphore = asyncio.Semaphore(CONCURRENCY)


async def Synth(textFile: Path, voice: str, fmt: str = fileFormat):
    """Синтез аудио файла из одного текстового файла с заданным голосом диктора."""
    async with semaphore:
        with textFile.open("r", encoding="utf-8") as f:
            text = f.read().strip()

        if not text:
            print(f"Пропускаем пустой файл: {textFile.name}")

            return

        baseName = textFile.stem
        outPath = outputDir / f"{baseName}_{voice}.{fmt}"

        try:
            async with client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice=voice,
                input=text,
                instructions=passport,
                response_format=fmt,
            ) as resp:
                await resp.stream_to_file(str(outPath))

            print(f"Сгенерировано: {outPath}")

        except Exception as e:
            print(f"Ошибка в {textFile.name} [{voice}]: {e}")


def CollectInputFiles(root: Path) -> list[Path]:
    """Ищем .txt и .md файлы, сортируем их по имени."""
    if not root.exists():
        raise FileNotFoundError(f"Директория не существует: {root}")

    files = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".md"}]

    return sorted(files, key=lambda p: p.name)


async def Main() -> None:
    files = CollectInputFiles(textsDir)

    if not files:
        print(f"Нет .txt или .md файлов в директории: {textsDir}")

        return

    tasks = []
    for f in files:
        for v in voices:
            tasks.append(Synth(f, v, fileFormat))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(Main())
