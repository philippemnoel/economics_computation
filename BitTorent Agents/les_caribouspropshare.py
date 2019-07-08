#!/usr/bin/python
# Philippe Noel & Laurentiu Calancea
# BitTorent PropShare Client, as defined in Pset PDF
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
################################################################################
class Les_caribousPropShare(Peer):
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
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
    # update this function to allocate bandwith propertionaly to the fraction of
    # the total received from the previous round from all peers
    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds
        returns: list of Upload objects.
        In each round, this will be called after requests().
        """
        round = history.current_round()
        # round 0 / no request -- we return here for simplicity
        if len(requests) == 0:
            chosen, bws = [], [] # nothing to return
            # upload nothing and return nothing (for closure)
            uploads = [Upload(self.id, peer_id, bw)
                       for (peer_id, bw) in zip(chosen, bws)]
            return uploads # should always return []
        # round 1 or more, or with requests
        else:
            # get list of peers requesting pieces this round
            requesters = set() # set so we don't have duplicates
            for request in requests:
                requesters.add(request.requester_id)
            # each of the curr requesters and how much they uploaded last round
            requesters_breakdown_last_round = dict()
            # peers we will unchoke next because they uploaded to us last time
            to_unchoke = set()
            # total of how much curr requesters uploaded last round
            requesters_total_last_round = 0
            # loop over all the downloads we received to find total and partials
            for download in history.downloads[round - 1]:
                # info for the current download peer
                id, blocks = download.from_id, download.blocks
                # if this peer uploaded to us last round and requests now
                if id in requesters:
                    to_unchoke.add(id) # uploaded, we will unchoke next round
                    requesters_total_last_round += download.blocks
                    # keep track of breakdown for proportional bandwith
                    if id not in requesters_breakdown_last_round:
                        requesters_breakdown_last_round[id] = blocks
                    else:
                        requesters_breakdown_last_round[id] += blocks
            # we have who to unchoke, now figure out their bandwiths
            # formula: last_round_upload from this requester / total_last_round_upload from curr requesters
            bws, chosen = [], [] # also get peers as list for zipping
            for id in to_unchoke:
                # get how much this peer uploaded last round
                blocks = requesters_breakdown_last_round[id]
                # 90% of our bandwith this way and 10% optimistic unchoking
                bws.append(int(self.up_bw * 0.90 * (blocks / float(requesters_total_last_round))))
                chosen.append(id)
            # now we just have 10% optimistic unchoking to do
            # more requesters than unchoke, there are some potential peers for optimistic unchoking
            if len(requesters) > len(to_unchoke):
                # peers that are not unchoked
                potential_optimistic_peers = requesters.difference(to_unchoke)
                # pick any of them at random
                optimistic_peer = random.sample(potential_optimistic_peers, 1)[0]
                # add to bws & chosen
                bws.append(int(0.10 * self.up_bw)) # 10% reserved for optimistic unchoking
                chosen.append(optimistic_peer)
        # upload and return
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
        return uploads
