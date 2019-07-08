#!/usr/bin/python
# Philippe Noel & Laurentiu Calancea
# BitTorent Reference Client, assumptions discussed in the writeup
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
class Les_caribousStd(Peer):
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = ["fake"]
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
    # we extend this function with reciprocal upload & optimistic unchoking
    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds
        returns: list of Upload objects.
        In each round, this will be called after requests().
        """
        # Chapter 5 also mentions that we could scale the number of slots by
        # the bandwith of the peer, but for simplicity since this is only the
        # standard client, we leave it at 4
        real_number_unchocked = 4
        number_unchocked = real_number_unchocked - 1
        round = history.current_round()
#        logging.debug("%s again.  It's round %d." % (
#            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.
        #Let's select the people from the history who've helped us the most:
        dict_with_values={}
        for peer in peers:
            dict_with_values[peer.id]=0
        if round > 0:
            for histy in history.downloads[round-1]:
                if histy.to_id==self.id:
                    dict_with_values[histy.from_id]+=histy.blocks
        if round>1:
            for histy in history.downloads[round-2]:
                if histy.to_id==self.id:
                    dict_with_values[histy.from_id]+=histy.blocks
        important_people_list=[]
        for their_id, their_uploads in sorted(dict_with_values.items(), key=lambda x: x[1], reverse=True):
            important_people_list.append(their_id)
        #We are done with selecting the "important people list"
        #We create a list called chosen where we put the people who give us the most
        #Chosen full is the list which contains chosen as well at the optimically unchocked one
        chosen = []
        chosen_full = []
        if len(requests) == 0:
#            logging.debug("No one wants my pieces!")
            bws = []
        else:
#            logging.debug("Still here: uploading to a random peer")
            copy_requests = requests[:]
            copy_number_unchocked = number_unchocked
            set_copy_requests = set()
            for i in range(len(copy_requests)):
                set_copy_requests.add(copy_requests[i].requester_id)
            #Here I just take care of the unchocked people, in our case 3
            #I put then in the chosen list, which is a list exclusive for unchocked people
            if bool(set_copy_requests) and copy_number_unchocked>0:
                for important_person in important_people_list:
                    if copy_number_unchocked>0 and bool(set_copy_requests):
                        if important_person in set_copy_requests:
                            chosen.append(important_person)
                            copy_number_unchocked-=1
                            set_copy_requests = set_copy_requests - set(important_person)
                while copy_number_unchocked>0 and bool(set_copy_requests):
                    selected = random.sample(set_copy_requests, 1)
                    chosen.append(selected[0])
                    copy_number_unchocked-=1
                    set_copy_requests = set_copy_requests - set(selected[0])
            #Here I try to use the self states to remember
             #I selct %4 because every 4th one needs to be reselected
             #It is == 2 because I want this to generalize to all cases, i.e, we
            if round % 4 == 2:
                self.dummy_state["cake"] = ['fake']
                if len(requests) > len(chosen):
                    set_requests = set()
                    for r in requests:
                        set_requests.add(r.requester_id)
                    my_set_chosen = set(chosen)
                    set_to_choose_from = set_requests - my_set_chosen
#                    print(set_to_choose_from, ' set choose from')
                    if len(set_to_choose_from)>0:
                        self.dummy_state["cake"] = random.sample(set_to_choose_from, 1)
#                        print(self.dummy_state["cake"], '  this is my Optimistic')
                else:
                    self.dummy_state["cake"] = ['fake']
            if self.dummy_state["cake"]!=['fake']:
                chosen_full = chosen +  self.dummy_state["cake"]
            else:
                chosen_full = chosen[:]
#            print(self.dummy_state['cake'], 'my state')
#            print(chosen_full, 'this is my chosen full')
            if len(chosen_full)!=0:
                bws = even_split(self.up_bw, len(chosen_full))
            else:
                bws=[]
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen_full, bws)]
        return uploads
