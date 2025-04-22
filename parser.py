import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime

DB_PATH = "articles.db"
TB_ARTICLES = "articles"
TB_AUTHORS = "authors"

TURKISH_MONTHS = {
    "Ocak": "01", "Şubat": "02", "Mart": "03", "Nisan": "04",
    "Mayıs": "05", "Haziran": "06", "Temmuz": "07", "Ağustos": "08",
    "Eylül": "09", "Ekim": "10", "Kasım": "11", "Aralık": "12"
}

def convert_turkish_date(turkish_date):
    day, month, year = turkish_date.split()
    return f"{year}-{TURKISH_MONTHS[month]}-{day.zfill(2)}"

def add_article(article):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            sql = f'''INSERT INTO {TB_ARTICLES}(author, date, title, desc, link) VALUES (?, ?, ?, ?, ?)'''
            cur = conn.cursor()
            cur.execute(sql, article)
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        if str(e) == "UNIQUE constraint failed: articles.link":
            return None
        print(f"Database error: {e}")
        return None

def fetch_with_parser(url, parser_type):
    session = requests.Session()
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        if parser_type == "nefes":
            author = soup.find('div', class_='author-name')
            author_name = author.get_text(strip=True) if author else "Unknown"
            articles = soup.find_all('article', class_='article-card')

            for article in articles:
                link_tag = article.find('a', href=True)
                title = link_tag.get("title", "No Title") if link_tag else "No Title"
                link = link_tag.get("href", "#") if link_tag else "#"
                date_tag = article.find('time')
                date = convert_turkish_date(date_tag.get_text(strip=True)) if date_tag else "1970-01-01"

                entry = (author_name, date, title, "", link)
                if add_article(entry):
                    print(f'Added article {author_name}')

        elif parser_type == "ekonomim":
            author = soup.find('h2', class_='name')
            author_name = author.get_text(strip=True) if author else "Unknown"
            articles = soup.find_all('div', class_='col-12 col-sm-6 item')

            for article in articles:
                link_tag = article.find('a', href=True)
                title = link_tag.get("title", "No Title") if link_tag else "No Title"
                link = link_tag.get("href", "#") if link_tag else "#"
                date_tag = article.find('span', class_='date')
                date = convert_turkish_date(date_tag.get_text(strip=True)) if date_tag else "1970-01-01"

                entry = (author_name, date, title, "", link)
                if add_article(entry):
                    print(f'Added article {author_name}')

        elif parser_type == "cumhuriyet":
            author = soup.find('div', class_='adi')
            author_name = author.get_text(strip=True) if author else "Unknown"
            articles = soup.find('ul', class_='yazilar').find_all('li')
            baseurl = "https://www.cumhuriyet.com.tr"

            for article in articles:
                link_tag = article.find('a', href=True)
                link = baseurl + link_tag.get("href", "#") if link_tag else "#"
                title = article.find("span", class_="baslik").get_text(strip=True) if link_tag else "No Title"
                date_parts = article.find('span', class_='tarih').get_text(strip=True).split()[:3]
                date = convert_turkish_date(" ".join(date_parts))

                entry = (author_name, date, title, "", link)
                if add_article(entry):
                    print(f'Added article {author_name}')

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def fetch_authors(parser):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT link, author FROM {TB_AUTHORS} WHERE parser = ?", (parser,))
            for url, author in cur.fetchall():
                print(f"Fetching articles for {author} on {parser}...")
                fetch_with_parser(url, parser)
    except sqlite3.OperationalError as e:
        print(f"DB error: {e}")

if __name__ == "__main__":
    for source in ["nefes", "ekonomim", "cumhuriyet"]:
        fetch_authors(source)
