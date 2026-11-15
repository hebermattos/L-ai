import unittest
from unittest.mock import MagicMock
from ingest.sitemap import sitemap_urls
from ingest.remote import read_remote_pdf
from ingest.evaluate import evaluate
from ingest.web import SourceRejected

class SitemapTests(unittest.TestCase):
    def test_sitemap_and_index_limits(self):
        fetcher=MagicMock(domains={"example.org"})
        fetcher.get_resource.side_effect=[
            b'<sitemapindex><sitemap><loc>https://example.org/nested.xml</loc></sitemap></sitemapindex>',
            b'<urlset><url><loc>https://example.org/a</loc></url><url><loc>http://127.0.0.1/private</loc></url><url><loc>https://evil.org/b</loc></url></urlset>'
        ]
        self.assertEqual(sitemap_urls(fetcher,["https://example.org/sitemap.xml"]),["https://example.org/a"])
        self.assertEqual(fetcher.get_resource.call_count,2)

    def test_defused_xml(self):
        fetcher=MagicMock(domains={"example.org"})
        fetcher.get_resource.return_value=b'<!DOCTYPE x [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]><urlset><url><loc>&xxe;</loc></url></urlset>'
        with self.assertRaises(Exception):
            sitemap_urls(fetcher,["https://example.org/sitemap.xml"])

    def test_bad_limits(self):
        with self.assertRaises(ValueError):
            sitemap_urls(MagicMock(),[],max_urls=1000)

class RemoteTests(unittest.TestCase):
    def test_pdf_only_url(self):
        with self.assertRaises(SourceRejected):
            read_remote_pdf(MagicMock(domains={"example.org"}),"https://example.org/internal")
    def test_pdf_with_text(self):
        import fitz
        pdf=fitz.open()
        page=pdf.new_page()
        for n in range(8):
            page.insert_text((60,90+n*24),"Technical information about infrastructure and software.")
        data=pdf.tobytes()
        pdf.close()
        f=MagicMock(domains={"example.org"})
        f.get_resource.return_value=data
        doc=read_remote_pdf(f,"https://example.org/library/text.pdf")
        self.assertIn("Page 1",doc.body)
        self.assertEqual(doc.source,"https://example.org/library/text.pdf")

class MetricsTests(unittest.TestCase):
    def test_ranking(self):
        result=evaluate([{"relevant_sources":["b"],"retrieved_sources":["a","b"]},
                         {"relevant_sources":["c"],"retrieved_sources":["a"]}])
        self.assertEqual(result["hit_at_k"],0.5)
        self.assertEqual(result["mrr"],0.25)
