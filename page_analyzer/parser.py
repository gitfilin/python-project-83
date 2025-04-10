from bs4 import BeautifulSoup


def get_data(content: str) -> dict:
    soup = BeautifulSoup(content, 'lxml')
    data = {}
    title = soup.title.text
    data['title'] = title[0:69] if title else None
    h1 = soup.h1.text
    data['h1'] = h1[0:64] if h1 else None
    data['description'] = None
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta:
        data['description'] = meta.get('content', None)[0:299]

    return data
