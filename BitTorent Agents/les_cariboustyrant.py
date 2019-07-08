#!/usr/bin/python
# Philippe Noel & Laurentiu Calancea
# BitTorent Tyrant Client, as defined in Chapter 5 of the book
import math
import random
import logging
from messages import Upload, Request
from util import even_split
from peer import Peer
############################## Helper functions ################################
# counts the number of each needed pieces (for rarest first implementation)
def count_pieces(needed_pieces, peers):
    countdict = dict() # pieces count {piece_id: count}
    # loop over all peers
    for peer in peers:
        # for each peer, loop over all their pieces
        for piece in peer.available_pieces:
            # if one of these is needed, add to our dictionary
            if piece in needed_pieces:
                if piece not in countdict:
                    countdict[piece] = 1
                else:
                    countdict[piece] += 1
    # if the dict is still empty, then there are no needed pieces available
    if countdict == dict():
        return []
    # else there are and we return their count
    else:
        # we convert to list for easier sorting & accessing
        # we will put all same count in a list to shuffle for symmetry breaking
        invertdict = dict()
        for piece_id, piece_count in countdict.iteritems():
            if piece_count not in invertdict:
                invertdict[piece_count] = [piece_id]
            else:
                invertdict[piece_count].append(piece_id)
        # convert to list and sort by number
        sorted_pieces = []
        for piece_count, piece_id_lst in invertdict.iteritems():
            sorted_pieces.append((piece_count, piece_id_lst))
        sorted_pieces.sort(key=lambda tup: tup[0])
        # list of tuples (piece_count, piece_id_list), increasing count
        return sorted_pieces

# updates peers based on Algorithm 5.2 - Chapter 5, step 5
def update_prev_unchoked_peers(self, round, history, alpha, gamma, r, peers):
    # we have 3 cases, a, b, c
    for id in self.unchoked_peers:
        # case a) - peer j did not unchoke peer i, so unchoke counter == 0
        if self.previously_unchoked_peers_counter[id] == 0:
            self.expected_threshold_rate[id] *= 1.0 + alpha
            # have_messages function for expected bw from page 117
            have_messages = 0
            for peer in peers:
                if peer.id == id:
                    have_messages = len(peer.available_pieces)
            self.download_rate_estimates[id] =  float(have_messages / 4.0)
        # case b) and c), peer j did unchoke peer i, so unchoke counter > 0
        else:
            # we first get the total amount of download received last round
            # from this peer, we reciprocate with observed rate (5.2 - 5b)
            for download in history.downloads[round - 1]:
                if download.from_id == id:
                    self.estimate_download_rate += download.blocks
            # case c), unchoked for >= r periods, decrease by gamma
            if self.previously_unchoked_peers_counter[id] >= r:
                self.expected_threshold_rate[id] *= 1.0 - gamma
    # return nothing -- we're updating in the class
################################################################################
class Les_caribousTyrant(Peer):
    # adding additional book-keeping procedures to keep track of everything
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        # additional accounting & book-keeping procedures proposed in chapter
        # we have them here to have continuity over the rounds more easily
        # keep estimate and thresold for each peer and from each peer to handle reciprocation
        self.estimate_download_rate = dict() # f_ji
        self.expected_threshold_rate = dict() # T_j
        self.num_slots = 0 # dynamically update the number of unchoke slots we have
        # keep track of who peers that we previously unchoked in previous r rounds
        # format: {peer_id: number_of_times_unchoked_in_previous_r_rounds}
        self.previously_unchoked_peers_counter = dict()
        # peers unchoked in the last round (need to keep track for updating
        # according to 5. in Algorithm 5.2 - Chapter 5)
        self.unchoked_peers = set()
    # same as in reference client (Les_caribousStd) & same helper function
    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see
        returns: a list of Request() objects
        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = filter(needed, range(len(self.pieces)))
        np_set = set(needed_pieces)  # sets support fast intersection ops.
        requests = [] # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        # id sorting useless, we shuffle insteas for symmetry breaking
        random.shuffle(peers)
        # let's now find the rarest pieces
        # this is a list
        rarest_first_needed_pieces = count_pieces(needed_pieces, peers)
        # sanity check
        if rarest_first_needed_pieces == []:
            return requests # no needed pieces available
        # loop over all our pieces, rarest first
        for piece_count, piece_id_lst in rarest_first_needed_pieces:
            # let's shuffle so we don't always pick the same pieces (we had
            # problems before were all peers always wanted the same pieces)
            random.shuffle(piece_id_lst)
            # loop over all out pieces and request
            for piece_id in piece_id_lst:
                # request all available pieces from all peers!
                # (up to self.max_requests from each)
                for peer in peers:
                    av_set = set(peer.available_pieces)
                    isect = av_set.intersection(np_set)
                    n = min(self.max_requests, len(isect))
                    # if n >= 0, we still have requests we can make
                    if n > 0:
                        if piece_id in av_set:
                            start_block = self.pieces[piece_id]
                            r = Request(self.id, peer.id, piece_id, start_block)
                            requests.append(r)
                            n -= 1 # one more request done
        # done!!
        return requests
    # updating this function with strategic unchoking BitTyrant algorithm
    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds
        returns: list of Upload objects.
        In each round, this will be called after requests().
        """
        round = history.current_round()
        # parameters (taken from BitTyrant algorithm -- Chapter 5)
        alpha = 0.20
        gamma = 0.10
        r = 3
        bw_capacity = self.up_bw # initial bandwith per round
        # resetting our unchoked peers set everytime (since we only consider
        # last round)
        self.unchoked_peers = set()
        # get list of peers requesting pieces this round
        requesters = set() # set so we don't have duplicates
        for request in requests:
            requesters.add(request.requester_id)
        # final bandwiths and chosen peers to unchoke
        bws, chosen = [], []
        # round 0, initialization round
        if len(requests) == 0:
            chosen, bws = [], []
            # initialize our book-keeping parameters (to avoid KeyError later)
            for peer in peers:
                # arbitrary number of slots to begin, not super important here
                self.num_slots = int(math.sqrt(self.up_bw))
                # divide evenly across all slots, but really not so important
                self.estimate_download_rate[peer.id] = self.up_bw / float(self.num_slots)
                self.expected_threshold_rate[peer.id] = self.up_bw / float(self.num_slots)
                self.previously_unchoked_peers_counter[peer.id] = 0 # starting round
            # upload nothing, just for closure
            uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            return uploads # should always be []
        # round 1 or more
        else:
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"
            # first, we must update our book-keeping parameters before this
            # round (equivalent to end of last round)
            update_prev_unchoked_peers(self, round, history, alpha, gamma, r, peers)
            # excellent, now we can sort by decreasing ratio (f_ij / T_j)
            requesters_lst = list(requesters) # conversion for sorting
            random.shuffle(requesters_lst) # another symmetry breaking, always good before a big operation
            # decreasing order sorting, per the algorithm
            requesters_lst.sort(key=lambda i: float(self.estimate_download_rate[i] / self.expected_threshold_rate[i]), reverse=True)
            # loop over all our requests
            for requester in requesters_lst:
                # try to assign them a proportional bandwith based on Algorithm 5.2
                curr_bw = self.expected_threshold_rate[requester]
                # if we have enough bandwith left, unchoke them and reduce capacity left
                if curr_bw <= bw_capacity:
                    self.unchoked_peers.add(requester)
                    bw_capacity -= curr_bw
                    bws.append(curr_bw)
                    chosen.append(requester)
            # this is vacuously true, we just define the number of slots to be
            # the number of peers we could unchoke with this bandwith scheme and
            # our maximum bandwith
            self.num_slots = len(self.unchoked_peers)
            # upload everything and return
            uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
        return uploads
