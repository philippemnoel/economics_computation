#!/usr/bin/env python

import sys

from gsp import GSP
from nautilusbb import Nautilusbb
from util import argmax_index


class Highend(Nautilusbb):
    """Balanced bidding agent"""
    TOTALROUNDS = 48
    RANGE= 6

    def __init__(self, id, value, budget):
        super(Highend, self).__init__(id,value, budget)

    def bid(self, t, history, reserve):
        # we bid less in the beginning rounds, bid more at the end
        # when other agents are out of money
        midpoint = self.TOTALROUNDS/2
        error = self.RANGE
        if t > self.TOTALROUNDS - self.RANGE:
            return super(Highend, self).bid(t,history, reserve)
        else: 
            return 0.5 * super(Highend, self).bid(t,history, reserve)

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


