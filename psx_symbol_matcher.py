"""
PSX Stock Symbol Matcher
Maps company names in news articles to stock symbols
"""

import re
import math
from typing import List, Tuple, Dict, Set, Optional
from rapidfuzz import fuzz

# Single-word aliases that are too generic to match alone (avoid false positives)
GENERIC_WORD_BLOCKLIST = {
    "united", "national", "pakistan", "bank", "banks", "limited", "company",
    "ltd", "the", "oil", "gas", "cement", "power", "steel", "textile", "food",
    "foods", "group", "corporation", "industries", "mill", "mills", "company",
}


class PSXSymbolMatcher:
    """Matches company names in text to PSX stock symbols"""

    def __init__(self):
        """Initialize with PSX stock mappings"""
        self.stock_mappings = self._build_stock_mappings()
        self.reverse_index = self._build_reverse_index()

    def _build_stock_mappings(self) -> Dict[str, Dict]:
        """Build comprehensive mapping of all PSX stocks"""
        # Comprehensive list from PSX Liquidity Screener
        base_stocks = {
            # Banks
            "HBL": "Habib Bank Limited",
            "UBL": "United Bank Limited",
            "MCB": "MCB Bank Limited",
            "BAFL": "Bank Alfalah Limited",
            "ABL": "Allied Bank Limited",
            "BAHL": "Bank Al-Habib Limited",
            "MEBL": "Meezan Bank Limited",
            "NBP": "National Bank of Pakistan",
            "AKBL": "Askari Bank Limited",
            "FABL": "Faysal Bank Limited",
            "SNBL": "Soneri Bank Limited",
            "BOP": "Bank of Punjab",
            "HMB": "Habib Metropolitan Bank",
            "SCBPL": "Standard Chartered Bank Pakistan",
            "JSBL": "JS Bank Limited",

            # Oil & Gas
            "SNGP": "Sui Northern Gas Pipelines Limited",
            "OGDC": "Oil & Gas Development Company",
            "PPL": "Pakistan Petroleum Limited",
            "POL": "Pakistan Oilfields Limited",
            "MARI": "Mari Petroleum Company Limited",
            "PSO": "Pakistan State Oil",
            "APL": "Attock Petroleum Limited",
            "SSGC": "Sui Southern Gas Company",

            # Cement
            "LUCK": "Lucky Cement Limited",
            "DGKC": "D.G. Khan Cement Company",
            "MLCF": "Maple Leaf Cement Factory",
            "PIOC": "Pioneer Cement Limited",
            "CHCC": "Cherat Cement Company",
            "FCCL": "Fauji Cement Company Limited",
            "KOHC": "Kohat Cement Company Limited",
            "ACPL": "Attock Cement Pakistan Limited",
            "THCCL": "Thal Cement Limited",

            # Fertilizer
            "FFC": "Fauji Fertilizer Company",
            "EFERT": "Engro Fertilizers Limited",
            "FATIMA": "Fatima Fertilizer Company",

            # Power
            "HUBC": "Hub Power Company",
            "KAPCO": "Kot Addu Power Company",

            # Textile
            "GATM": "Gul Ahmed Textile Mills",
            "NCL": "Nishat Chunian Limited",
            "NML": "Nishat Mills Limited",
            "KTML": "Kohinoor Textile Mills",

            # Food & Personal Care
            "NESTLE": "Nestle Pakistan Limited",
            "EFOODS": "Engro Foods Limited",
            "UNITY": "Unity Foods Limited",
            "NATF": "Natco Pharma Limited",

            # Automobiles & Parts
            "INDU": "Indus Motor Company",
            "HCAR": "Honda Atlas Cars Pakistan",
            "ATLH": "Atlas Honda Limited",
            "MTL": "Millat Tractors Limited",
            "GADT": "Ghandhara Automobiles Limited",

            # Chemicals
            "ICI": "ICI Pakistan Limited",
            "EPCL": "Engro Polymer & Chemicals",
            "LOTCHEM": "Lotte Chemical Pakistan Limited",

            # Pharmaceuticals
            "GLAXO": "GlaxoSmithKline Pakistan",
            "SEARL": "Searle Company Limited",

            # Technology & Communication
            "TRG": "The Resource Group",
            "SYS": "Systems Limited",
            "NETSOL": "NetSol Technologies",
            "AVN": "Avanceon Limited",
            "PTC": "Pakistan Tobacco Company",
            "AIRLINK": "Airlink Communication Limited",

            # Steel & Engineering
            "ASTL": "Amreli Steels Limited",
            "ISL": "International Steels Limited",
            "ASL": "Aisha Steel Mills Limited",
            "MUGHAL": "Mughal Iron & Steel Industries",

            # Paper & Board
            "CPPL": "Century Paper & Board Mills",

            # Investment Companies
            "PAEL": "Pakistan Aluminium Beverage Cans",
            "PKGS": "Packages Limited",

            # Miscellaneous
            "LOADS": "Loads Limited",
            "DAWH": "Dawood Hercules Corporation",
            "SHEL": "Shell Pakistan Limited",
            "COLG": "Colgate Palmolive Pakistan",
            "SIEM": "Siemens Pakistan Engineering",
            "RMPL": "Rafhan Maize Products",
            "AICL": "Archroma Pakistan Limited",
            "GTYR": "General Tyre & Rubber Company",
            "SHFA": "Shifa International Hospital",
            "ABOT": "Abbott Laboratories Pakistan",
            "FEROZ": "Ferozsons Laboratories Limited",
            "FHAM": "Fauji Foods Limited",
            "CLOV": "Clover Pakistan Limited",
            "AGTL": "AGP Limited",
            "THALL": "Thal Limited",
            "ADMM": "Adamjee Insurance Company",
        }

        # Build enhanced mappings with aliases and keywords
        mappings = {}
        for symbol, full_name in base_stocks.items():
            aliases = self._generate_aliases(symbol, full_name)
            keywords = self._extract_keywords(full_name)
            sector = self._determine_sector(symbol)

            mappings[symbol] = {
                'full_name': full_name,
                'aliases': aliases,
                'keywords': keywords,
                'sector': sector
            }

        return mappings

    def _generate_aliases(self, symbol: str, full_name: str) -> List[str]:
        """Generate common aliases for a company (multi-word and discriminative where possible)."""
        aliases = []

        # Remove "Limited", "Pakistan", etc.
        short_name = full_name.replace(" Limited", "").replace(" Pakistan", "")
        aliases.append(short_name)

        # Multi-word discriminative phrases (sector-qualified to avoid location-only false matches)
        discriminative = {
            "HBL": ["Habib Bank", "Habib Bank Limited"],
            "UBL": ["United Bank", "United Bank Limited"],
            "MCB": ["MCB Bank", "MCB Bank Limited"],
            "PSO": ["Pakistan State Oil", "State Oil"],
            "OGDC": ["Oil & Gas Development", "OGDC Limited"],
            "PPL": ["Pakistan Petroleum", "Pakistan Petroleum Limited"],
            "FFC": ["Fauji Fertilizer", "Fauji Fertilizer Company"],
            "FHAM": ["Fauji Foods", "Fauji Foods Limited"],
            "FCCL": ["Fauji Cement", "Fauji Cement Company"],
            "LUCK": ["Lucky Cement", "Lucky Cement Limited"],
            "DGKC": ["D.G. Khan Cement", "DG Khan Cement"],
            "KOHC": ["Kohat Cement", "Kohat Cement Company"],
            "ACPL": ["Attock Cement", "Attock Cement Pakistan"],
            "PIOC": ["Pioneer Cement"],
            "MLCF": ["Maple Leaf Cement"],
            "EFERT": ["Engro Fertilizers", "Engro Fertilizers Limited"],
            "EFOODS": ["Engro Foods", "Engro Foods Limited"],
            "HUBC": ["Hub Power", "Hub Power Company"],
            "NML": ["Nishat Mills", "Nishat Mills Limited"],
            "NCL": ["Nishat Chunian", "Nishat Chunian Limited"],
            "DAWH": ["Dawood Hercules", "Dawood Hercules Corporation"],
        }
        if symbol in discriminative:
            aliases.extend(discriminative[symbol])

        # First word only if not generic (used for reverse index filtering later)
        words = full_name.split()
        if len(words) > 1:
            aliases.append(words[0])

        # Common abbreviations
        if "Bank" in full_name:
            aliases.append(short_name.replace(" Bank", ""))
        if "Cement" in full_name:
            aliases.append(short_name.replace(" Cement", ""))

        return list(set(aliases))

    def _extract_keywords(self, full_name: str) -> List[str]:
        """Extract searchable keywords from company name"""
        # Remove common words
        stop_words = {'limited', 'pakistan', 'company', 'ltd', 'the'}
        words = full_name.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords

    def _determine_sector(self, symbol: str) -> str:
        """Determine sector from symbol"""
        sector_map = {
            'HBL,UBL,MCB,BAFL,ABL,BAHL,MEBL,NBP,AKBL,FABL,SNBL,BOP,HMB,SCBPL,JSBL': 'Banking',
            'OGDC,PPL,POL,MARI,PSO,APL': 'Oil & Gas',
            'SNGP,SSGC': 'Gas Distribution',
            'LUCK,DGKC,MLCF,PIOC,CHCC,FCCL,KOHC,ACPL,THCCL': 'Cement',
            'FFC,EFERT,FATIMA': 'Fertilizer',
            'HUBC,KAPCO': 'Power',
            'GATM,NCL,NML,KTML': 'Textile',
            'ICI,EPCL,LOTCHEM,AICL': 'Chemicals',
            'ASTL,ISL,ASL,MUGHAL': 'Steel',
        }

        for symbols, sector in sector_map.items():
            if symbol in symbols.split(','):
                return sector

        return 'Other'

    def _build_reverse_index(self) -> Dict[str, str]:
        """Build reverse index: full names and multi-word aliases only (no single-word keywords)."""
        index = {}

        for symbol, data in self.stock_mappings.items():
            # Full name always
            index[data['full_name'].lower()] = symbol

            # Aliases: multi-word only (avoids false positives from "khan", "communication", etc.)
            for alias in data['aliases']:
                key = alias.lower().strip()
                if not key or " " not in key:
                    continue
                index[key] = symbol

        return index

    def find_mentioned_symbols(self, text: str) -> List[Tuple[str, float]]:
        """
        Find all stock symbols mentioned in text.

        Returns:
            List of (symbol, confidence) tuples. Weak matches below MIN_CONFIDENCE are dropped.
        """
        MIN_CONFIDENCE = 0.55
        text_lower = text.lower()
        mentions = {}

        # Method 1: Exact symbol match (highest confidence)
        for symbol in self.stock_mappings.keys():
            pattern = r'\b' + re.escape(symbol) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                mentions[symbol] = max(mentions.get(symbol, 0), 1.0)

        # Method 2: Full company name match
        for symbol, data in self.stock_mappings.items():
            if data['full_name'].lower() in text_lower:
                mentions[symbol] = max(mentions.get(symbol, 0), 0.95)

        # Method 3: Multi-word alias match only
        for key, symbol in self.reverse_index.items():
            if len(key) > 3 and key in text_lower:
                mentions[symbol] = max(mentions.get(symbol, 0), 0.7)

        # Drop weak matches
        mentions = {s: c for s, c in mentions.items() if c >= MIN_CONFIDENCE}
        return sorted(mentions.items(), key=lambda x: x[1], reverse=True)

    def determine_primary_symbol(self, mentions: List[Tuple[str, float]], text: str = "") -> Optional[str]:
        """
        Determine the primary stock symbol from mentions using confidence,
        frequency in text, title/lead weighting, and tie-break by earliest mention.
        """
        if not mentions:
            return None

        if len(mentions) == 1:
            return mentions[0][0]

        text_lower = text.lower() if text else ""
        title_zone = text_lower[:200]  # Title and lead (first ~200 chars)

        # Base score from confidence
        scores = {s: c for s, c in mentions}

        # Frequency: count occurrences of symbol, full name, and main aliases
        for symbol, _ in mentions:
            data = self.stock_mappings.get(symbol)
            if not data:
                continue
            count = 0
            pattern = r'\b' + re.escape(symbol) + r'\b'
            count += len(re.findall(pattern, text, re.IGNORECASE))
            if data['full_name'].lower() in text_lower:
                count += 2  # full name is strong signal
            for alias in data['aliases']:
                if " " in alias and alias.lower() in text_lower:
                    count += 1
            if count > 0:
                scores[symbol] = scores.get(symbol, 0) + math.log(1 + count) * 0.1

        # Title/lead boost: symbol or full name or multi-word alias in first 200 chars
        for symbol, _ in mentions:
            data = self.stock_mappings.get(symbol)
            if symbol.lower() in title_zone:
                scores[symbol] = scores.get(symbol, 0) * 1.5
                continue
            if data and data['full_name'].lower() in title_zone:
                scores[symbol] = scores.get(symbol, 0) * 1.5
                continue
            if data:
                for alias in data.get('aliases', []):
                    if " " in alias and alias.lower() in title_zone:
                        scores[symbol] = scores.get(symbol, 0) * 1.5
                        break

        # Tie-break: when scores are close, prefer symbol that appears earliest in text
        best_score = max(scores.values()) if scores else 0
        candidates = [s for s, sc in scores.items() if sc >= best_score * 0.95]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            return max(scores.items(), key=lambda x: x[1])[0] if scores else None

        earliest_pos = {}
        for symbol in candidates:
            data = self.stock_mappings.get(symbol)
            pos = len(text_lower)
            pattern = r'\b' + re.escape(symbol) + r'\b'
            m = re.search(pattern, text_lower)
            if m:
                pos = min(pos, m.start())
            if data:
                fn = data['full_name'].lower()
                idx = text_lower.find(fn)
                if idx != -1:
                    pos = min(pos, idx)
            earliest_pos[symbol] = pos

        return min(candidates, key=lambda s: earliest_pos.get(s, len(text_lower)))

    def resolve_company_name(self, company_name: str) -> Optional[str]:
        """
        Resolve a company name to its stock symbol

        Args:
            company_name: Company name to resolve

        Returns:
            Stock symbol or None
        """
        normalized = company_name.lower().strip()

        # Exact match
        if normalized in self.reverse_index:
            return self.reverse_index[normalized]

        # Fuzzy match using rapidfuzz
        best_match = None
        best_score = 0

        for key, symbol in self.reverse_index.items():
            score = fuzz.ratio(normalized, key)
            if score > best_score and score > 80:  # 80% similarity threshold
                best_score = score
                best_match = symbol

        return best_match

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get full information for a symbol"""
        return self.stock_mappings.get(symbol)

    def get_all_symbols(self) -> List[str]:
        """Get list of all tracked symbols"""
        return list(self.stock_mappings.keys())

    def get_symbols_by_sector(self, sector: str) -> List[str]:
        """Get all symbols in a sector"""
        return [
            symbol for symbol, data in self.stock_mappings.items()
            if data['sector'] == sector
        ]
