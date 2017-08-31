#--------------------------------------------------------------------
# bakery.evaluate: Logic for evaluating targets in builds.
#
# Author: Lain Supe (supelee)
# Date: Wednesday, June 7th 2017
#--------------------------------------------------------------------

import collections

from .work import *
from .error import *
from .log import *

#--------------------------------------------------------------------
class EvaluationError(BuildError):
    pass

#--------------------------------------------------------------------
class EvaluationDecider:
    def get_evaluation_set(self, injector, target, higher_eval_set = None):
        raise NotImplementedError()

    def evaluate(self, injector, target):
        raise NotImplementedError()

#--------------------------------------------------------------------
class TaskEvaluator:
    def __init__(self, decider):
        self.decider = decider

    def evaluate(self, injector, targets):
        eval_set = set()
        dep_graph = injector.get_dependency_graph(*targets)
        for target in targets:
            eval_set |= self.decider.get_evaluation_set(injector, target)

        eval_deck = self._calculate_eval_deck(dep_graph, eval_set)
        
        for card_set in eval_deck:
            self._evaluate_card(injector, card_set)
    
    def _evaluate_card(self, injector, card_set):
        for target in card_set:
            self.decider.evaluate(injector, target)

    def _calculate_eval_deck(self, dep_graph, eval_set):
        processed_set = set()
        eval_deck = []
        todo_set = set(eval_set)

        while todo_set:
            card_set = set()
            for target in todo_set:
                todo_deps = {x for x in dep_graph[target] if x in eval_set}
                if all(x in processed_set for x in todo_deps):
                    card_set.add(target)
            if not card_set:
                # This should never happen because of the dependency cycle checks in xeno, but just in case...
                raise EvaluationError('Unable to resolve remaining dependencies for build deck: %s' % repr(todo_set))
            eval_deck.append(card_set)
            processed_set |= card_set
            todo_set ^= card_set
        
        return eval_deck

