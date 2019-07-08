#!/usr/bin/env python

import sys

from gsp import GSP
from nautilusbb import Nautilusbb
from util import argmax_index


class Lowbid(Nautilusbb):
    """Balanced bidding agent"""
    TOTALROUNDS = 48
    RANGE = 9

    def __init__(self, id, value, budget):
        super(Lowbid, self).__init__(id,value, budget)

    def initial_bid(self, reserve):
        return self.value / 2

    def bid(self, t, history, reserve):
        # we bid nothing on low click through rates (lowest clicks occur on )
        midpoint = self.TOTALROUNDS/2
        error = self.RANGE
        if abs(t - midpoint) <= error:
            return 0
        else: 
            return super(Lowbid, self).bid(t,history, reserve)

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


