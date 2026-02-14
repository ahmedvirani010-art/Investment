"""
Simple RSS Parser
Alternative to feedparser using built-in libraries
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
import re


class SimpleFeedEntry:
    """Simple feed entry compatible with feedparser"""
    def __init__(self, title: str, link: str, description: str, published: Optional[str] = None):
        self.title = title
        self.link = link
        self.summary = description
        self.description = description

        # Parse published date
        if published:
            self.published_parsed = self._parse_date(published)
            self.updated_parsed = self.published_parsed
        else:
            self.published_parsed = None
            self.updated_parsed = None

    def _parse_date(self, date_str: str) -> tuple:
        """Parse RFC822 or ISO date to time tuple"""
        try:
            # Try RFC822 format (common in RSS)
            from email.utils import parsedate
            parsed = parsedate(date_str)
            if parsed:
                return parsed
        except:
            pass

        try:
            # Try ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.timetuple()[:6]
        except:
            pass

        # Return current time if parsing fails
        return datetime.now().timetuple()[:6]

    def get(self, key: str, default=None):
        """Dictionary-like get method"""
        return getattr(self, key, default)


class SimpleFeed:
    """Simple feed parser result"""
    def __init__(self, entries: List[SimpleFeedEntry]):
        self.entries = entries


def parse(url_or_content: str) -> SimpleFeed:
    """
    Parse RSS feed from URL or XML content

    Args:
        url_or_content: URL string or XML content

    Returns:
        SimpleFeed object with entries
    """
    import urllib.request

    # Fetch content if URL
    if url_or_content.startswith('http'):
        try:
            with urllib.request.urlopen(url_or_content, timeout=10) as response:
                content = response.read()
        except Exception as e:
            return SimpleFeed([])
    else:
        content = url_or_content

    # Parse XML
    try:
        root = ET.fromstring(content)
    except:
        return SimpleFeed([])

    entries = []

    # Try RSS 2.0 format
    for item in root.findall('.//item'):
        title = item.find('title')
        link = item.find('link')
        description = item.find('description')
        pubDate = item.find('pubDate')

        if title is not None and link is not None:
            entry = SimpleFeedEntry(
                title=title.text or '',
                link=link.text or '',
                description=(description.text or '') if description is not None else '',
                published=(pubDate.text or '') if pubDate is not None else None
            )
            entries.append(entry)

    # Try Atom format
    if not entries:
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for item in root.findall('.//atom:entry', ns):
            title = item.find('atom:title', ns)
            link = item.find('atom:link', ns)
            summary = item.find('atom:summary', ns)
            updated = item.find('atom:updated', ns)

            if title is not None and link is not None:
                link_href = link.get('href', '')
                entry = SimpleFeedEntry(
                    title=title.text or '',
                    link=link_href,
                    description=(summary.text or '') if summary is not None else '',
                    published=(updated.text or '') if updated is not None else None
                )
                entries.append(entry)

    return SimpleFeed(entries)
