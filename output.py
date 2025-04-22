import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from feedgen.feed import FeedGenerator
import pytz

DB_PATH = "./rss/articles.db"
TB_ARTICLES = "articles"
TB_AUTHORS = "authors"
DOMAIN = "https://alperozgur.github.io/"
RSS_DIR = "rss"


def generate_rss(short_name, author, author_link, parser):
    """Generate RSS feed for a given author."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT title, link, desc, date 
                FROM {TB_ARTICLES} 
                WHERE author = ? 
                ORDER BY date ASC
            """, (author,))
            articles = cur.fetchall()

        if not articles:
            print(f"No articles for {author}")
            return

        fg = FeedGenerator()
        fg.title(author)
        fg.link(href=author_link, rel="self")
        fg.description(f"{author} tarafından yazılan tüm köşe yazıları")

        for title, url, description, date_str in articles:
            fe = fg.add_entry()
            fe.title(title)
            fe.link(href=url)
            fe.description(description)
            try:
                pub_date = datetime.strptime(date_str, "%Y-%m-%d")
                fe.pubDate(pytz.utc.localize(pub_date))
            except ValueError:
                print(f"Invalid date for article '{title}': {date_str}")

        output_path = f"{RSS_DIR}/{parser}/{short_name}.xml"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fg.rss_file(output_path)
        print(f"RSS generated: {output_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")


def fetch_authors_and_generate_feeds():
    """Fetch all authors from the DB, generate their RSS, and produce OPML."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT short, author, link, parser FROM {TB_AUTHORS}")
            authors = cur.fetchall()

        if not authors:
            print("No authors in database.")
            return

        opml = ET.Element("opml", version="2.0")
        ET.SubElement(opml, "head").append(ET.Element("title", text="Köşe Yazarları RSS Listesi"))
        body = ET.SubElement(opml, "body")

        for short, author, link, parser in authors:
            generate_rss(short, author, link, parser)
            xml_url = f"{DOMAIN}{RSS_DIR}/{parser}/{short}.xml"
            ET.SubElement(body, "outline", text=author, type="link", xmlUrl=xml_url)

        opml_path = f"{RSS_DIR}/index.opml"
        with open(opml_path, "wb") as f:
            ET.ElementTree(opml).write(f, encoding="utf-8", xml_declaration=True)
        print(f"OPML written: {opml_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")


def parse_opml(path):
    """Parse OPML and return the body element."""
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag.lower() != "opml":
        raise ValueError("Invalid OPML file")
    body = root.find("body")
    if body is None:
        raise ValueError("OPML missing body")
    return body


def opml_to_html(outlines, indent=0):
    """Convert OPML outline tags to HTML."""
    html = ""
    for outline in outlines:
        text = outline.get("text", "[No Text]")
        xml_url = outline.get("xmlUrl")
        indent_space = " " * indent
        if xml_url:
            html += f"{indent_space}<li class='list-group-item bg-white shadow-sm p-2 opml-item'><a href='{xml_url}' class='text-decoration-none text-primary'>{text}</a></li>\n"
        else:
            html += f"{indent_space}<li class='list-group-item bg-white shadow-sm p-2 opml-item'>{text}</li>\n"
        children = outline.findall("outline")
        if children:
            html += f"{indent_space}<ul class='list-group ms-3'>\n"
            html += opml_to_html(children, indent + 2)
            html += f"{indent_space}</ul>\n"
    return html


def generate_html(opml_path, html_path):
    """Generate an HTML file from an OPML outline."""
    body = parse_opml(opml_path)
    html_content = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <title>OPML Viewer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f0f8ff; color: #002147; }}
        .navbar {{ background-color: #002147; }}
        .navbar-brand, .nav-link {{ color: #ffffff !important; }}
        .container {{ margin-top: 30px; }}
        .opml-container {{ background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
        .footer {{ background-color: #002147; color: white; text-align: center; padding: 20px 0; margin-top: 30px; }}
        .btn-custom {{ background-color: #002147; color: white; }}
        .btn-custom:hover {{ background-color: #003366; color: white; }}
        .opml-item:hover {{ background-color: #dfefff; transition: background-color 0.3s ease-in-out; }}
    </style>
    <script>
        function searchOPML() {{
            let input = document.getElementById('searchInput').value.toLowerCase();
            let items = document.getElementsByClassName('opml-item');
            for (let item of items) {{
                let text = item.textContent.toLowerCase();
                item.style.display = text.includes(input) ? '' : 'none';
            }}
        }}
    </script>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark">
    <div class="container"><a class="navbar-brand" href="#">OPML Viewer</a></div>
</nav>
<div class="container">
    <div class="opml-container">
        <div class="mb-3">
            <input type="text" id="searchInput" class="form-control" placeholder="Search..." onkeyup="searchOPML()">
        </div>
        <ul class="list-group">
            {opml_to_html(body.findall('outline'))}
        </ul>
    </div>
</div>
<footer class="footer">
    <p>&copy; 2025 OPML Viewer. All rights reserved.</p>
</footer>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML created: {html_path}")


if __name__ == "__main__":
    fetch_authors_and_generate_feeds()
    generate_html(f"{RSS_DIR}/index.opml", f"{RSS_DIR}/index.html")
