from .constants import State, Prompt, GameErrors
from .deck import Deck
from .players import Player, NetworkPlayer
from .utils import prompter
from collections import defaultdict, deque
from itertools import cycle
from twisted.web import http, server, xmlrpc
import random
import string

class Game:
    def __init__(self):
        self.history = []
        self.state = None

        self.turn_cycler = None
        self.turn = None

    def init(self):
        self.state = State.GAME_BEGIN

    def advance_turn(self):
        self.turn = next(self.turn_cycler)

    def calc_score(self):
        for player in self.players:
            player.calc_score()
        for player in self.players:
            if player.score >= 40:
                return True
        return False


class NetworkGame(Game):
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = []
        self.round_no = 1
        self.log_file = open('game_log.txt', 'a')
        self.error_queue = deque()
        self.input_wait_queue = deque()
        self.global_message_queue = defaultdict(deque)
        self.score_queue = defaultdict(deque)
        super().__init__()

    def init(self):
        super().init()
        self.input_wait_queue.pop()
        self.turn_cycler = cycle(self.players)
        self.turn = next(self.turn_cycler)

    def add_player(self, alias):
        if len(self.players) < 6:
            player_token = ''.join(
                random.choices(
                    string.ascii_uppercase +
                    string.digits,
                    k=5))
            self.players.append(NetworkPlayer(alias, player_token))
            return {"token": player_token}
        else:
            return {"error": "Game is full"}

    def add_AIplayer(self):
        if len(self.players) < 6:
            player_token = ''.join(['AI'] + 
                random.choices(
                    string.ascii_uppercase +
                    string.digits,
                    k=3))
            self.players.append(NetworkPlayer(player_token, player_token, auto=True))
            return {"token": player_token, "alias": player_token}
        else:
        	return {"error": "Game is full. Can't add AI player"}

    def join_AI_player(self, player): #Takes input an object of NetworkPlayer to add to the game. Useful in adding already established AI's to a new game.
        if len(self.players) < 6:
        	self.players.append(player)
        	return {"token": player.token, "alias": player.token}
        else:
        	return {"error": "Game is full. Can't add AI player"}

    def moveAI(self, player):
        def draw_or_fold():
            if len(set(player.hand)) < 3 or player.score < 11:
                return 'Fold'
            else:
                return 'Draw'
        
        if player.active:
            if not len(player.hand):
                return None
            elif sum([self.deck.playable(card) for card in player.hand]):
                return str(player.hand[[self.deck.playable(card) for card in player.hand].index(1)])
            else:
                return draw_or_fold()
        return None

    def find_player(self, player_token):
        # validate guarantees you will find one
        for player in self.players:
            if player.token == player_token:
                return player
        return None

    def drawable(self):
        active_players = sum(map(lambda x: x.active, self.players))
        if not len(self.deck.main_pile) or active_players is 1:
            return False 
        return True

    def active_count(self):
        return sum(map(lambda x: x.active, self.players))

    def _broadcast_message(self, message, typ='NORMAL'):
        queue = self.global_message_queue if typ == 'NORMAL' else self.score_queue
        for player in self.players:
            queue[player.token].append(message)

    def evaluate(self, state, info):
        if state is State.GAME_BEGIN:
            for player in self.players:
                player.score=0
            self.log_file.write("NG/\n")
            self.log_file.write("Round,Type,Player,Move/Score,TopCard(BeforeMove),PlayerHand(AfterMove)\n")
            return None, State.ROUND_BEGIN

        elif state is State.ROUND_BEGIN:
            # deck
            self.deck = Deck()
            self.deck.start()
            self.package_send2 = {}

            # first draw
            for player in self.players:
                player.init()
            for i in range(6):
                for player in self.players:
                    player.draw(self.deck)

            return None, State.ROUND_CONT

        elif state is State.ROUND_CONT:
            if info is not None and info.isdigit():
                info = int(info)

            if not sum(map(lambda x: x.active, self.players)):
                return None, State.ROUND_END

            player = self.turn
            deck = self.deck
            if player.active:
                if not deck.playable(player.hand):
                    active_players = sum(map(lambda x: x.active, self.players))
                    if not len(deck.main_pile) or active_players is 1:
                        player.deactivate()
                        return None, State.ROUND_END
                    else:
                        if info == "Fold":
                            player.deactivate()
                            curr_hand = ''.join([str(i) for i in player.hand])
                            self._broadcast_message(f"<span class='l-player-name'>{player.alias}</span> has folded")
                            self.log_file.write(f"{self.round_no},M,{player.token},{0},{self.deck.discard_pile[-1]},{curr_hand}\n")
                        elif info == "Draw":
                            player.draw(self.deck)
                            curr_hand = ''.join([str(i) for i in player.hand])
                            self._broadcast_message(f"<span class='l-player-name'>{player.alias}</span> has drawn")
                            self.log_file.write(f"{self.round_no},M,{player.token},{-1},{self.deck.discard_pile[-1]},{curr_hand}\n")
                        else:
                            return Prompt.FD, State.ROUND_CONT
                else:
                    if info is None:
                    	active_players = sum(map(lambda x: x.active, self.players))
                    	if not len(deck.main_pile) or active_players is 1:
                    		return Prompt.PF, State.ROUND_CONT
                    	return Prompt.PFD, State.ROUND_CONT
                    else:
                        if info == "Fold":
                            player.deactivate()
                            self._broadcast_message(f"<span class='l-player-name'>{player.alias}</span> has folded")
                            curr_hand = ''.join([str(i) for i in player.hand])
                            self.log_file.write(f"{self.round_no},M,{player.token},{0},{self.deck.discard_pile[-1]},{curr_hand}\n")
                        elif info == "Draw":
                            player.draw(self.deck)
                            curr_hand = ''.join([str(i) for i in player.hand])
                            self._broadcast_message(f"<span class='l-player-name'>{player.alias}</span> has drawn")
                            self.log_file.write(f"{self.round_no},M,{player.token},{-1},{self.deck.discard_pile[-1]},{curr_hand}\n")
                        elif deck.playable(info) and info in player.hand:
                            tbd = player.delete(info)
                            deck.discard(tbd)
                            curr_hand = ''.join([str(i) for i in player.hand])
                            self._broadcast_message(f"<span class='l-player-name'>{player.alias}</span> has played {tbd}")
                            self.log_file.write(f"{self.round_no},M,{player.token},{tbd},{self.deck.discard_pile[-2]},{curr_hand}\n")

                            # round ender if finishes hand
                            if not len(player.hand):
                                return None, State.ROUND_END
                        else:
                            return Prompt.PF, State.ROUND_CONT

            self.advance_turn()
            return None, State.ROUND_CONT

        elif state is State.ROUND_END:
            over = self.calc_score()
            scores = [(player.alias, player.score) for player in self.players]
            for player in self.players:
                self.log_file.write(f"{self.round_no},S,{player.token},{player.score},,\n")
            self.round_no += 1
            self._broadcast_message(scores, typ='SPECIAL')
            if over:
                winner = sorted(self.players,
                                key=lambda x: x.score)[0]
                self._broadcast_message({'winner': winner.alias}, typ='SPECIAL')
                return None, State.GAME_END
            else:
                return None, State.ROUND_BEGIN

    def get_info(self, prompt):
        if prompt is None:
            return None
        elif prompt is Prompt.FD:
            self.input_wait_queue.append("FD")
            return None
        elif prompt is Prompt.PF:
            self.input_wait_queue.append("PF")
            return None
        elif prompt is Prompt.PFD:
        	self.input_wait_queue.append("PFD")
        	return None

    def step(self, info):
        if self.state is not State.GAME_END:
            prompt, new_state = self.evaluate(self.state, info)
            #print(f"{self.game_id} stepping from {str(self.state)} to {str(new_state)}")
            self.state = new_state
            return self.get_info(prompt)
        else:
            self.log_file.write("/NG\n")
            self.log_file.close()


class GameMaster(xmlrpc.XMLRPC):
    def __init__(self):
        self.games = {}
        xmlrpc.XMLRPC.__init__(self)

    @staticmethod
    def __apply_CORS_headers(request):
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        request.setHeader('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Access-Control-Allow-Origin')

    def render_OPTIONS(self, request):
        GameMaster.__apply_CORS_headers(request)
        request.setResponseCode(http.OK)
        request.write('OK'.encode('utf-8'))
        request.finish()
        return server.NOT_DONE_YET

    @xmlrpc.withRequest
    def xmlrpc_open(self, request):
        GameMaster.__apply_CORS_headers(request)
        game_id = ''.join(
            random.choices(
                string.ascii_uppercase +
                string.digits,
                k=5))
        g = NetworkGame(game_id)
        g.input_wait_queue.append("start")
        self.games[game_id] = g
        return game_id

    @xmlrpc.withRequest
    def xmlrpc_validate(self, request, game_id, player_token=None):
        GameMaster.__apply_CORS_headers(request)
        if game_id not in self.games:
            return False
        elif player_token is not None:
            search = sum(map(lambda x: x.token == player_token, self.games[game_id].players))
            if not search:
                return False
        return True

    @xmlrpc.withRequest
    def xmlrpc_join(self, request, game_id, alias):
        GameMaster.__apply_CORS_headers(request)
        return self.games[game_id].add_player(alias)

    @xmlrpc.withRequest
    def xmlrpc_query_state(self, request, game_id, player_token):
        GameMaster.__apply_CORS_headers(request)
        result = {}
        result["message"] = []
        result["score"] = []

        if not self.xmlrpc_validate(request, game_id, player_token=player_token):
            result["error"] = "Invalid token, game pair presented"
            return result

        game = self.games[game_id]
        player = game.find_player(player_token)
        curr_state = game.state

        if not len(game.input_wait_queue):
            _ = game.step(None)

        # Game not begun, lobby state to be sent
        if curr_state is None:
            result["game_state"] = "none"
            result["action"] = "wait"
            result["players"] = list(map(lambda x: x.alias, game.players))

        if curr_state is State.ROUND_CONT:
            result["game_state"] = "round_running"
            result["whose_turn"] = game.turn.alias
            result["hand"] = player.hand
            result["top_card"], result["top_card_v"] = game.deck.top_card()
            if game.turn == player:
                result["my_turn"] = "yes"
                if len(game.input_wait_queue):
                    result["expected_action"] = game.input_wait_queue.pop()

        if len(game.error_queue):
            result["error"] = game.error_queue.pop()

        msg_for_player = game.global_message_queue[player.token]
        while len(msg_for_player):
            result["message"].append(msg_for_player.pop())

        special_msg_for_player = game.score_queue[player.token]
        while len(special_msg_for_player):
            result["score"].append(special_msg_for_player.pop())
        
        if curr_state is State.ROUND_CONT:
            if game.turn.auto:
                _ = game.step(game.moveAI(game.turn))
        return result

    @xmlrpc.withRequest
    def xmlrpc_push_input(self, request, game_id, player_token, inp):
        GameMaster.__apply_CORS_headers(request)
        result = {}

        if not self.xmlrpc_validate(request, game_id, player_token=player_token):
            result["error"] = "Invalid token, game pair presented"
            return result

        game = self.games[game_id]
        player = game.find_player(player_token)
        curr_state = game.state

        if game.turn == player:
            _ = game.step(inp)
        return True

    @xmlrpc.withRequest
    def xmlrpc_add_ai_player(self, request, game_id):
        GameMaster.__apply_CORS_headers(request)
        game = self.games[game_id]
        return game.add_AIplayer()


    @xmlrpc.withRequest
    def xmlrpc_start_game(self, request, game_id, player_token):
        GameMaster.__apply_CORS_headers(request)
        result = {}

        if not self.xmlrpc_validate(request, game_id, player_token=player_token):
            result["error"] = "Invalid token, game pair presented"
            return result

        game = self.games[game_id]
        game.init()

        return result

