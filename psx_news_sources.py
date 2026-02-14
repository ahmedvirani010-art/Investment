"""
PSX News Sources Configuration
Defines news sources for Pakistan Stock Exchange coverage
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class NewsSource:
    """Configuration for a news source"""
    name: str
    url: str
    source_type: str  # 'rss', 'web_scrape', 'api'
    language: str  # 'en', 'ur'
    priority: int  # 1-5, higher = more reliable
    rate_limit: float  # seconds between requests
    enabled: bool = True
    requires_auth: bool = False
    api_key: Optional[str] = None
    categories: List[str] = field(default_factory=list)


# Primary News Sources for PSX
PSX_NEWS_SOURCES = [
    # English Sources - Stock Specific
    NewsSource(
        name="Business Recorder",
        url="https://www.brecorder.com/rss/latest",
        source_type="rss",
        language="en",
        priority=5,
        rate_limit=2.0,
        categories=["stocks", "business", "economy"]
    ),
    NewsSource(
        name="Dawn Business",
        url="https://www.dawn.com/feeds/business",
        source_type="rss",
        language="en",
        priority=5,
        rate_limit=2.0,
        categories=["stocks", "business", "economy"]
    ),
    NewsSource(
        name="Express Tribune Business",
        url="https://tribune.com.pk/rss/business",
        source_type="rss",
        language="en",
        priority=4,
        rate_limit=2.0,
        categories=["stocks", "business"]
    ),
    NewsSource(
        name="The News Business",
        url="https://www.thenews.com.pk/rss/1/3",
        source_type="rss",
        language="en",
        priority=4,
        rate_limit=2.0,
        categories=["business"]
    ),
]

# Macro Economic News Sources
MACRO_NEWS_SOURCES = [
    NewsSource(
        name="Business Recorder Economy",
        url="https://www.brecorder.com/rss/economy",
        source_type="rss",
        language="en",
        priority=5,
        rate_limit=2.0,
        categories=["economy", "macro"]
    ),
    NewsSource(
        name="Dawn Economy",
        url="https://www.dawn.com/feeds/economy",
        source_type="rss",
        language="en",
        priority=5,
        rate_limit=2.0,
        categories=["economy", "macro"]
    ),
]


@dataclass
class MacroCategory:
    """Macro economic news category definition"""
    category_id: str
    keywords: List[str]
    affected_sectors: List[str]
    affected_symbols: List[str]  # Or 'ALL'
    impact_type: str  # 'revenue_positive', 'cost_negative', 'mixed'
    description: str
    typical_volatility: str  # 'low', 'moderate', 'high'
    regional_source: str


# Macro Economic Categories
MACRO_CATEGORIES = {
    'oil_prices': MacroCategory(
        category_id='oil_prices',
        keywords=['crude oil', 'brent', 'wti', 'oil price', 'petroleum cost'],
        affected_sectors=['Oil & Gas', 'Energy', 'Transport', 'Cement'],
        affected_symbols=['OGDC', 'PPL', 'PSO', 'APL', 'POL', 'MARI'],
        impact_type='revenue_positive',
        description='Crude oil price movements',
        typical_volatility='high',
        regional_source='Global'
    ),

    'interest_rates': MacroCategory(
        category_id='interest_rates',
        keywords=['policy rate', 'kibor', 'interest rate', 'state bank rate', 'monetary policy', 'sbp rate'],
        affected_sectors=['Banking', 'All'],
        affected_symbols=['HBL', 'UBL', 'MCB', 'MEBL', 'NBP', 'BAFL', 'BAHL', 'ABL', 'AKBL', 'FABL'],
        impact_type='revenue_positive',
        description='Interest rate changes',
        typical_volatility='moderate',
        regional_source='Pakistan'
    ),

    'gas_prices': MacroCategory(
        category_id='gas_prices',
        keywords=['gas price', 'lng', 'natural gas', 'gas tariff', 'ogra'],
        affected_sectors=['Gas Distribution', 'Fertilizer', 'Power'],
        affected_symbols=['SNGP', 'SSGC', 'FFC', 'EFERT', 'FATIMA'],
        impact_type='cost_negative',
        description='Natural gas and LNG prices',
        typical_volatility='moderate',
        regional_source='Pakistan + Import'
    ),

    'coal_prices': MacroCategory(
        category_id='coal_prices',
        keywords=['coal price', 'coal import', 'thermal coal'],
        affected_sectors=['Cement', 'Power'],
        affected_symbols=['LUCK', 'DGKC', 'MLCF', 'PIOC', 'FCCL', 'KOHC', 'CHCC', 'ACPL', 'THCCL'],
        impact_type='cost_negative',
        description='Coal prices for cement and power',
        typical_volatility='moderate',
        regional_source='Import'
    ),

    'usd_pkr': MacroCategory(
        category_id='usd_pkr',
        keywords=['dollar', 'exchange rate', 'rupee', 'usd/pkr', 'devaluation', 'forex'],
        affected_sectors=['All'],
        affected_symbols=['ALL'],
        impact_type='mixed',
        description='USD/PKR exchange rate',
        typical_volatility='high',
        regional_source='Pakistan'
    ),

    # Chemical Sector Specific
    'pta_prices': MacroCategory(
        category_id='pta_prices',
        keywords=['pta price', 'purified terephthalic acid', 'pta import', 'polyester raw material'],
        affected_sectors=['Chemicals', 'Textile'],
        affected_symbols=['EPCL', 'LOTCHEM', 'ICI', 'NML', 'NCL'],
        impact_type='cost_negative',
        description='PTA - key raw material for polyester/PET',
        typical_volatility='high',
        regional_source='China'
    ),

    'caustic_soda_prices': MacroCategory(
        category_id='caustic_soda_prices',
        keywords=['caustic soda', 'sodium hydroxide', 'naoh', 'caustic price', 'chlor-alkali'],
        affected_sectors=['Chemicals', 'Textile', 'Paper'],
        affected_symbols=['EPCL', 'ICI', 'NML', 'NCL', 'CPPL', 'LOTCHEM'],
        impact_type='mixed',
        description='Caustic soda for chemicals and textile',
        typical_volatility='moderate',
        regional_source='Local + Import'
    ),

    'ethylene_prices': MacroCategory(
        category_id='ethylene_prices',
        keywords=['ethylene price', 'ethylene', 'c2', 'naphtha cracker', 'ethylene derivative'],
        affected_sectors=['Chemicals'],
        affected_symbols=['EPCL', 'LOTCHEM', 'ICI'],
        impact_type='cost_negative',
        description='Ethylene - building block for polymers',
        typical_volatility='high',
        regional_source='Middle East + Local'
    ),

    'propylene_prices': MacroCategory(
        category_id='propylene_prices',
        keywords=['propylene price', 'polypropylene', 'pp', 'c3', 'propylene derivative'],
        affected_sectors=['Chemicals', 'Packaging'],
        affected_symbols=['EPCL', 'LOTCHEM', 'ICI', 'PAEL', 'CHERAT'],
        impact_type='cost_negative',
        description='Propylene for polypropylene and packaging',
        typical_volatility='high',
        regional_source='Middle East + Import'
    ),

    'monomers_prices': MacroCategory(
        category_id='monomers_prices',
        keywords=['meg price', 'monoethylene glycol', 'glycol', 'meg import', 'polyester feedstock'],
        affected_sectors=['Chemicals', 'Textile'],
        affected_symbols=['EPCL', 'LOTCHEM', 'NML', 'NCL'],
        impact_type='cost_negative',
        description='MEG + PTA = Polyester (PET)',
        typical_volatility='high',
        regional_source='Middle East'
    ),

    'naphtha_prices': MacroCategory(
        category_id='naphtha_prices',
        keywords=['naphtha price', 'naphtha', 'light naphtha', 'naphtha cracker', 'petrochemical feedstock'],
        affected_sectors=['Chemicals'],
        affected_symbols=['EPCL', 'LOTCHEM'],
        impact_type='cost_negative',
        description='Primary feedstock for petrochemicals',
        typical_volatility='high',
        regional_source='Import (linked to crude)'
    ),

    'polyester_prices': MacroCategory(
        category_id='polyester_prices',
        keywords=['polyester price', 'pet resin', 'polyester fiber', 'polyester staple fiber', 'psf'],
        affected_sectors=['Chemicals', 'Textile'],
        affected_symbols=['EPCL', 'LOTCHEM', 'NML', 'NCL', 'GATM'],
        impact_type='mixed',
        description='Polyester - revenue for chemicals, cost for textile',
        typical_volatility='moderate',
        regional_source='Local + Import'
    ),

    'steel_prices': MacroCategory(
        category_id='steel_prices',
        keywords=['steel price', 'iron ore', 'scrap metal', 'rebar'],
        affected_sectors=['Steel'],
        affected_symbols=['ASTL', 'ISL', 'ASL', 'MUGHAL'],
        impact_type='mixed',
        description='Steel and iron ore prices',
        typical_volatility='high',
        regional_source='Global'
    ),

    'cotton_prices': MacroCategory(
        category_id='cotton_prices',
        keywords=['cotton price', 'lint', 'cotton crop', 'cotton import'],
        affected_sectors=['Textile'],
        affected_symbols=['NML', 'NCL', 'GATM', 'KTML'],
        impact_type='cost_negative',
        description='Cotton prices for textile industry',
        typical_volatility='moderate',
        regional_source='Local + Import'
    ),

    'wheat_prices': MacroCategory(
        category_id='wheat_prices',
        keywords=['wheat price', 'grain', 'food commodity', 'wheat import'],
        affected_sectors=['Food'],
        affected_symbols=['EFOODS', 'NESTLE', 'UNITY'],
        impact_type='cost_negative',
        description='Wheat prices for food industry',
        typical_volatility='moderate',
        regional_source='Local + Import'
    ),

    'electricity_tariff': MacroCategory(
        category_id='electricity_tariff',
        keywords=['electricity tariff', 'power tariff', 'nepra', 'fuel adjustment', 'power cost'],
        affected_sectors=['Power', 'Cement', 'Textile', 'All'],
        affected_symbols=['HUBC', 'KAPCO', 'LUCK', 'DGKC', 'NML'],
        impact_type='cost_negative',
        description='Electricity tariff changes',
        typical_volatility='moderate',
        regional_source='Pakistan'
    ),

    'taxation': MacroCategory(
        category_id='taxation',
        keywords=['tax', 'super tax', 'income tax', 'sales tax', 'gst', 'fbr'],
        affected_sectors=['All'],
        affected_symbols=['ALL'],
        impact_type='cost_negative',
        description='Tax policy changes',
        typical_volatility='low',
        regional_source='Pakistan'
    ),

    'inflation': MacroCategory(
        category_id='inflation',
        keywords=['inflation', 'cpi', 'consumer price index', 'pbs inflation', 'price index'],
        affected_sectors=['All'],
        affected_symbols=['ALL'],
        impact_type='mixed',
        description='Inflation and CPI data',
        typical_volatility='low',
        regional_source='Pakistan'
    ),
}


def get_all_sources() -> List[NewsSource]:
    """Get all enabled news sources"""
    return [s for s in PSX_NEWS_SOURCES + MACRO_NEWS_SOURCES if s.enabled]


def get_stock_sources() -> List[NewsSource]:
    """Get stock-specific news sources"""
    return [s for s in PSX_NEWS_SOURCES if s.enabled]


def get_macro_sources() -> List[NewsSource]:
    """Get macro economic news sources"""
    return [s for s in MACRO_NEWS_SOURCES if s.enabled]


def get_macro_category(category_id: str) -> Optional[MacroCategory]:
    """Get macro category by ID"""
    return MACRO_CATEGORIES.get(category_id)


def identify_macro_category(text: str) -> Optional[MacroCategory]:
    """Identify macro category from text based on keywords"""
    text_lower = text.lower()

    for category in MACRO_CATEGORIES.values():
        if any(keyword in text_lower for keyword in category.keywords):
            return category

    return None
