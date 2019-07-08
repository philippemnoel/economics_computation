#!/usr/bin/env python

import logging
from pprint import pformat

class Stats:
    def __init__(self, history, values):
        self.history = history
        self.values = values  # dict id->value

    def util_in_round(self,id,t):
        round = self.history.round(t)
        if id not in round.occupants:
            # Didn't get a slot in this round
            return 0
        slot = round.occupants.index(id)
        return round.clicks[slot] * (
            self.values[id] - round.per_click_payments[slot])

    def total_utility(self, id, verbose=False):
        

        rounds = self.history.num_rounds()
        if(verbose):
            logging.info("%d: utils: %s\n" % (id, str(list(self.util(id,t) for t in range(rounds)))))
            logging.info("%d: value = %s" % (id, self.values[id]))
        
        return sum(self.util_in_round(id,t) for t in range(rounds))

    def revenue_in_round(self, t):
        r = self.history.round(t)
        rev = sum(r.slot_payments)
        return rev

    def total_revenue(self):
        rev = 0
        def slot_payments(slot_clicks, per_click_payments):
            return map(lambda (x,y): x*y,
                       zip(slot_clicks, per_click_payments))

        for i in range(self.history.num_rounds()):
            rev += self.revenue_in_round(i)

        return rev

    def __repr__(self):
        return "Stats(history with %d rounds, vals %s)" % (
            self.history.last_round() + 1,
            str(self.values))
