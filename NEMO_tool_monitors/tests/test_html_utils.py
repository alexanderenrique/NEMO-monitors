from django.test import SimpleTestCase

from NEMO_tool_monitors.html_utils import normalize_description_links, normalize_external_href


class NormalizeExternalHrefTests(SimpleTestCase):
    def test_bare_domain(self):
        self.assertEqual(normalize_external_href("google.com"), "https://google.com")

    def test_already_absolute(self):
        self.assertEqual(normalize_external_href("https://google.com"), "https://google.com")
        self.assertEqual(normalize_external_href("/local/path"), "/local/path")
        self.assertEqual(normalize_external_href("#section"), "#section")

    def test_relative_path_without_domain(self):
        self.assertEqual(normalize_external_href("docs/page"), "docs/page")


class NormalizeDescriptionLinksTests(SimpleTestCase):
    def test_anchor_with_bare_domain(self):
        html = '<p>See <a href="google.com">Google</a>.</p>'
        self.assertIn('href="https://google.com"', normalize_description_links(html))

    def test_anchor_with_https_unchanged(self):
        html = '<a href="https://example.org">Example</a>'
        self.assertEqual(normalize_description_links(html), html)
