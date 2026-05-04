import feedparser
import yaml
import re
import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

JST = timezone(timedelta(hours=9))
MAX_ENTRIES_PER_FEED = 10


def strip_tags(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120] + "…" if len(text) > 120 else text


def parse_date(entry):
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = datetime(*val[:6], tzinfo=timezone.utc).astimezone(JST)
                return dt.strftime("%Y/%m/%d")
            except Exception:
                pass
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = parsedate_to_datetime(val).astimezone(JST)
                return dt.strftime("%Y/%m/%d")
            except Exception:
                pass
    return ""


HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RSSFeedBot/1.0)"}


def fetch_categories(config_path):
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    categories = []
    for category in config.get("categories", []):
        feeds_data = []
        for feed_cfg in category.get("feeds", []):
            parsed = feedparser.parse(feed_cfg["url"], request_headers=HEADERS)
            print(f"  {feed_cfg['name']}: status={parsed.get('status', 'N/A')} entries={len(parsed.entries)}")
            entries = []
            for entry in parsed.entries[:MAX_ENTRIES_PER_FEED]:
                entries.append(
                    {
                        "title": entry.get("title", "（タイトルなし）"),
                        "link": entry.get("link", ""),
                        "summary": strip_tags(entry.get("summary", entry.get("description", ""))),
                        "date": parse_date(entry),
                    }
                )
            feeds_data.append({"name": feed_cfg["name"], "entries": entries})

        categories.append(
            {
                "name": category["name"],
                "color": category.get("color", "slate"),
                "feeds": feeds_data,
            }
        )

    return categories


def generate(config_path, template_dir, output_path):
    categories = fetch_categories(config_path)
    updated_at = datetime.now(JST).strftime("%Y/%m/%d %H:%M JST")

    env = Environment(loader=FileSystemLoader(template_dir))
    tmpl = env.get_template("index.html.j2")
    html = tmpl.render(categories=categories, updated_at=updated_at)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {output_path}  ({updated_at})")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate(
        config_path=os.path.join(base, "feeds.yml"),
        template_dir=os.path.join(base, "templates"),
        output_path=os.path.join(base, "output", "index.html"),
    )
