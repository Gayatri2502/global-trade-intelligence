import unittest
from run import extract, canonical
class ExtractionTests(unittest.TestCase):
 def test_public_contacts(self):
  lead,_=extract('https://example.com/contact','<title>Example Trade</title><p>Moringa exporter</p><a href="mailto:sales@example.com">Email</a><a href="tel:+911234567890">Call</a><a href="https://instagram.com/example">Instagram</a>',{})
  self.assertEqual(lead['email'],'sales@example.com');self.assertEqual(lead['phone'],'+911234567890');self.assertEqual(lead['status'],'Unverified');self.assertEqual(len(lead['social_urls']),1)
 def test_dedup_domain(self):
  a,_=extract('https://example.com/','<p>info@example.com</p>',{});b,_=extract('https://example.com/contact','<p>info@example.com</p>',{});self.assertEqual(a['lead_id'],b['lead_id'])
 def test_block_page(self):
  with self.assertRaises(ValueError):extract('https://example.com','Verify you are human CAPTCHA',{})
 def test_no_number_guessing(self):
  lead,_=extract('https://example.com','<p>Export 1234567890 tonnes. Year 2026.</p>',{});self.assertIsNone(lead)
if __name__=='__main__':unittest.main()
