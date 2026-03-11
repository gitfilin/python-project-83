from urllib.parse import urlparse


def normalize_url(url):
    """Приводим URL к единому виду"""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = 'https://' + url
        parsed = urlparse(url)
    return parsed.netloc or parsed.path
