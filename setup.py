from setuptools import setup, find_packages

setup(
    name="telegram-ai-scraper",
    version="0.2.0",
    description="Telegram channel scraper with Whisper transcription and AI-ready export",
    author="cryptoyasenka",
    url="https://github.com/cryptoyasenka/telegram-ai-scraper",
    py_modules=["cli", "config", "db", "scraper", "transcriber", "exporter", "links"],
    packages=find_packages(include=["web", "web.*"]),
    package_data={"web": ["templates/*.html", "static/*.css"]},
    python_requires=">=3.11",
    install_requires=[
        "telethon>=1.40.0",
        "faster-whisper>=1.1.1",
        "ffmpeg-python>=0.2.0",
        "click>=8.1.0",
        "aiosqlite>=0.20.0",
        "rich>=14.0.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
        "jinja2>=3.1.0",
        "python-multipart>=0.0.12",
    ],
    entry_points={
        "console_scripts": [
            "tgp=cli:cli",
        ],
    },
)
