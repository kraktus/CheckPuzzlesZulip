from check_puzzles_zulip import Extractor

import unittest
import datetime


class Test(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.maxDiff = None


if __name__ == "__main__":
    unittest.main()
