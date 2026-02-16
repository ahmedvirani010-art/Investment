"""
Find actual announcements on PIBTL company page
Focus on tables and PDF links, ignore market indices
"""

from psx_announcement_scraper import PSXAnnouncementScraper
from bs4 import BeautifulSoup
import re

def main():
    print("=" * 70)
    print("FINDING REAL ANNOUNCEMENTS FOR PIBTL")
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

    # Strategy 1: Look for tables with actual announcement data
    print("=" * 70)
    print("STRATEGY 1: ANALYZING TABLES FOR ANNOUNCEMENTS")
    print("=" * 70)
    print()

    tables = soup.find_all('table', class_='tbl')
    print(f"Found {len(tables)} tables with class 'tbl'")
    print()

    for i, table in enumerate(tables, 1):
        print(f"\nTable {i}:")
        print("-" * 50)

        # Get headers
        headers = table.find_all('th')
        header_texts = [h.get_text(strip=True) for h in headers]

        if headers:
            print(f"Headers: {header_texts}")

        # Check if this looks like an announcements table
        announcement_keywords = ['announcement', 'notice', 'title', 'date', 'subject', 'type']
        is_announcement_table = any(
            keyword in ' '.join(header_texts).lower()
            for keyword in announcement_keywords
        )

        if is_announcement_table:
            print("⚠️ POTENTIAL ANNOUNCEMENT TABLE!")

        # Show all rows
        rows = table.find_all('tr')
        print(f"Rows: {len(rows)}")

        for j, row in enumerate(rows[:10], 1):  # Show first 10 rows
            cols = row.find_all(['td', 'th'])

            if not cols:
                continue

            # Get text from each column
            col_texts = []
            for col in cols:
                # Check for links
                links = col.find_all('a')
                if links:
                    link_text = ', '.join([f"{a.get_text(strip=True)}[{a.get('href', '')}]" for a in links])
                    col_texts.append(link_text)
                else:
                    col_texts.append(col.get_text(strip=True))

            print(f"  Row {j}: {col_texts}")

        print()

    # Strategy 2: Look specifically for announcement/notice sections
    print("=" * 70)
    print("STRATEGY 2: LOOKING FOR ANNOUNCEMENT SECTIONS")
    print("=" * 70)
    print()

    # Common PSX patterns
    announcement_patterns = [
        ('div', {'class': re.compile(r'announcement', re.I)}),
        ('div', {'id': re.compile(r'announcement', re.I)}),
        ('section', {'class': re.compile(r'announcement', re.I)}),
        ('div', {'class': re.compile(r'company.*notice', re.I)}),
    ]

    for tag, attrs in announcement_patterns:
        elements = soup.find_all(tag, attrs)
        if elements:
            print(f"Found {len(elements)} {tag} elements matching {attrs}")
            for elem in elements[:3]:  # Show first 3
                print(f"  Class: {elem.get('class')}")
                print(f"  Text: {elem.get_text(strip=True)[:200]}...")
                print()

    # Strategy 3: Analyze PDF links more carefully
    print("=" * 70)
    print("STRATEGY 3: ANALYZING PDF LINKS (LIKELY ANNOUNCEMENTS)")
    print("=" * 70)
    print()

    # Look for rows/containers that have PDF links
    pdf_rows = []

    for pdf_link in soup.find_all('a', href=re.compile(r'\.pdf$', re.I)):
        # Get the row/container this PDF is in
        parent_row = pdf_link.find_parent('tr')

        if parent_row:
            pdf_rows.append(parent_row)

    print(f"Found {len(pdf_rows)} table rows with PDF links")
    print()

    for i, row in enumerate(pdf_rows[:10], 1):
        cols = row.find_all(['td', 'th'])

        print(f"PDF Row {i}:")

        for j, col in enumerate(cols, 1):
            text = col.get_text(strip=True)
            links = col.find_all('a')

            print(f"  Col {j}: {text[:50]}")

            if links:
                for link in links:
                    href = link.get('href', '')
                    if href.endswith('.pdf'):
                        full_url = f"https://dps.psx.com.pk{href}" if href.startswith('/') else href
                        print(f"    PDF: {full_url}")

        print()

    # Strategy 4: Look for company announcement tab/section
    print("=" * 70)
    print("STRATEGY 4: LOOKING FOR TAB/SECTION HEADERS")
    print("=" * 70)
    print()

    # Find all headings
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
    for heading in headings:
        text = heading.get_text(strip=True)
        if text and ('announcement' in text.lower() or 'notice' in text.lower()):
            print(f"Found heading: {text}")
            print(f"  Tag: {heading.name}")
            print(f"  Class: {heading.get('class')}")

            # Look for content after this heading
            next_elem = heading.find_next_sibling()
            if next_elem:
                print(f"  Next element: {next_elem.name}")
                print(f"  Content: {next_elem.get_text(strip=True)[:100]}...")

            print()

if __name__ == "__main__":
    main()
