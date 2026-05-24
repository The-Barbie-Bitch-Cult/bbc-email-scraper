import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from email_scraper.cli import (
    FetchResult,
    INTERACTIVE_BANNER,
    crawl,
    extract_emails,
    extract_mailto_emails,
    is_in_scope,
    normalize_start_url,
    parse_args,
    parse_page,
    prompt_interactive,
)


class EmailScraperTests(unittest.TestCase):
    def test_normalize_start_url_adds_https_and_path(self):
        self.assertEqual(normalize_start_url("example.com"), "https://example.com/")

    def test_parse_args_accepts_custom_user_agent(self):
        args = parse_args(["https://example.com", "--user-agent", "CustomBot/1.0"])

        self.assertEqual(args.user_agent, "CustomBot/1.0")

    def test_parse_args_can_disable_robots_checks(self):
        args = parse_args(["https://example.com", "--no-robots"])

        self.assertTrue(args.ignore_robots)

    def test_parse_args_allows_interactive_mode_without_url(self):
        args = parse_args([])

        self.assertIsNone(args.url)

    def test_prompt_interactive_collects_all_options(self):
        args = parse_args([])
        responses = iter(
            [
                "example.com",
                "out.csv",
                "25",
                "500000",
                "0",
                "5",
                "y",
                "n",
                "CustomBot/1.0",
                "y",
            ]
        )

        output = io.StringIO()
        with patch("builtins.input", side_effect=lambda: next(responses)), redirect_stdout(output):
            updated = prompt_interactive(args)

        self.assertIn("Barbie Bitch Cult - Email Scraper", output.getvalue())
        self.assertIn("██████", output.getvalue())
        self.assertIn(INTERACTIVE_BANNER.strip().splitlines()[0], output.getvalue())
        self.assertEqual(updated.url, "example.com")
        self.assertEqual(updated.output, "out.csv")
        self.assertEqual(updated.max_pages, 25)
        self.assertEqual(updated.max_bytes, 500000)
        self.assertEqual(updated.delay, 0)
        self.assertEqual(updated.timeout, 5)
        self.assertTrue(updated.include_subdomains)
        self.assertTrue(updated.ignore_robots)
        self.assertEqual(updated.user_agent, "CustomBot/1.0")
        self.assertTrue(updated.verbose)

    def test_extract_emails_from_text(self):
        self.assertEqual(
            extract_emails("Contact Sales@Example.com or bad..name@example.com"),
            {"sales@example.com"},
        )

    def test_extract_mailto_emails(self):
        self.assertEqual(extract_mailto_emails("mailto:Info@example.com?subject=Hello"), {"info@example.com"})

    def test_parse_page_finds_text_and_mailto_emails(self):
        result = FetchResult(
            url="https://example.com/",
            content_type="text/html",
            body="""
            <html>
              <body>
                <p>Email support@example.com</p>
                <a href="mailto:sales@example.com">Sales</a>
                <a href="/profiles/ops@example.com">Ops</a>
                <script>hidden@example.com</script>
              </body>
            </html>
            """,
        )

        findings, links = parse_page(result)

        self.assertIn("mailto:sales@example.com", links)
        self.assertEqual(
            {finding.email for finding in findings},
            {"support@example.com", "sales@example.com", "ops@example.com"},
        )
        self.assertEqual({finding.discovery_type for finding in findings}, {"text", "mailto", "link"})

    def test_scope_defaults_to_same_host(self):
        self.assertTrue(is_in_scope("https://example.com/about", "example.com", include_subdomains=False))
        self.assertFalse(is_in_scope("https://docs.example.com/about", "example.com", include_subdomains=False))

    def test_scope_can_include_subdomains(self):
        self.assertTrue(is_in_scope("https://docs.example.com/about", "www.example.com", include_subdomains=True))

    def test_crawl_writes_csv_with_mocked_fetch(self):
        pages = {
            "https://example.com/": """
                <html>
                  <body>
                    <p>Contact info@example.com</p>
                    <a href="/team.html">Team</a>
                  </body>
                </html>
            """,
            "https://example.com/team.html": """
                <html>
                  <body><a href="mailto:sales@example.com">Sales</a></body>
                </html>
            """,
        }

        def fake_fetch(url, user_agent, timeout, max_bytes):
            return FetchResult(url=url, body=pages[url], content_type="text/html; charset=utf-8")

        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "emails.csv"
            with patch("email_scraper.cli.fetch_url", side_effect=fake_fetch):
                count = crawl(
                    start_url="https://example.com/",
                    output_path=str(output_path),
                    max_pages=10,
                    max_bytes=1000,
                    delay=0,
                    timeout=1,
                    include_subdomains=False,
                    respect_robots=False,
                    user_agent="test",
                    verbose=False,
                )

            self.assertEqual(count, 2)
            self.assertEqual(
                output_path.read_text(encoding="utf-8").splitlines(),
                [
                    "email,source_url,discovery_type",
                    "info@example.com,https://example.com/,text",
                    "sales@example.com,https://example.com/team.html,mailto",
                ],
            )


if __name__ == "__main__":
    unittest.main()
