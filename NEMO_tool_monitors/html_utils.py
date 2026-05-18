import re
from typing import Optional

_HREF_ATTR_RE = re.compile(
    r"""(<a\s[^>]*\bhref\s*=\s*)(['"])(.*?)\2""",
    re.IGNORECASE | re.DOTALL,
)


def normalize_external_href(href: str) -> str:
    """Turn bare domains (e.g. google.com) into absolute https URLs."""
    href = (href or "").strip()
    if not href:
        return href
    lower = href.lower()
    if lower.startswith(("#", "/", "mailto:", "tel:", "javascript:", "data:")):
        return href
    if lower.startswith("//") or lower.startswith("http://") or lower.startswith("https://"):
        return href
    host = href.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if "." in host and not host.startswith("."):
        return f"https://{href}"
    return href


def normalize_description_links(html: Optional[str]) -> str:
    """Fix anchor hrefs in monitor description HTML so bare domains are absolute."""
    if not html:
        return ""

    def replace_href(match: re.Match) -> str:
        prefix, quote, href = match.group(1), match.group(2), match.group(3)
        return f"{prefix}{quote}{normalize_external_href(href)}{quote}"

    return _HREF_ATTR_RE.sub(replace_href, html)
