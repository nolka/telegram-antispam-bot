import unittest

from views.custom_filters import escape


class TestCustomFilters(unittest.TestCase):
    def test_escape(self):
        content = 'Some.Text(["🚁","🏍"]'
        expected = r'Some\.Text\(\["🚁"\,"🏍"\]'

        self.assertEqual(expected, escape(content))
