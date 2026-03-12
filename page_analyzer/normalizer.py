from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """Приводим URL к единому виду: схема + хост, без пути.

    Примеры:
    - https://example.com -> https://example.com
    - https://example.com/about -> https://example.com
    - example.com/about -> http://example.com
    """
    parsed = urlparse(url)

    if not parsed.scheme:
        parsed = urlparse(f'http://{url}')

    scheme = parsed.scheme
    netloc = parsed.netloc or parsed.path

    return f'{scheme}://{netloc}'
