from setuptools import setup

setup(
    name="tg-parser",
    version="0.1.0",
    py_modules=["cli", "config", "db", "scraper", "transcriber", "exporter", "links"],
    install_requires=[
        "telethon>=1.40.0",
        "faster-whisper>=1.1.1",
        "ffmpeg-python>=0.2.0",
        "click>=8.1.0",
        "aiosqlite>=0.20.0",
        "rich>=14.0.0",
    ],
    entry_points={
        "console_scripts": [
            "tgp=cli:cli",
        ],
    },
)
