"""
PSX Announcement Classifier

Categorizes announcements and assigns materiality scores
Extracts financial data from announcement text and PDF attachments
"""

import re
from typing import Optional, Tuple, Dict
import logging
from psx_announcement_scraper_v2 import RawAnnouncement
from psx_announcement_storage import Announcement
from datetime import datetime

logger = logging.getLogger(__name__)


class AnnouncementClassifier:
    """
    Classifies PSX announcements by type and materiality

    Categories:
    - financial_results: Quarterly/annual results
    - dividend: Cash/bonus/rights dividends
    - board_meeting: Board meeting notices/outcomes
    - director_dealing: Director buy/sell shares
    - contract: Major contracts awarded
    - production: Production updates
    - corporate_action: M&A, splits, etc.
    - agm_egm: Annual/extraordinary general meetings
    - book_closure: Book closure notices
    - material_info: Price-sensitive information
    - regulatory: Regulatory compliance
    - other: Miscellaneous
    """

    # Category keywords mapping
    CATEGORY_KEYWORDS = {
        'financial_results': {
            'keywords': [
                'quarterly', 'annual', 'half yearly', 'half-yearly',
                'financial results', 'profit', 'loss', 'earnings',
                'eps', 'revenue', 'turnover', 'financial statements'
            ],
            'patterns': [
                r'Q[1-4].*results',
                r'(1st|2nd|3rd|4th).*quarter',
                r'year.*ended',
                r'financial.*performance'
            ]
        },
        'dividend': {
            'keywords': [
                'dividend', 'bonus', 'right issue', 'rights issue',
                'interim dividend', 'final dividend', 'cash dividend',
                'bonus shares', 'scrip dividend'
            ],
            'patterns': [
                r'dividend.*\d+%',
                r'\d+%.*dividend',
                r'bonus.*\d+:\d+',
                r'right.*\d+:\d+'
            ]
        },
        'board_meeting': {
            'keywords': [
                'board meeting', 'board of directors', 'meeting notice',
                'board decision', 'board resolution'
            ],
            'patterns': [
                r'board.*meeting',
                r'meeting.*scheduled',
                r'directors.*meeting'
            ]
        },
        'director_dealing': {
            'keywords': [
                'director', 'ceo', 'cfo', 'chairman',
                'shares acquired', 'shares sold', 'shareholding',
                'insider trading', 'beneficial ownership'
            ],
            'patterns': [
                r'director.*shares',
                r'ceo.*acquired',
                r'shares.*director'
            ]
        },
        'contract': {
            'keywords': [
                'contract', 'agreement', 'awarded', 'project',
                'mou', 'memorandum', 'won', 'secured'
            ],
            'patterns': [
                r'contract.*worth',
                r'project.*value',
                r'agreement.*signed',
                r'awarded.*\$'
            ]
        },
        'production': {
            'keywords': [
                'production', 'output', 'capacity', 'manufacturing',
                'oil production', 'gas production', 'cement dispatches',
                'monthly production', 'quarterly production'
            ],
            'patterns': [
                r'production.*\d+',
                r'output.*increased',
                r'capacity.*utilization'
            ]
        },
        'corporate_action': {
            'keywords': [
                'merger', 'acquisition', 'amalgamation', 'takeover',
                'restructuring', 'spin-off', 'split', 'consolidation',
                'delisting', 'listing'
            ],
            'patterns': [
                r'merger.*with',
                r'acquisition.*of',
                r'takeover.*bid'
            ]
        },
        'agm_egm': {
            'keywords': [
                'agm', 'egm', 'annual general meeting',
                'extraordinary general meeting', 'general meeting',
                'shareholders meeting'
            ],
            'patterns': [
                r'(agm|egm).*notice',
                r'general.*meeting.*\d{4}'
            ]
        },
        'book_closure': {
            'keywords': [
                'book closure', 'books closed', 'books close',
                'closed period', 'transfer books'
            ],
            'patterns': [
                r'book.*closure',
                r'books.*closed'
            ]
        },
        'material_info': {
            'keywords': [
                'price sensitive', 'material information',
                'disclosure', 'default', 'litigation', 'penalty',
                'investigation', 'suspension'
            ],
            'patterns': [
                r'material.*information',
                r'price.*sensitive'
            ]
        },
        'regulatory': {
            'keywords': [
                'secp', 'compliance', 'regulatory', 'filing',
                'cfs', 'pattern of shareholding', 'related party'
            ],
            'patterns': [
                r'secp.*compliance',
                r'regulatory.*requirement'
            ]
        }
    }

    def __init__(self):
        """Initialize classifier"""
        self.financial_extractor = FinancialDataExtractor()

    def classify(self, raw: RawAnnouncement) -> Announcement:
        """
        Classify raw announcement and convert to processed Announcement

        Args:
            raw: RawAnnouncement object from scraper

        Returns:
            Classified Announcement object
        """
        # Determine category
        category, subcategory = self._determine_category(raw.title, raw.description)

        # Score materiality
        materiality_tier = self._score_materiality(
            category, subcategory, raw.title, raw.description
        )

        # Extract financial data
        financial_data = self.financial_extractor.extract(raw.title, raw.description)

        # Determine market impact
        market_impact = self._determine_market_impact(category, financial_data)

        # Create Announcement object
        announcement = Announcement(
            announcement_id=raw.announcement_id,
            symbol=raw.symbol,
            announcement_date=raw.announcement_date,
            category=category,
            subcategory=subcategory,
            materiality_tier=materiality_tier,
            title=raw.title,
            description=raw.description,
            attachment_url=raw.attachment_url,
            source_url=raw.source_url,
            source=raw.source,
            dividend_amount=financial_data.get('dividend_amount'),
            dividend_type=financial_data.get('dividend_type'),
            eps=financial_data.get('eps'),
            profit_amount=financial_data.get('profit_amount'),
            profit_change_pct=financial_data.get('profit_change_pct'),
            revenue=financial_data.get('revenue'),
            fetched_date=raw.fetched_date,
            is_processed=True,
            processing_notes=f"Classified as {category} (Tier {materiality_tier})",
            market_impact=market_impact
        )

        return announcement

    def _determine_category(
        self,
        title: str,
        description: str
    ) -> Tuple[str, Optional[str]]:
        """
        Determine announcement category and subcategory

        Args:
            title: Announcement title
            description: Announcement description

        Returns:
            Tuple of (category, subcategory)
        """
        text = (title + " " + description).lower()

        # Check each category
        category_scores = {}

        for category, config in self.CATEGORY_KEYWORDS.items():
            score = 0

            # Keyword matching
            for keyword in config['keywords']:
                if keyword.lower() in text:
                    score += 2

            # Pattern matching
            for pattern in config.get('patterns', []):
                if re.search(pattern, text, re.IGNORECASE):
                    score += 3

            if score > 0:
                category_scores[category] = score

        # Get best match
        if category_scores:
            category = max(category_scores, key=category_scores.get)
            subcategory = self._determine_subcategory(category, text)
            return category, subcategory

        # Default
        return 'other', None

    def _determine_subcategory(self, category: str, text: str) -> Optional[str]:
        """Determine subcategory based on category"""

        if category == 'financial_results':
            if 'quarterly' in text or re.search(r'Q[1-4]', text, re.IGNORECASE):
                return 'quarterly'
            elif 'annual' in text or 'year ended' in text:
                return 'annual'
            elif 'half' in text:
                return 'half_yearly'

        elif category == 'dividend':
            if 'bonus' in text:
                return 'bonus'
            elif 'right' in text:
                return 'right_issue'
            elif 'interim' in text:
                return 'interim_cash'
            elif 'final' in text:
                return 'final_cash'
            else:
                return 'cash'

        elif category == 'contract':
            # Determine if major or minor based on value
            value_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(million|billion|m|b)', text, re.IGNORECASE)
            if value_match:
                value = float(value_match.group(1).replace(',', ''))
                unit = value_match.group(2).lower()

                if unit in ['billion', 'b']:
                    value *= 1000  # Convert to millions

                if value >= 100:  # $100M+
                    return 'major'
                else:
                    return 'minor'

        elif category == 'corporate_action':
            if 'merger' in text:
                return 'merger'
            elif 'acquisition' in text:
                return 'acquisition'
            elif 'split' in text:
                return 'split'

        return None

    def _score_materiality(
        self,
        category: str,
        subcategory: Optional[str],
        title: str,
        description: str
    ) -> int:
        """
        Assign materiality tier (1=Critical, 2=Material, 3=Info)

        Args:
            category: Announcement category
            subcategory: Announcement subcategory
            title: Announcement title
            description: Announcement description

        Returns:
            Materiality tier (1, 2, or 3)
        """
        text = (title + " " + description).lower()

        # TIER 1: CRITICAL (Immediate price impact expected)
        tier1_categories = [
            'financial_results',
            'dividend',
            'corporate_action'
        ]

        if category in tier1_categories:
            # Check for additional indicators of high impact
            if category == 'financial_results':
                # Look for significant profit changes
                if re.search(r'(profit|earnings).*(increased|decreased|up|down).*(20|30|40|50)%', text, re.IGNORECASE):
                    return 1
                # Look for loss
                if 'loss' in text and 'profit' not in text:
                    return 1

            if category == 'dividend':
                # Extract dividend percentage
                div_match = re.search(r'(\d+)%.*dividend|dividend.*(\d+)%', text)
                if div_match:
                    div_pct = int(div_match.group(1) or div_match.group(2))
                    if div_pct >= 30:  # High dividend
                        return 1
                # Bonus shares are always critical
                if 'bonus' in text:
                    return 1

            if category == 'corporate_action':
                # M&A always critical
                if any(word in text for word in ['merger', 'acquisition', 'takeover']):
                    return 1

            # Default to tier 1 for these categories if not specifically assessed
            return 1

        # Contract category - tier based on size
        if category == 'contract':
            if subcategory == 'major':
                return 1
            else:
                return 2

        # Material information
        if category == 'material_info':
            if any(word in text for word in ['default', 'penalty', 'investigation', 'suspension']):
                return 1
            return 2

        # TIER 2: MATERIAL (Significant but less urgent)
        tier2_categories = [
            'board_meeting',
            'director_dealing',
            'production',
            'agm_egm'
        ]

        if category in tier2_categories:
            return 2

        # TIER 3: INFORMATIONAL (Low/no impact)
        return 3

    def _determine_market_impact(
        self,
        category: str,
        financial_data: Dict
    ) -> Optional[str]:
        """
        Determine expected market impact (positive, negative, neutral)

        Args:
            category: Announcement category
            financial_data: Extracted financial data

        Returns:
            'positive', 'negative', 'neutral', or None
        """
        # Positive impact
        if category == 'dividend':
            return 'positive'

        if category == 'financial_results':
            profit_change = financial_data.get('profit_change_pct')
            if profit_change:
                if profit_change > 10:
                    return 'positive'
                elif profit_change < -10:
                    return 'negative'
                else:
                    return 'neutral'

        if category == 'contract' and financial_data.get('subcategory') == 'major':
            return 'positive'

        if category == 'corporate_action':
            return 'positive'  # Generally positive (acquisitions, etc.)

        if category == 'material_info':
            return 'negative'  # Usually negative (penalties, defaults)

        return None


class FinancialDataExtractor:
    """Extract financial data from announcement text"""

    def extract(self, title: str, description: str) -> Dict:
        """
        Extract financial data from text

        Returns:
            Dictionary with extracted values:
            - dividend_amount
            - dividend_type
            - eps
            - profit_amount
            - profit_change_pct
            - revenue
        """
        text = title + " " + description

        data = {}

        # Extract dividend
        dividend_data = self._extract_dividend(text)
        data.update(dividend_data)

        # Extract EPS
        eps = self._extract_eps(text)
        if eps:
            data['eps'] = eps

        # Extract profit
        profit_data = self._extract_profit(text)
        data.update(profit_data)

        # Extract revenue
        revenue = self._extract_revenue(text)
        if revenue:
            data['revenue'] = revenue

        return data

    def _extract_dividend(self, text: str) -> Dict:
        """Extract dividend information"""
        data = {}

        # Cash dividend (percentage)
        cash_match = re.search(
            r'(?:cash\s+)?dividend.*?(\d+(?:\.\d+)?)%|(\d+(?:\.\d+)?)%.*?dividend',
            text,
            re.IGNORECASE
        )
        if cash_match:
            amount = float(cash_match.group(1) or cash_match.group(2))
            data['dividend_amount'] = amount
            data['dividend_type'] = 'cash'

        # Cash dividend (rupees per share)
        cash_rs_match = re.search(
            r'(?:Rs\.?|PKR)\s*(\d+(?:\.\d+)?)\s*per share',
            text,
            re.IGNORECASE
        )
        if cash_rs_match and 'dividend' in text.lower():
            amount = float(cash_rs_match.group(1))
            data['dividend_amount'] = amount
            data['dividend_type'] = 'cash'

        # Bonus shares (ratio)
        bonus_match = re.search(
            r'bonus.*?(\d+):(\d+)|(\d+):(\d+).*?bonus',
            text,
            re.IGNORECASE
        )
        if bonus_match:
            if bonus_match.group(1):
                ratio_str = f"{bonus_match.group(1)}:{bonus_match.group(2)}"
                ratio = float(bonus_match.group(1)) / float(bonus_match.group(2))
            else:
                ratio_str = f"{bonus_match.group(3)}:{bonus_match.group(4)}"
                ratio = float(bonus_match.group(3)) / float(bonus_match.group(4))

            data['dividend_amount'] = ratio * 100  # Convert to percentage
            data['dividend_type'] = 'bonus'

        # Right shares
        right_match = re.search(
            r'right.*?(\d+):(\d+)|(\d+):(\d+).*?right',
            text,
            re.IGNORECASE
        )
        if right_match:
            if right_match.group(1):
                ratio = float(right_match.group(1)) / float(right_match.group(2))
            else:
                ratio = float(right_match.group(3)) / float(right_match.group(4))

            data['dividend_amount'] = ratio * 100
            data['dividend_type'] = 'right'

        return data

    def _extract_eps(self, text: str) -> Optional[float]:
        """Extract EPS (Earnings Per Share)"""
        # Pattern: EPS Rs. 10.50 or EPS: 10.50
        eps_match = re.search(
            r'eps[:\s]+(?:Rs\.?|PKR)?\s*(\d+(?:\.\d+)?)',
            text,
            re.IGNORECASE
        )
        if eps_match:
            return float(eps_match.group(1))

        return None

    def _extract_profit(self, text: str) -> Dict:
        """Extract profit amount and change percentage"""
        data = {}

        # Profit amount (in millions/billions)
        profit_match = re.search(
            r'(?:profit|earnings).*?(?:Rs\.?|PKR)\s*(\d+(?:\.\d+)?)\s*(million|billion|m|b)',
            text,
            re.IGNORECASE
        )
        if profit_match:
            amount = float(profit_match.group(1))
            unit = profit_match.group(2).lower()

            if unit in ['billion', 'b']:
                amount *= 1000  # Convert to millions

            data['profit_amount'] = amount

        # Profit change percentage
        change_match = re.search(
            r'(?:profit|earnings).*?(?:increased|decreased|up|down).*?(\d+(?:\.\d+)?)%',
            text,
            re.IGNORECASE
        )
        if change_match:
            change_pct = float(change_match.group(1))
            if 'decreased' in text.lower() or 'down' in text.lower():
                change_pct = -change_pct
            data['profit_change_pct'] = change_pct

        # Alternative: explicit percentage format
        pct_match = re.search(
            r'(\d+(?:\.\d+)?)%.*?(?:increase|decrease|growth|decline)',
            text,
            re.IGNORECASE
        )
        if pct_match and 'profit_change_pct' not in data:
            change_pct = float(pct_match.group(1))
            if 'decrease' in text.lower() or 'decline' in text.lower():
                change_pct = -change_pct
            data['profit_change_pct'] = change_pct

        return data

    def _extract_revenue(self, text: str) -> Optional[float]:
        """Extract revenue amount"""
        revenue_match = re.search(
            r'(?:revenue|turnover|sales).*?(?:Rs\.?|PKR)\s*(\d+(?:\.\d+)?)\s*(million|billion|m|b)',
            text,
            re.IGNORECASE
        )
        if revenue_match:
            amount = float(revenue_match.group(1))
            unit = revenue_match.group(2).lower()

            if unit in ['billion', 'b']:
                amount *= 1000

            return amount

        return None


if __name__ == "__main__":
    # Test classifier
    print("=" * 60)
    print("PSX ANNOUNCEMENT CLASSIFIER - TEST MODE")
    print("=" * 60)

    classifier = AnnouncementClassifier()

    # Test cases
    test_announcements = [
        RawAnnouncement(
            announcement_id="HBL_20260214_001",
            symbol="HBL",
            announcement_date=datetime.now(),
            title="Final Dividend 50%",
            description="Board announces final cash dividend of Rs 50 per share (500%) for year ended Dec 31, 2025",
            source_url="https://test.psx.com.pk"
        ),
        RawAnnouncement(
            announcement_id="OGDC_20260214_002",
            symbol="OGDC",
            announcement_date=datetime.now(),
            title="Quarterly Results Q1 2026",
            description="Profit increased by 35% to Rs 45 billion. EPS Rs 10.50",
            source_url="https://test.psx.com.pk"
        ),
        RawAnnouncement(
            announcement_id="LUCK_20260214_003",
            symbol="LUCK",
            announcement_date=datetime.now(),
            title="Contract Award",
            description="Major contract worth $150 million secured for cement supply",
            source_url="https://test.psx.com.pk"
        ),
        RawAnnouncement(
            announcement_id="PSO_20260214_004",
            symbol="PSO",
            announcement_date=datetime.now(),
            title="Book Closure Notice",
            description="Books will be closed from 20th to 25th March 2026",
            source_url="https://test.psx.com.pk"
        ),
    ]

    print("\nClassifying announcements...\n")

    for raw in test_announcements:
        announcement = classifier.classify(raw)

        print(f"{'='*60}")
        print(f"Symbol: {announcement.symbol}")
        print(f"Title: {announcement.title}")
        print(f"Category: {announcement.category}")
        print(f"Subcategory: {announcement.subcategory}")
        print(f"Materiality: Tier {announcement.materiality_tier} ", end="")

        if announcement.materiality_tier == 1:
            print("🔴 CRITICAL")
        elif announcement.materiality_tier == 2:
            print("🟡 MATERIAL")
        else:
            print("🟢 INFORMATIONAL")

        print(f"Market Impact: {announcement.market_impact or 'N/A'}")

        if announcement.dividend_amount:
            print(f"Dividend: {announcement.dividend_amount}% ({announcement.dividend_type})")

        if announcement.eps:
            print(f"EPS: Rs {announcement.eps}")

        if announcement.profit_change_pct:
            print(f"Profit Change: {announcement.profit_change_pct:+.1f}%")

        print()

    print("✅ Classifier test complete")
