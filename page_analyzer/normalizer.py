from urllib.parse import urlparse


def normalize(url: str) -> str:
    """Нормализация URL - извлечение схемы и домена.

    Args:
        url: URL для нормализации.

    Returns:
        str: Нормализованный URL (схема://домен).
    """
    data = urlparse(url)
    return f'{data.scheme}://{data.netloc}'
