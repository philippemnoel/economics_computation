#!/usr/bin/env python

import sys

from gsp import GSP
from util import argmax_index

class Nautilusbb(object):
    """Balanced bidding agent"""
    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget

    def initial_bid(self, reserve):
        return self.value / 2


    def slot_info(self, t, history, reserve):
        """Compute the following for each slot, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns list of tuples [(slot_id, min_bid, max_bid)], where
        min_bid is the bid needed to tie the other-agent bid for that slot
        in the last round.  If slot_id = 0, max_bid is 2* min_bid.
        Otherwise, it's the next highest min_bid (so bidding between min_bid
        and max_bid would result in ending up in that slot)
        """
        prev_round = history.round(t-1)
        other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)

        clicks = prev_round.clicks
        def compute(s):
            (min, max) = GSP.bid_range_for_slot(s, clicks, reserve, other_bids)
            if max == None:
                max = 2 * min
            return (s, min, max)
            
        info = map(compute, range(len(clicks)))
#        sys.stdout.write("slot info: %s\n" % info)
        return info

    def expected_utils_h(self,info, clicks, value):
        # calculates utility per slot assuming agent has won with bid
        # uses clicks and info[i][2] = min_bid for round i
        utility = lambda s: clicks[s]*(value - info[s][1])
        
        # expected utility
        return [utility(slot_id) for (slot_id, _, _) in info]

    def get_clicks(self,t,history):
        return history.round(t-1).clicks

    def expected_utils(self, t, history, reserve, value):
        """
        Figure out the expected utility of bidding such that we win each
        slot, assuming that everyone else keeps their bids constant from
        the previous round.

        returns a list of tuples (slot_id, utility) per slot.
        """
        # info contains (slot_id, min_bid, max_bid) so if we bid 
        # min_bid <= b <= max_bid we win slot_id
        info = self.slot_info(t,history, reserve)
        clicks = self.get_clicks(t,history)

        utilities = self.expected_utils_h(info, clicks, value)
        
        return utilities

    def target_slot(self, t, history, reserve, value):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        i =  argmax_index(self.expected_utils(t, history, reserve, value))
        info = self.slot_info(t, history, reserve)
        return info[i]

    def bid(self,t,history,reserve):
        return self.bid_value(t,history,reserve,self.value)

    def bid_value(self, t, history, reserve, value):
        # The Balanced bidding strategy (BB) is the strategy for a player j that, given
        # bids b_{-j},
        # - targets the slot s*_j which maximizes his utility, that is,
        # s*_j = argmax_s {clicks_s (v_j - p_s(j))}.
        # - chooses his bid b' for the next round so as to
        # satisfy the following equation:
        # clicks_{s*_j} (v_j - p_{s*_j}(j)) = clicks_{s*_j-1}(v_j - b')
        # (p_x is the price/click in slot x)
        # If s*_j is the top slot, bid the value v_j
        prev_round = history.round(t-1)

        bid = 0  # change this
        info = self.target_slot(t,history,reserve, value)

        min_bid = info[1]
        c = [float(x) for x in self.get_clicks(t,history)]
        k = info[0]
        p = min_bid

        # written for clarity
        if p >= value:
            bid = value
        elif k > 0:
            # use click ratio as a measure of quality ratio
            bid = value - (c[k]/c[k-1]) * (value - p)
        else:
            bid = value

        return bid

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, value)


