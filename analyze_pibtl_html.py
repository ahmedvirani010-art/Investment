"""
Analyze PIBTL company page HTML structure to improve announcement parsing
"""

from psx_announcement_scraper import PSXAnnouncementScraper
from bs4 import BeautifulSoup
import re

def main():
    print("=" * 70)
    print("PIBTL COMPANY PAGE HTML ANALYSIS")
    print("=" * 70)
    print()

    scraper = PSXAnnouncementScraper(delay_seconds=2.0)
    company_url = f"{scraper.PSX_BASE_URL}/company/PIBTL"

    print(f"Fetching: {company_url}")
    response = scraper._fetch_url(company_url)

    if not response or response.status_code != 200:
        print("Failed to fetch page")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    print("✓ Page loaded successfully")
    print()

    # Find announcement-related sections
    print("=" * 70)
    print("SEARCHING FOR ANNOUNCEMENT SECTIONS")
    print("=" * 70)
    print()

    # Look for sections with "announcement" in class/id
    announcement_sections = soup.find_all(['div', 'section', 'table'],
                                         class_=re.compile(r'announcement|notice|corporate', re.I))

    print(f"Found {len(announcement_sections)} sections with announcement-related classes")
    print()

    for i, section in enumerate(announcement_sections, 1):
        print(f"Section {i}:")
        print(f"  Tag: {section.name}")
        print(f"  Class: {section.get('class')}")
        print(f"  ID: {section.get('id')}")
        print(f"  Text preview: {section.get_text(strip=True)[:100]}...")
        print()

    # Look for date pattern and surrounding context
    print("=" * 70)
    print("ANALYZING DATE CONTEXT")
    print("=" * 70)
    print()

    date_pattern = re.compile(r'13-02-2026')

    for elem in soup.find_all(text=date_pattern):
        print("Found date: 13-02-2026")
        print(f"  Element: {elem}")
        print(f"  Parent tag: {elem.parent.name if elem.parent else 'None'}")
        print(f"  Parent class: {elem.parent.get('class') if elem.parent else 'None'}")
        print()

        # Get parent hierarchy
        current = elem.parent
        depth = 0
        print("  Parent hierarchy:")
        while current and depth < 5:
            print(f"    Level {depth}: <{current.name}> class={current.get('class')} id={current.get('id')}")
            print(f"      Text: {current.get_text(strip=True)[:80]}...")
            current = current.parent
            depth += 1
        print()

        # Get siblings
        if elem.parent:
            print("  Siblings:")
            for sib in elem.parent.find_all(['td', 'div', 'span', 'p'], recursive=False):
                text = sib.get_text(strip=True)
                if text and len(text) > 5:
                    print(f"    - {sib.name}: {text[:60]}...")
        print()

    # Look for tables specifically
    print("=" * 70)
    print("ANALYZING TABLES")
    print("=" * 70)
    print()

    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    print()

    for i, table in enumerate(tables, 1):
        print(f"Table {i}:")
        print(f"  Class: {table.get('class')}")
        print(f"  ID: {table.get('id')}")

        # Check if table contains date
        if '13-02-2026' in table.get_text():
            print(f"  ⚠️ CONTAINS TARGET DATE!")

            # Get headers
            headers = table.find_all('th')
            if headers:
                print(f"  Headers: {[h.get_text(strip=True) for h in headers]}")

            # Get first few rows
            rows = table.find_all('tr')
            print(f"  Total rows: {len(rows)}")

            for j, row in enumerate(rows[:5], 1):
                cols = row.find_all(['td', 'th'])
                row_text = [col.get_text(strip=True)[:30] for col in cols]
                print(f"  Row {j}: {row_text}")

        print()

    # Look for PDF links near announcements
    print("=" * 70)
    print("ANALYZING PDF LINKS")
    print("=" * 70)
    print()

    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
    print(f"Found {len(pdf_links)} PDF links")
    print()

    for i, link in enumerate(pdf_links[:10], 1):
        href = link.get('href')
        text = link.get_text(strip=True)
        parent_text = link.parent.get_text(strip=True) if link.parent else ''

        print(f"PDF {i}:")
        print(f"  Text: {text[:60]}")
        print(f"  URL: {href}")
        print(f"  Parent context: {parent_text[:80]}...")
        print()

    # Save sample HTML for manual inspection
    print("=" * 70)
    print("SAVING HTML SAMPLE")
    print("=" * 70)
    print()

    # Save a section containing the date
    for elem in soup.find_all(text=date_pattern):
        if elem.parent:
            # Get grandparent or great-grandparent for more context
            context = elem.parent.parent if elem.parent.parent else elem.parent

            with open('/home/user/Investment/pibtl_announcement_sample.html', 'w', encoding='utf-8') as f:
                f.write(str(context.prettify()))

            print("✓ Saved HTML sample to: pibtl_announcement_sample.html")
            print(f"  Contains {len(context.get_text())} characters")
            print()
            break

if __name__ == "__main__":
    main()
