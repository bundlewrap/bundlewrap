from unittest import TestCase

from blockwart.concurrency import parallel_method


class ParallelMethodTestHelper(object):
    def __init__(self, id):
        self.id = id

    def example_method(self, *args, **kwargs):
        return {'args': args, 'kwargs': kwargs, 'id': self.id}


class ParallelMethodTest(TestCase):
    """
    Tests blockwart.concurrency.parallel_method.
    """
    def test_usage(self):
        obj_dict = {
            'one': ParallelMethodTestHelper(1),
            'two': ParallelMethodTestHelper(2),
            'three': ParallelMethodTestHelper(3),
        }
        results = parallel_method(
            obj_dict,
            'example_method',
            ('arg1',),
            {'kwarg1': 'kwval1'},
        )
        self.assertEqual(results['one']['id'], 1)
        self.assertEqual(results['two']['args'], ('arg1',))
        self.assertEqual(results['three']['kwargs'], {'kwarg1': 'kwval1'})
