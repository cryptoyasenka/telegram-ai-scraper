import asyncio
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm, Prompt

import config
import db
import scraper
import transcriber
import exporter

console = Console()


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _get_client():
    api_id = Prompt.ask("API ID")
    api_hash = Prompt.ask("API Hash")

    client = await scraper.create_client(int(api_id), api_hash)

    state_file = config.DATA_DIR / "api_credentials.json"
    import json
    state_file.write_text(json.dumps({"api_id": int(api_id), "api_hash": api_hash}))

    await scraper.authenticate(client)
    return client


async def _load_client():
    import json
    state_file = config.DATA_DIR / "api_credentials.json"
    if not state_file.exists():
        console.print("[red]Сначала выполните: tgp auth[/red]")
        sys.exit(1)

    creds = json.loads(state_file.read_text())
    client = await scraper.create_client(creds["api_id"], creds["api_hash"])

    if not await client.is_user_authorized():
        console.print("[red]Сессия истекла. Выполните: tgp auth[/red]")
        sys.exit(1)

    return client


@click.group()
def cli():
    """TG Parser — парсер Telegram-каналов для AI"""
    db.init_db()


@cli.command()
def auth():
    """Авторизация в Telegram API"""
    console.print("[bold]Авторизация в Telegram[/bold]")
    console.print("Получите API ключи на https://my.telegram.org\n")

    async def _auth():
        client = await _get_client()
        console.print("[green]Авторизация успешна![/green]")
        await client.disconnect()

    run_async(_auth())


@cli.command()
@click.argument("channel")
def add(channel):
    """Добавить канал: tgp add @username или tgp add https://t.me/username"""
    async def _add():
        client = await _load_client()
        try:
            info = await scraper.resolve_channel(client, channel)
            if not info:
                console.print(f"[red]Канал '{channel}' не найден[/red]")
                return

            db.add_channel(info["id"], info["username"], info["title"])
            console.print(f"[green]Добавлен: {info['title']} (@{info['username']})[/green]")
        finally:
            await client.disconnect()

    run_async(_add())


@cli.command()
@click.argument("channel", required=False)
def scrape(channel):
    """Скрейпинг каналов. Без аргумента — все каналы."""
    async def _scrape():
        client = await _load_client()
        try:
            if channel:
                ch = db.get_channel_by_username(channel.lstrip("@"))
                if not ch:
                    console.print(f"[red]Канал '{channel}' не найден в БД. Сначала: tgp add {channel}[/red]")
                    return
                channels = [ch]
            else:
                channels = db.get_all_channels()
                if not channels:
                    console.print("[red]Нет каналов. Добавьте: tgp add @username[/red]")
                    return

            for ch in channels:
                console.print(f"\n[bold]Скрейпинг: {ch['title']}[/bold]")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("{task.completed}/{task.total}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Сообщения", total=0)

                    def on_progress(current, total):
                        progress.update(task, completed=current, total=total)

                    count = await scraper.scrape_channel(
                        client, ch["id"], offset_id=ch["last_message_id"],
                        progress_callback=on_progress,
                    )

                console.print(f"[green]Готово: {count} сообщений[/green]")

                pending = transcriber.count_pending(ch["id"])
                if pending > 0:
                    if pending > config.TRANSCRIPTION_WARN_THRESHOLD:
                        console.print(
                            f"\n[yellow]Найдено {pending} голосовых/видео для транскрипции.[/yellow]"
                        )
                        console.print("[yellow]На CPU это может занять несколько часов.[/yellow]")
                        choice = Prompt.ask(
                            "Что делать?",
                            choices=["all", "test10", "skip"],
                            default="skip",
                        )
                        if choice == "skip":
                            console.print("Пропущено. Запустите позже: tgp transcribe")
                        elif choice == "test10":
                            _do_transcribe(ch["id"], limit=10)
                        else:
                            _do_transcribe(ch["id"])
                    else:
                        if Confirm.ask(f"Транскрибировать {pending} файлов?"):
                            _do_transcribe(ch["id"])
        finally:
            await client.disconnect()

    run_async(_scrape())


@cli.command()
@click.argument("channel", required=False)
def update(channel):
    """Подтянуть новые посты из каналов"""
    scrape.callback(channel)


@cli.command()
@click.argument("channel", required=False)
@click.option("--limit", "-l", type=int, help="Лимит файлов")
def transcribe(channel, limit):
    """Транскрибировать голосовые и видео"""
    if channel:
        ch = db.get_channel_by_username(channel.lstrip("@"))
        if not ch:
            console.print(f"[red]Канал не найден: {channel}[/red]")
            return
        channels = [ch]
    else:
        channels = db.get_all_channels()

    for ch in channels:
        pending = transcriber.count_pending(ch["id"])
        if pending == 0:
            console.print(f"[dim]{ch['title']}: нечего транскрибировать[/dim]")
            continue

        if pending > config.TRANSCRIPTION_WARN_THRESHOLD and not limit:
            console.print(
                f"\n[yellow]{ch['title']}: {pending} файлов для транскрипции (CPU, может быть долго)[/yellow]"
            )
            choice = Prompt.ask("Что делать?", choices=["all", "test10", "skip"], default="skip")
            if choice == "skip":
                continue
            elif choice == "test10":
                _do_transcribe(ch["id"], limit=10)
            else:
                _do_transcribe(ch["id"])
        else:
            _do_transcribe(ch["id"], limit=limit)


def _do_transcribe(channel_id: str, limit=None):
    ch = db.get_channel(channel_id)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Транскрипция {ch['title']}", total=0)

        def on_progress(current, total):
            progress.update(task, completed=current, total=total)

        done = transcriber.transcribe_channel(channel_id, limit=limit, progress_callback=on_progress)

    console.print(f"[green]Транскрибировано: {done} файлов[/green]")


@cli.command(name="export")
@click.argument("channel", required=False)
@click.option("--links-only", is_flag=True, help="Только посты со ссылками")
@click.option("--min-length", type=int, default=20, help="Мин. длина текста (фильтр шитпостов)")
@click.option("--min-views", type=int, help="Мин. просмотры")
@click.option("--search", "-s", help="Поиск по тексту")
@click.option("--merge", is_flag=True, help="Все каналы в один файл")
@click.option("--no-filter", is_flag=True, help="Экспорт без фильтров")
def export_cmd(channel, links_only, min_length, min_views, search, merge, no_filter):
    """Экспорт каналов в MD и JSON для AI"""
    if no_filter:
        min_length = 0

    kwargs = {
        "min_length": min_length,
        "has_links": links_only,
        "min_views": min_views,
        "search": search,
    }

    if merge:
        path = exporter.save_merged_export(**kwargs)
        if path:
            console.print(f"[green]Merged export: {path}[/green]")
        else:
            console.print("[red]Нет каналов для экспорта[/red]")
        return

    if channel:
        ch = db.get_channel_by_username(channel.lstrip("@"))
        if not ch:
            console.print(f"[red]Канал не найден: {channel}[/red]")
            return
        channels = [ch]
    else:
        channels = db.get_all_channels()

    for ch in channels:
        try:
            md_path, json_path = exporter.save_export(ch["id"], **kwargs)
            console.print(f"[green]{ch['title']}:[/green]")
            console.print(f"  MD:   {md_path}")
            console.print(f"  JSON: {json_path}")
        except Exception as e:
            console.print(f"[red]{ch['title']}: ошибка — {e}[/red]")


@cli.command()
@click.argument("query")
@click.option("--links", is_flag=True, help="Искать по ссылкам")
def search(query, links):
    """Поиск по тексту или ссылкам"""
    if links:
        results = db.search_links(query)
        if not results:
            console.print("[dim]Ничего не найдено[/dim]")
            return

        table = Table(title=f"Ссылки: '{query}'")
        table.add_column("Дата", width=10)
        table.add_column("Канал", width=20)
        table.add_column("URL", width=40)
        table.add_column("Контекст", width=50)

        for r in results:
            table.add_row(
                r.get("date", "")[:10],
                r.get("channel_title", ""),
                r.get("url", ""),
                (r.get("context_text", "") or "")[:50],
            )
        console.print(table)
    else:
        results = db.search_all(query)
        if not results:
            console.print("[dim]Ничего не найдено[/dim]")
            return

        table = Table(title=f"Поиск: '{query}'")
        table.add_column("Дата", width=10)
        table.add_column("Канал", width=20)
        table.add_column("Текст", width=80)

        for r in results:
            text = r.get("text", "") or r.get("voice_transcript", "") or ""
            table.add_row(
                r.get("date", "")[:10],
                r.get("channel_title", ""),
                text[:80],
            )
        console.print(table)


@cli.command()
def status():
    """Статистика по всем каналам"""
    stats = db.get_stats()
    channels = db.get_all_channels()

    table = Table(title="TG Parser — статус")
    table.add_column("Канал", width=25)
    table.add_column("Постов", justify="right", width=10)
    table.add_column("Последний скрейп", width=20)
    table.add_column("Last ID", justify="right", width=10)

    for ch in channels:
        table.add_row(
            f"{ch['title']} (@{ch['username']})",
            str(ch["total_posts"]),
            ch.get("last_scraped", "—") or "—",
            str(ch["last_message_id"]),
        )

    console.print(table)
    console.print(f"\nВсего: {stats['channels']} каналов, {stats['messages']} сообщений, "
                  f"{stats['links']} ссылок")
    console.print(f"Голосовых/видео: {stats['voice_video']}, транскрибировано: {stats['transcribed']}")


@cli.command()
def channels():
    """Список каналов из Telegram (для добавления)"""
    async def _list():
        client = await _load_client()
        try:
            chs = await scraper.list_user_channels(client)
            table = Table(title="Ваши каналы и группы")
            table.add_column("#", width=4)
            table.add_column("Название", width=30)
            table.add_column("Username", width=20)
            table.add_column("Тип", width=10)

            for i, ch in enumerate(chs, 1):
                table.add_row(str(i), ch["title"], f"@{ch['username']}" if ch["username"] else "—", ch["type"])

            console.print(table)
        finally:
            await client.disconnect()

    run_async(_list())


if __name__ == "__main__":
    cli()
