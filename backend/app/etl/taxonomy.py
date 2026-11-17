"""Engineering job taxonomy, geo normalization, and canonical skill extraction."""

from __future__ import annotations

import re
from typing import Any

ENGINEERING_TAXONOMY: dict[str, list[str]] = {
    "Computer Science & IT": [
        "AI & Machine Learning", "Data Science & Analytics", "Full-Stack & Web",
        "Cloud & DevOps", "Cybersecurity", "Embedded & Systems",
    ],
    "Mechanical Engineering": [
        "CAD/CAM & Product Design", "Robotics & Mechatronics", "HVAC & Thermal Systems",
        "Manufacturing & Quality", "Automotive & EV",
    ],
    "Civil & Structural Engineering": [
        "Structural Design", "Construction Management", "Transportation & Infrastructure",
        "Geotechnical & Environmental", "BIM & Urban Planning",
    ],
    "Electrical & Electronics": [
        "VLSI & Semiconductors", "Power Systems & Smart Grid", "Control & Instrumentation",
        "Embedded Hardware & IoT", "Telecommunications",
    ],
    "Chemical & Process": [
        "Process Engineering", "Petrochemicals & Energy", "Pharmaceuticals & Biotech",
        "Materials & Polymers",
    ],
    "Aerospace & Automotive": [
        "Aerodynamics & Propulsion", "Avionics", "EV Powertrain", "Vehicle Dynamics",
    ],
    "Industrial & Manufacturing": [
        "Supply Chain & Operations", "Quality Assurance & Six Sigma", "Plant & Process Automation",
    ],
}

REGIONS = ["India", "APAC", "Europe", "North America", "Middle East", "Global/Remote"]

# Canonical names map to regex aliases, ordered to prefer specific products and
# avoid substrings (for example, Go inside Golang or Java inside JavaScript).
CANONICAL_SKILL_DICTIONARY: dict[str, tuple[str, ...]] = {
    "JavaScript": (r"\bjavascript\b", r"\bjs\b"),
    "TypeScript": (r"\btypescript\b", r"\bts\b"),
    "React": (r"\breact(?:\.js|js)?\b",),
    "Next.js": (r"\bnext(?:\.js|js)\b",),
    "Node.js": (r"\bnode(?:\.js|js)\b",),
    "PostgreSQL": (r"\bpostgres(?:ql)?\b",),
    "Scikit-learn": (r"\bscikit[ -]?learn\b", r"\bsklearn\b"),
    "PyTorch": (r"\bpytorch\b",),
    "TensorFlow": (r"\btensorflow\b",),
    "Python": (r"\bpython\b",),
    "Java": (r"\bjava\b",),
    "C++": (r"\bc\+\+\b",),
    "C#": (r"\bc#\b", r"\bc sharp\b"),
    "Go": (r"\bgolang\b", r"\bgo language\b"),
    "Ruby": (r"\bruby\b",),
    "PHP": (r"\bphp\b",),
    "Rust": (r"\brust\b",),
    "SQL": (r"\bsql\b",),
    "MySQL": (r"\bmysql\b",),
    "MongoDB": (r"\bmongodb?\b",),
    "Redis": (r"\bredis\b",),
    "Django": (r"\bdjango\b",),
    "FastAPI": (r"\bfastapi\b",),
    "Flask": (r"\bflask\b",),
    "GraphQL": (r"\bgraphql\b",),
    "REST APIs": (r"\brest(?:ful)? apis?\b",),
    "AWS": (r"\baws\b", r"amazon web services"),
    "Azure": (r"\bazure\b",),
    "Google Cloud": (r"google cloud", r"\bgcp\b"),
    "Docker": (r"\bdocker\b",),
    "Kubernetes": (r"\bkubernetes\b", r"\bk8s\b"),
    "Terraform": (r"\bterraform\b",),
    "CI/CD": (r"\bci\s*/\s*cd\b", r"continuous integration", r"continuous delivery"),
    "Pandas": (r"\bpandas\b",),
    "NumPy": (r"\bnumpy\b",),
    "Apache Spark": (r"apache spark", r"\bspark\b"),
    "Airflow": (r"\bapache airflow\b", r"\bairflow\b"),
    "dbt": (r"\bdbt\b",),
    "Tableau": (r"\btableau\b",),
    "Power BI": (r"power\s*bi",),
    "Machine Learning": (r"machine learning", r"\bml\b"),
    "LLMs": (r"\bllms?\b", r"large language models?"),
    "LangChain": (r"\blangchain\b",),
    "Elasticsearch": (r"\belasticsearch\b",),
    "Kafka": (r"\bkafka\b",),
    "Git": (r"\bgit\b",),
    "AutoCAD": (r"\bautocad\b",),
    "SolidWorks": (r"\bsolidworks\b", r"solid works"),
    "ANSYS": (r"\bansys\b",),
    "MATLAB": (r"\bmatlab\b",),
    "CATIA": (r"\bcatia\b",),
    "Revit": (r"\brevit\b",),
    "STAAD.Pro": (r"\bstaad(?:\.pro)?\b",),
    "PLC/SCADA": (r"\bplc\b", r"\bscada\b"),
    "ETAP": (r"\betap\b",),
    "Verilog": (r"\bverilog\b",),
    "Embedded C": (r"\bembedded c\b", r"\barm cortex\b"),
    "Six Sigma": (r"six\s*sigma", r"\b6\s*sigma\b"),
    "Lean Manufacturing": (r"lean manufacturing", r"lean production"),
    "Aspen HYSYS": (r"aspen\s*hysys", r"\bhysys\b"),
    "Primavera P6": (r"primavera\s*p6", r"\bp6\b"),
    "GD&T": (r"gd\s*&\s*t", r"geometric dimensioning and tolerancing"),
    "FEA": (r"\bfea\b", r"finite element analysis"),
    "CFD": (r"\bcfd\b", r"computational fluid dynamics"),
}

BRANCH_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Aerospace & Automotive", ("aerospace", "aeronautical", "avionics", "aircraft", "propulsion", "vehicle dynamics", "ev powertrain")),
    ("Civil & Structural Engineering", ("civil engineer", "structural engineer", "structural design", "geotechnical", "construction manager", "bim model", "transportation infrastructure", "urban planner")),
    ("Electrical & Electronics", ("electrical engineer", "electronics engineer", "vlsi", "semiconductor", "power systems", "smart grid", "instrumentation", "telecommunications", "hardware engineer")),
    ("Chemical & Process", ("chemical engineer", "process engineer", "petrochemical", "refinery", "pharmaceutical", "biotech", "polymer", "aspen hysys")),
    ("Industrial & Manufacturing", ("industrial engineer", "manufacturing engineer", "six sigma", "supply chain", "quality assurance", "plant automation", "lean manufacturing")),
    ("Mechanical Engineering", ("mechanical engineer", "solidworks", "autocad", "catia", "hvac", "thermal systems", "robotics", "mechatronics", "automotive engineer", "cad/cam")),
    ("Computer Science & IT", ("software engineer", "software developer", "computer science", "machine learning", "data scientist", "data engineer", "web developer", "cloud engineer", "cybersecurity", "devops", "embedded software")),
)

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "AI & Machine Learning": ("machine learning", "artificial intelligence", "deep learning", "llm", "nlp", "computer vision", "pytorch", "tensorflow"),
    "Data Science & Analytics": ("data science", "data scientist", "data analyst", "analytics", "business intelligence", "tableau", "power bi"),
    "Full-Stack & Web": ("full stack", "full-stack", "frontend", "front-end", "backend", "back-end", "web developer", "react", "node.js", "web application"),
    "Cloud & DevOps": ("devops", "site reliability", "sre", "cloud engineer", "kubernetes", "terraform", "platform engineer"),
    "Cybersecurity": ("cybersecurity", "security engineer", "penetration test", "soc analyst", "information security"),
    "Embedded & Systems": ("embedded software", "embedded systems", "firmware", "operating systems", "systems engineer", "rtos"),
    "CAD/CAM & Product Design": ("cad/cam", "autocad", "solidworks", "catia", "product design", "gd&t"),
    "Robotics & Mechatronics": ("robotics", "robotic", "mechatronics", "motion control"),
    "HVAC & Thermal Systems": ("hvac", "thermal", "heat transfer", "refrigeration"),
    "Manufacturing & Quality": ("manufacturing", "quality engineer", "six sigma", "lean manufacturing", "production engineer"),
    "Automotive & EV": ("automotive", "electric vehicle", "\bev\b", "vehicle dynamics", "automotive design"),
    "Structural Design": ("structural", "staad", "structural design", "bridge engineer"),
    "Construction Management": ("construction manager", "construction management", "site engineer", "project engineer"),
    "Transportation & Infrastructure": ("transportation", "highway", "railway", "infrastructure", "traffic engineer"),
    "Geotechnical & Environmental": ("geotechnical", "environmental engineer", "soil mechanics", "hydrology"),
    "BIM & Urban Planning": ("bim", "revit", "urban planning", "town planner"),
    "VLSI & Semiconductors": ("vlsi", "semiconductor", "asic", "fpga", "verilog", "chip design"),
    "Power Systems & Smart Grid": ("power system", "smart grid", "power distribution", "etap", "renewable energy"),
    "Control & Instrumentation": ("control systems", "instrumentation", "plc", "scada", "automation controls"),
    "Embedded Hardware & IoT": ("embedded hardware", "iot", "internet of things", "pcb design", "embedded c"),
    "Telecommunications": ("telecommunications", "telecom", "5g", "rf engineer", "wireless network"),
    "Process Engineering": ("process engineer", "process engineering", "process design", "hysys"),
    "Petrochemicals & Energy": ("petrochemical", "oil and gas", "refinery", "energy engineer"),
    "Pharmaceuticals & Biotech": ("pharma", "pharmaceutical", "biotech", "bioprocess", "clinical manufacturing"),
    "Materials & Polymers": ("materials engineer", "polymer", "materials science", "composites"),
    "Aerodynamics & Propulsion": ("aerodynamics", "propulsion", "flight dynamics", "turbine"),
    "Avionics": ("avionics", "aircraft electronics", "flight control systems"),
    "EV Powertrain": ("ev powertrain", "electric powertrain", "battery management", "traction motor"),
    "Vehicle Dynamics": ("vehicle dynamics", "chassis", "suspension design"),
    "Supply Chain & Operations": ("supply chain", "operations research", "logistics", "procurement"),
    "Quality Assurance & Six Sigma": ("quality assurance", "six sigma", "quality control", "iso 9001"),
    "Plant & Process Automation": ("plant automation", "process automation", "scada", "plc", "industrial automation"),
}

COUNTRY_ALIASES: dict[str, str] = {
    "india": "India", "bharat": "India", "singapore": "Singapore", "australia": "Australia",
    "new zealand": "New Zealand", "japan": "Japan", "china": "China", "hong kong": "Hong Kong",
    "south korea": "South Korea", "korea": "South Korea", "indonesia": "Indonesia", "malaysia": "Malaysia",
    "thailand": "Thailand", "philippines": "Philippines", "vietnam": "Vietnam", "taiwan": "Taiwan",
    "germany": "Germany", "united kingdom": "United Kingdom", "uk": "United Kingdom", "britain": "United Kingdom",
    "ireland": "Ireland", "france": "France", "spain": "Spain", "italy": "Italy", "netherlands": "Netherlands",
    "sweden": "Sweden", "norway": "Norway", "denmark": "Denmark", "switzerland": "Switzerland", "poland": "Poland",
    "united states": "United States", "usa": "United States", "us": "United States", "canada": "Canada", "mexico": "Mexico",
    "uae": "UAE", "united arab emirates": "UAE", "dubai": "UAE", "abu dhabi": "UAE", "saudi arabia": "Saudi Arabia",
    "qatar": "Qatar", "israel": "Israel", "turkey": "Türkiye", "turkiye": "Türkiye", "egypt": "Egypt",
    "south africa": "South Africa", "brazil": "Brazil",
}

COUNTRY_REGIONS: dict[str, str] = {
    "India": "India",
    **{country: "APAC" for country in ("Singapore", "Australia", "New Zealand", "Japan", "China", "Hong Kong", "South Korea", "Indonesia", "Malaysia", "Thailand", "Philippines", "Vietnam", "Taiwan")},
    **{country: "Europe" for country in ("Germany", "United Kingdom", "Ireland", "France", "Spain", "Italy", "Netherlands", "Sweden", "Norway", "Denmark", "Switzerland", "Poland")},
    **{country: "North America" for country in ("United States", "Canada", "Mexico")},
    **{country: "Middle East" for country in ("UAE", "Saudi Arabia", "Qatar", "Israel", "Türkiye", "Egypt")},
}


def extract_canonical_skills(text: str) -> list[str]:
    """Return canonical skills found in text, preserving dictionary order."""
    return [name for name, patterns in CANONICAL_SKILL_DICTIONARY.items() if any(re.search(pattern, text, re.I) for pattern in patterns)]


def classify_engineering(title: str, description: str) -> tuple[str, str]:
    """Map role text to one branch/domain pair, preferring specific signals."""
    text = f"{title} {description}".casefold()
    branch = next((name for name, words in BRANCH_KEYWORDS if any(word in text for word in words)), "Computer Science & IT")
    domains = ENGINEERING_TAXONOMY[branch]
    domain = next((name for name in domains if any(word in text for word in DOMAIN_KEYWORDS[name])), domains[0])
    return branch, domain


def normalize_country(value: Any, location: str = "") -> str:
    """Resolve country aliases and common city names from supplied geo text."""
    text = f"{value or ''} {location or ''}".casefold()
    for alias in sorted(COUNTRY_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", text):
            return COUNTRY_ALIASES[alias]
    cities = {
        "bengaluru": "India", "bangalore": "India", "mumbai": "India", "delhi": "India", "hyderabad": "India",
        "san francisco": "United States", "new york": "United States", "seattle": "United States", "austin": "United States",
        "toronto": "Canada", "vancouver": "Canada", "london": "United Kingdom", "berlin": "Germany",
        "paris": "France", "amsterdam": "Netherlands", "dublin": "Ireland", "sydney": "Australia", "melbourne": "Australia",
    }
    for city, country in cities.items():
        if city in text:
            return country
    return str(value).strip() if value else "Unknown"


def classify_region_country(location: str = "", country: str = "", work_mode: str = "") -> tuple[str, str]:
    """Normalize country and assign one of the API's six supported regions."""
    normalized_country = normalize_country(country, location)
    region = COUNTRY_REGIONS.get(normalized_country)
    if region:
        return region, normalized_country
    text = f"{location} {country}".casefold()
    if any(token in text for token in ("remote", "worldwide", "global", "anywhere")) or work_mode.casefold() == "remote":
        return "Global/Remote", normalized_country
    return "Global/Remote", normalized_country


def classify_job(title: str, description: str, location: str = "", country: str = "", work_mode: str = "") -> dict[str, str]:
    """Classify job branch, domain, region, and country for ETL persistence."""
    branch, domain = classify_engineering(title, description)
    region, country_name = classify_region_country(location, country, work_mode)
    return {"engineering_branch": branch, "domain": domain, "region": region, "country": country_name}
