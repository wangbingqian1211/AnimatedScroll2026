import unittest
from backend.revisions import node

class ZeroRevisionTests(unittest.TestCase):
    def setUp(self):
        self.w={'entities':{'material:main':{'revision':3,'published':{'text':'latest'},'refs':[]}},'revisionArchive':{'material:main':{'1':{'data':{'text':'first'},'refs':[]}}}}
    def test_placeholder_uses_first_publication(self):
        self.assertEqual(node(self.w,'material:main',0)['data']['text'],'first')
    def test_missing_real_revision_still_fails(self):
        with self.assertRaises(ValueError):node(self.w,'material:main',2)
    def test_unpublished_dependency_still_fails(self):
        self.w['revisionArchive']={}
        self.w['entities']['material:main'].update(revision=0,published=None)
        with self.assertRaises(ValueError):node(self.w,'material:main',0)
