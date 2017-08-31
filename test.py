import unittest
from bakery import *

#--------------------------------------------------------------------
def create_test_graph():
    """
        A
        |\
        | C  L
        |  \  \ 
     K  B   M  F
      \  \ /__/|
       D  E    |
      /  / \   |
     G  H   I  J
    """
    return {
        'A':        ['C', 'B'],
        'B':        ['D', 'E'],
        'C':        ['M', 'F'],
        'D':        ['G'],
        'E':        ['H', 'I'],
        'F':        ['E', 'J'],
        'G':        [],
        'H':        [],
        'I':        [],
        'J':        [],
        'K':        ['D'],
        'L':        ['F'],
        'M':        ['C']
    }

#--------------------------------------------------------------------
class EvaluateTests(unittest.TestCase):
