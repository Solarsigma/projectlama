import sys, random, string
from game import NetworkGame, State, NetworkPlayer
import pickle

   # Table format- play n,play n+1,fold,draw
qtable = [{},{},{},{}]
xp=[]


def poss_moves(state):
    hand = [int(i) for i in state[0:-1]]
    top_card = int(state[-1])

    moves=[2,3]

    if top_card in hand:
        moves.append(0)

    if (top_card % 7 + 1) in hand:
        moves.append(1)

    return moves


def make_state(hand, top_card):
    slist = sorted(hand)+[top_card]
    return ''.join([str(v) for v in slist])


def getAction(game,xp):   
    if xp:   
        top_card = game.deck.discard_pile[-1]
        state = make_state(game.turn.hand, top_card)
        # print("state before action",state)
        option_list = [str(top_card), str(top_card % 7 + 1), 'Draw', 'Fold']
        
        max_list=qtable[xp-1][state][:]
        if not game.drawable():
            max_list[2] = -40
        max_index_list=[i for i in range(len(max_list)) if max_list[i] == max(max_list)]
        #print(max_index_list, "....",state, qtable[xp-1][state])
        return option_list[random.choice(max_index_list)]
    else:
        return game.moveAI(game.turn)


def update_reward(hand, top_card, xp):                           # for initializing qtable 
    if make_state(hand, top_card) in qtable[xp-1]:
        return None
    
    qtable[xp-1][make_state(hand, top_card)] = [0, 0, 0, sum(set(hand))*(-1)/3]
    
    if top_card not in hand:
        qtable[xp-1][make_state(hand, top_card)][0] = -40

    if (top_card % 7 + 1) not in hand:
        qtable[xp-1][make_state(hand, top_card)][1] = -40

    if len(hand) == 1:          # reward for completing the hand
        if hand[0] == top_card:
            qtable[xp-1][make_state(hand, top_card)][0] = 25
        if hand[0] == (top_card % 7 + 1):
            qtable[xp-1][make_state(hand, top_card)][1] = 25        


if __name__ == "__main__":
    no_of_games = int(sys.argv[1])
    no_of_players = int(sys.argv[2])

    for i in range(no_of_players):
        xp.append(int(sys.argv[i+3]))              #experience level of agent and opponents

    for i in range(len(qtable)):
        with open(f"p{no_of_players}/q_table_{i+1}.pickle", "rb") as f:
            qtable[i] = pickle.load(f)

    players = []

    if no_of_players > 6:
        print("Error: Can't have more than 6 players per game")
        sys.exit(1)
    for i in range(no_of_players):
        player_token = ''.join(['AI'] + 
                random.choices(
                    string.ascii_uppercase +
                    string.digits,
                    k=3))
        players.append(NetworkPlayer(player_token, player_token, auto=True))

    wins = 0

    for i in range(no_of_games):
        game_id = ''.join(
            random.choices(
                string.ascii_uppercase +
                string.digits,
                k=5))
        game = NetworkGame(game_id)
        game.input_wait_queue.append("start")
        
        for AIplayer in players:
            game.join_AI_player(AIplayer)
        
        game.init()
        _ = game.step(None)
        curr_state = game.state
        while curr_state is not State.GAME_END:
            _ = game.step(None)
            if curr_state is State.ROUND_CONT:
                action = None
                if game.turn.active:
                    if xp[players.index(game.turn)]:
                        update_reward(game.turn.hand[:],game.deck.discard_pile[-1],xp[players.index(game.turn)])
                    action = getAction(game,xp[players.index(game.turn)])
                _ = game.step(action)
            curr_state = game.state

        if players[0].score < players[1].score:
            wins += 1

    print("Win % =",wins/no_of_games*100)
    
    for i in range(len(qtable)):
        with open(f"p{no_of_players}/q_table_{i+1}.pickle", "wb") as f:
            pickle.dump(qtable[i],f)

    sys.exit(0)
