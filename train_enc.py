import sys, random, string
from game import NetworkGame, State, NetworkPlayer
import pickle

alpha = 0.3
lambd = 0.8                 # Table format- play n,play n+1,fold,draw
qtable = [{},{},{},{}]
xp = []


def full_list(x):
    c = 0
    for i in x:
        if i == 0:
            c += 1
    if c == 0:
        return True
    return False


def make_state(hand, top_card , active_count):
    slist = sorted(hand) + [top_card] + [active_count]
    return ''.join([str(v) for v in slist])


def reward(state):
    hand = [int(i) for i in state[0:-2]]
    top_card = int(state[-2])


    reward_list = [-40, -40, -6, sum(set(hand))*(-1)/3]

    if top_card in hand:
        reward_list[0] = top_card/hand.count(top_card)

    if (top_card % 7 + 1) in hand:
        reward_list[1] = (top_card % 7 + 1)/hand.count(top_card % 7 + 1)

    return reward_list

def poss_moves(state):
    hand = [int(i) for i in state[0:-2]]
    top_card = int(state[-2])

    moves=[2,3]

    if top_card in hand:
        moves.append(0)

    if (top_card % 7 + 1) in hand:
        moves.append(1)

    return moves


def getActionAgent(game):   
        epsilon = 0.2
        top_card = game.deck.discard_pile[-1]
        state = make_state(game.turn.hand, top_card, game.active_count())
        #print("state before action",state)
        option_list = [str(top_card), str(top_card % 7 + 1), 'Draw', 'Fold']
        if random.random() < epsilon:
            poss_list=poss_moves(state)[:]
            if not game.drawable():
                poss_list.remove(2)
            return option_list[random.choice(poss_list)]
        else:
            max_list=qtable[xp[0]-1][state][:]
            if not game.drawable():
                max_list[2] = -40
            max_index_list=[i for i in range(len(max_list)) if max_list[i] == max(max_list)]
            #print(max_index_list, "....",state, qtable[xp[0]-1][state],option_list)
            return option_list[random.choice(max_index_list)]

def getActionOpponent(game,xp):   
    if xp:   
        top_card = game.deck.discard_pile[-1]
        state = make_state(game.turn.hand, top_card, game.active_count())
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

def update_reward(hand, top_card, active_count, xp):                           # for initializing qtable 
    if make_state(hand, top_card, active_count) in qtable[xp-1]:
        return None
    
    state = make_state(hand, top_card, active_count)
    qtable[xp-1][state] = [0, 0, 0, sum(set(hand))*(-1)/3]
    
    if top_card not in hand:
        qtable[xp-1][state][0] = -40

    if (top_card % 7 + 1) not in hand:
        qtable[xp-1][state][1] = -40

    if len(hand) == 1:          # reward for completing the hand
        if hand[0] == top_card:
            qtable[xp-1][state][0] = 25
        if hand[0] == (top_card % 7 + 1):
            qtable[xp-1][state][1] = 25        


def update_table(next_state, prev_state, action):
    update_reward(*next_state, xp[0])
    update_reward(*prev_state, xp[0])
    #print(prev_state)
    action_indexes = {str(prev_state[1]): 0, str(prev_state[1] % 7 + 1): 1, "Draw": 2, "Fold": 3}
    index = action_indexes[action]
    #if action == 'Fold':
        #print("Yes")
    pre_state = make_state(*prev_state)
    nex_state = make_state(*next_state)
    # print(pre_state,nex_state,reward_dict[pre_state])
    # print("before",qtable[pre_state])
    qtable[xp[0]-1][pre_state][index] = (1 - alpha)*qtable[xp[0]-1][pre_state][index] + alpha*(reward(pre_state)[index] + lambd*max(qtable[xp[0]-1][nex_state]))
    # print("after",qtable[pre_state])
    # print(".......//.......")


if __name__ == "__main__":
    random.seed()
    no_of_games = int(sys.argv[1])
    no_of_players = int(sys.argv[2])
    
    for i in range(no_of_players):
        xp.append(int(sys.argv[i+3]))              #experience level of agent and opponents

    for i in range(len(qtable)):
        with open(f"qtables_enc/q_table_{i+1}.pickle", "rb") as f:
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
    
    for i in range(no_of_games):
        print(i)
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
        prev_state = None
        action = None
        
        while curr_state is not State.GAME_END:
            _ = game.step(None)
            
            if curr_state is State.ROUND_CONT:
                if game.turn == players[0]:
                    if prev_state is None:
                        prev_state = (game.turn.hand[:], game.deck.discard_pile[-1], game.active_count())
                        update_reward(*prev_state, xp[0])
                    else:
                        if action:
                            update_table((game.turn.hand[:], game.deck.discard_pile[-1], game.active_count()), prev_state, action)
                            prev_state = (game.turn.hand[:], game.deck.discard_pile[-1], game.active_count())
                        action = None
                    
                    if game.turn.active:
                        action = getActionAgent(game)
                    # print("action",action)
                    _ = game.step(action)

                else:
                    # update_reward(game.turn.hand,game.deck.discard_pile[-1])
                    action1 = None

                    if xp[players.index(game.turn)]:
                        update_reward(game.turn.hand[:], game.deck.discard_pile[-1], game.active_count(), xp[players.index(game.turn)])

                    if game.turn.active:
                        action1 = getActionOpponent(game , xp[players.index(game.turn)])
                    
                    _ = game.step(action1)
                    # if action=="Fold":
                    # update_table((players[0].hand[:],game.deck.discard_pile[-1]),prev_state,action)

            curr_state = game.state
            if curr_state is State.ROUND_BEGIN:
                prev_state = None
    # print(qtable)
    ####################################
    ####################################
    print('.........')                                              
    print(list(qtable[xp[0]-1].values()).count([0, 0, 0, 0]), len(list(qtable[xp[0]-1].keys())))
    print('.........')
    c = 0
    l = []
    for i in qtable[xp[0]-1].keys():
        if full_list(qtable[xp[0]-1][i]):
            # print(i,qtable[i])
            c += 1
    print(c)

    for i in qtable[xp[0]-1].keys():
        for j in range(0, len(qtable[xp[0]-1][i])):
            l.append(((i, j), qtable[xp[0]-1][i][j]))

    print(sorted(l, key=lambda x: x[1])[0:5])

    print(sorted(l, key=lambda x: x[1])[:-5:-1])

    ####################################
    ####################################

    for i in range(len(qtable)):
        with open(f"qtables_enc/q_table_{i+1}.pickle", "wb") as f:
            pickle.dump(qtable[i],f)

    sys.exit(0)
