import re
from urllib.parse import urlparse

URL_PATTERN = re.compile(
    r'https?://[^\s<>\"\'\)\]\},;]+|'
    r'(?<!\w)(?:www\.)[^\s<>\"\'\)\]\},;]+',
    re.IGNORECASE,
)


def extract_links(text: str) -> list[dict]:
    if not text:
        return []

    results = []
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:!?)")
        try:
            parsed = urlparse(url if url.startswith("http") else f"https://{url}")
            domain = parsed.netloc.lower().removeprefix("www.")
        except Exception:
            domain = ""

        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 80)
        context = text[start:end].strip()

        results.append({
            "url": url,
            "domain": domain,
            "context_text": context,
        })

    return results
