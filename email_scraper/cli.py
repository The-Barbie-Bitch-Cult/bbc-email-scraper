from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import time
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib import parse, request, robotparser
from urllib.error import HTTPError, URLError


DEFAULT_USER_AGENT = "email-scraper/0.1 (+https://example.invalid/email-scraper)"
RESET = "\033[0m"
PINK = "\033[95m"
MAGENTA = "\033[35m"
CYAN = "\033[96m"
INTERACTIVE_BANNER = (
    "\n"
    "============================================================\n"
    f"{PINK}"
    "██████   █████  ██████  ██████  ██ ███████\n"
    "██   ██ ██   ██ ██   ██ ██   ██ ██ ██\n"
    "██████  ███████ ██████  ██████  ██ █████\n"
    "██   ██ ██   ██ ██   ██ ██   ██ ██ ██\n"
    "██████  ██   ██ ██   ██ ██████  ██ ███████\n"
    f"{MAGENTA}"
    "██████  ██ ████████  ██████ ██   ██\n"
    "██   ██ ██    ██    ██      ██   ██\n"
    "██████  ██    ██    ██      ███████\n"
    "██   ██ ██    ██    ██      ██   ██\n"
    "██████  ██    ██     ██████ ██   ██\n"
    f"{CYAN}"
    " ██████ ██    ██ ██      ████████\n"
    "██      ██    ██ ██         ██\n"
    "██      ██    ██ ██         ██\n"
    "██      ██    ██ ██         ██\n"
    " ██████  ██████  ███████    ██\n"
    f"{RESET}"
    "\n"
    "        Barbie Bitch Cult - Email Scraper\n"
    "============================================================\n"
)
EMAIL_PATTERN = re.compile(
    r"(?<![A-Z0-9._%+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![A-Z0-9._%+-])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    email: str
    source_url: str
    discovery_type: str


@dataclass(frozen=True)
class FetchResult:
    url: str
    body: str
    content_type: str


class LinkAndTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return

        if tag == "a":
            for name, value in attrs:
                if name.lower() == "href" and value:
                    self.links.append(html.unescape(value.strip()))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.text_parts.append(data)

    @property
    def visible_text(self) -> str:
        return " ".join(part.strip() for part in self.text_parts if part.strip())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="email-scraper",
        description="Crawl a domain and export linked or exposed email addresses to CSV. Run without a URL for interactive mode.",
    )
    parser.add_argument("url", nargs="?", help="Starting URL or domain, for example https://example.com")
    parser.add_argument("-o", "--output", default="emails.csv", help="CSV output path")
    parser.add_argument("--max-pages", type=positive_int, default=100, help="Maximum HTML pages to crawl")
    parser.add_argument("--max-bytes", type=positive_int, default=2_000_000, help="Maximum bytes to read per page")
    parser.add_argument("--delay", type=non_negative_float, default=0.2, help="Delay between requests in seconds")
    parser.add_argument("--timeout", type=positive_float, default=10.0, help="HTTP timeout in seconds")
    parser.add_argument("--include-subdomains", action="store_true", help="Allow subdomains of the starting domain")
    parser.add_argument(
        "--ignore-robots",
        "--no-robots",
        dest="ignore_robots",
        action="store_true",
        help="Do not check robots.txt",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent header")
    parser.add_argument("--verbose", action="store_true", help="Print crawl progress to stderr")
    return parser.parse_args(argv)


def prompt_interactive(args: argparse.Namespace) -> argparse.Namespace:
    print(INTERACTIVE_BANNER, flush=True)
    print("Press Enter to use the value shown in brackets.", flush=True)
    print(flush=True)

    args.url = prompt_required("Website URL or domain")
    args.output = prompt_text("CSV output file", args.output)
    args.max_pages = prompt_value("Maximum pages to crawl", args.max_pages, positive_int)
    args.max_bytes = prompt_value("Maximum bytes to read per page", args.max_bytes, positive_int)
    args.delay = prompt_value("Delay between requests in seconds", args.delay, non_negative_float)
    args.timeout = prompt_value("HTTP timeout in seconds", args.timeout, positive_float)
    args.include_subdomains = prompt_bool("Include subdomains", args.include_subdomains)
    respect_robots = prompt_bool("Honor robots.txt", not args.ignore_robots)
    args.ignore_robots = not respect_robots
    args.user_agent = prompt_text("User-Agent", args.user_agent)
    args.verbose = prompt_bool("Show progress while running", args.verbose)
    print()
    return args


def prompt_required(label: str) -> str:
    while True:
        value = prompt_input(f"{label}: ").strip()
        if value:
            return value
        print("Please enter a value.", flush=True)


def prompt_text(label: str, default: str) -> str:
    value = prompt_input(f"{label} [{default}]: ").strip()
    return value or default


def prompt_value(label: str, default, parser):
    while True:
        value = prompt_input(f"{label} [{default}]: ").strip()
        if not value:
            return default
        try:
            return parser(value)
        except (ValueError, argparse.ArgumentTypeError) as exc:
            print(f"Invalid value: {exc}", flush=True)


def prompt_bool(label: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        value = prompt_input(f"{label}? [{suffix}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter y or n.", flush=True)


def prompt_input(prompt: str) -> str:
    print(prompt, end="", flush=True)
    return input()


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def normalize_start_url(raw_url: str) -> str:
    if "://" not in raw_url:
        raw_url = f"https://{raw_url}"

    parsed = parse.urlsplit(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("start URL must be an HTTP or HTTPS URL")

    path = parsed.path or "/"
    return parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def normalize_url(url: str) -> str:
    parsed = parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return parse.urlunsplit((scheme, netloc, path, parsed.query, ""))


def is_html_link(url: str) -> bool:
    path = parse.urlsplit(url).path.lower()
    blocked_extensions = {
        ".7z",
        ".avi",
        ".css",
        ".doc",
        ".docx",
        ".gif",
        ".gz",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".ppt",
        ".pptx",
        ".rar",
        ".svg",
        ".tar",
        ".webp",
        ".xls",
        ".xlsx",
        ".xml",
        ".zip",
    }
    return not any(path.endswith(extension) for extension in blocked_extensions)


def root_for_subdomain_matching(hostname: str) -> str:
    hostname = hostname.lower()
    return hostname[4:] if hostname.startswith("www.") else hostname


def is_in_scope(url: str, start_host: str, include_subdomains: bool) -> bool:
    parsed = parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    host = (parsed.hostname or "").lower()
    start_host = start_host.lower()
    if host == start_host:
        return True

    if not include_subdomains:
        return False

    root = root_for_subdomain_matching(start_host)
    return host == root or host.endswith(f".{root}")


def make_robot_parser(start_url: str, user_agent: str, verbose: bool) -> robotparser.RobotFileParser | None:
    parsed = parse.urlsplit(start_url)
    robots_url = parse.urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    robots = robotparser.RobotFileParser()
    robots.set_url(robots_url)
    try:
        robots.read()
    except Exception as exc:  # robotparser can raise several urllib and parsing exceptions.
        if verbose:
            print(f"robots: could not read {robots_url}: {exc}", file=sys.stderr)
        return None
    if verbose:
        print(f"robots: loaded {robots_url}", file=sys.stderr)
    return robots


def can_fetch(robots: robotparser.RobotFileParser | None, user_agent: str, url: str) -> bool:
    if robots is None:
        return True
    return robots.can_fetch(user_agent, url)


def fetch_url(url: str, user_agent: str, timeout: float, max_bytes: int) -> FetchResult | None:
    req = request.Request(url, headers={"User-Agent": user_agent})
    try:
        with request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                return None
            body_bytes = response.read(max_bytes + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None

    if len(body_bytes) > max_bytes:
        body_bytes = body_bytes[:max_bytes]

    encoding = response_encoding(content_type) or "utf-8"
    body = body_bytes.decode(encoding, errors="replace")
    return FetchResult(url=url, body=body, content_type=content_type)


def response_encoding(content_type: str) -> str | None:
    match = re.search(r"charset=([^;\s]+)", content_type, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip("\"'")


def extract_emails(text: str) -> set[str]:
    emails: set[str] = set()
    for match in EMAIL_PATTERN.finditer(text):
        email = match.group(1).strip().strip(".,;:)]}>\"'").lower()
        if is_plausible_email(email):
            emails.add(email)
    return emails


def extract_mailto_emails(href: str) -> set[str]:
    if not href.lower().startswith("mailto:"):
        return set()

    mailto_target = href[7:].split("?", 1)[0]
    decoded = parse.unquote(mailto_target)
    return extract_emails(decoded)


def is_plausible_email(email: str) -> bool:
    local, _, domain = email.partition("@")
    if not local or not domain or ".." in email:
        return False
    if domain.startswith("-") or domain.endswith("-"):
        return False
    return "." in domain


def parse_page(result: FetchResult) -> tuple[set[Finding], list[str]]:
    parser = LinkAndTextParser()
    parser.feed(result.body)

    findings: set[Finding] = set()
    for email_address in extract_emails(parser.visible_text):
        findings.add(Finding(email=email_address, source_url=result.url, discovery_type="text"))

    for href in parser.links:
        for email_address in extract_mailto_emails(href):
            findings.add(Finding(email=email_address, source_url=result.url, discovery_type="mailto"))
        if not href.lower().startswith("mailto:"):
            for email_address in extract_emails(parse.unquote(href)):
                findings.add(Finding(email=email_address, source_url=result.url, discovery_type="link"))

    return findings, parser.links


def discover_links(
    links: Iterable[str],
    base_url: str,
    start_host: str,
    include_subdomains: bool,
) -> list[str]:
    discovered: list[str] = []
    for link in links:
        if has_invalid_url_chars(link):
            continue
        if link.lower().startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue

        absolute = parse.urljoin(base_url, link)
        if has_invalid_url_chars(absolute):
            continue
        normalized = normalize_url(absolute)
        if is_in_scope(normalized, start_host, include_subdomains) and is_html_link(normalized):
            discovered.append(normalized)
    return discovered


def has_invalid_url_chars(url: str) -> bool:
    return any(ord(char) <= 32 for char in url)


def crawl(
    start_url: str,
    output_path: str,
    max_pages: int,
    max_bytes: int,
    delay: float,
    timeout: float,
    include_subdomains: bool,
    respect_robots: bool,
    user_agent: str,
    verbose: bool,
) -> int:
    start_host = parse.urlsplit(start_url).hostname or ""
    robots = None if not respect_robots else make_robot_parser(start_url, user_agent, verbose)

    queue: deque[str] = deque([start_url])
    queued = {start_url}
    visited: set[str] = set()
    findings: set[Finding] = set()

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue

        if not can_fetch(robots, user_agent, url):
            if verbose:
                print(f"skip robots: {url}", file=sys.stderr)
            visited.add(url)
            continue

        if verbose:
            print(f"fetch: {url}", file=sys.stderr)

        result = fetch_url(url, user_agent, timeout, max_bytes)
        visited.add(url)
        if result is None:
            continue

        page_findings, links = parse_page(result)
        findings.update(page_findings)

        for link in discover_links(links, result.url, start_host, include_subdomains):
            if link not in visited and link not in queued:
                queue.append(link)
                queued.add(link)

        if delay > 0 and queue and len(visited) < max_pages:
            time.sleep(delay)

    write_csv(output_path, findings)
    if verbose:
        print(f"done: crawled={len(visited)} findings={len(findings)} output={output_path}", file=sys.stderr)
    return len(findings)


def write_csv(output_path: str, findings: set[Finding]) -> None:
    rows = sorted(findings, key=lambda item: (item.email, item.source_url, item.discovery_type))
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["email", "source_url", "discovery_type"])
        writer.writeheader()
        for finding in rows:
            writer.writerow(
                {
                    "email": finding.email,
                    "source_url": finding.source_url,
                    "discovery_type": finding.discovery_type,
                }
            )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.url is None:
            args = prompt_interactive(args)
        start_url = normalize_start_url(args.url)
        crawl(
            start_url=start_url,
            output_path=args.output,
            max_pages=args.max_pages,
            max_bytes=args.max_bytes,
            delay=args.delay,
            timeout=args.timeout,
            include_subdomains=args.include_subdomains,
            respect_robots=not args.ignore_robots,
            user_agent=args.user_agent,
            verbose=args.verbose,
        )
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except EOFError:
        print("error: interactive mode needs a terminal that can accept typed answers", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
