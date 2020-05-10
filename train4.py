import sys, random, string
from game import NetworkGame, State, NetworkPlayer
import pickle

alpha = 0.3
lambd = 0.8
reward_dict = {}   # Table format- play n,play n+1,fold,draw
qtable = {}
possible_moves = {}


def full_list(x):
    c = 0
    for i in x:
        if i == 0:
            c += 1
    if c == 0:
        return True
    return False


def make_state(hand, top_card):
    slist = sorted(hand)+[top_card]
    return ''.join([str(v) for v in slist])


def getAction(game):
    epsilon = 0.7
    top_card = game.deck.discard_pile[-1]
    state = make_state(game.turn.hand, top_card)
    # print("state before action",state)
    option_list = [str(top_card), str(top_card % 7 + 1), 'Draw', 'Fold']
    if random.random() < epsilon:
        return option_list[random.choice(possible_moves[state])]
    else:

        return option_list[qtable[state].index(max(qtable[state]))]


def update_reward(hand, top_card):
    if make_state(hand, top_card) in reward_dict:
        return None
    reward_list = [-40, -40, -6, sum(set(hand))*(-1)/2]
    moves = [2, 3]
    qtable[make_state(hand, top_card)] = [0, 0, 0, sum(set(hand))*(-1)/3]
    if top_card in hand:
        moves.append(0)
        if sum([card == top_card for card in hand]) > 1:
            reward_list[0] = top_card/2
        else:
            reward_list[0] = top_card
    else:
        qtable[make_state(hand, top_card)][0] = -40
    if (top_card % 7 + 1) in hand:
        moves.append(1)
        if sum([card == (top_card % 7 + 1) for card in hand]) > 1:
            reward_list[1] = (top_card % 7 + 1)/2
        else:
            reward_list[1] = (top_card % 7 + 1)
    else:
        qtable[make_state(hand, top_card)][1] = -40
    reward_dict[make_state(hand, top_card)] = reward_list
    possible_moves[make_state(hand, top_card)] = moves


def update_table(next_state, prev_state, action):
    update_reward(*next_state)
    update_reward(*prev_state)

    action_indexes = {str(prev_state[1]): 0, str(prev_state[1] % 7 + 1): 1, "Draw": 2, "Fold": 3}
    index = action_indexes[action]
    if action == 'Fold':
        print("Yes")
    pre_state = make_state(*prev_state)
    nex_state = make_state(*next_state)
    # print(pre_state,nex_state,reward_dict[pre_state])
    # print("before",qtable[pre_state])
    qtable[pre_state][index] = (1 - alpha)*qtable[pre_state][index] + alpha*(reward_dict[pre_state][index] + lambd*max(qtable[nex_state]))
    # print("after",qtable[pre_state])
    # print(".......//.......")


if __name__ == "__main__":
    random.seed()
    no_of_games = int(sys.argv[1])
    no_of_players = int(sys.argv[2])

    f1 = open("reward_table1.pickle", "rb")
    f2 = open("poss_moves_table1.pickle", "rb")
    f3 = open("q_table1.pickle", "rb")
    reward_dict = pickle.load(f1)
    possible_moves = pickle.load(f2)
    qtable = pickle.load(f3)
    f1.close()
    f2.close()
    f3.close()

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
                        prev_state = (game.turn.hand[:], game.deck.discard_pile[-1])
                        update_reward(*prev_state)
                    else:
                        if action:
                            update_table((game.turn.hand[:], game.deck.discard_pile[-1]), prev_state, action)
                            prev_state = (game.turn.hand[:], game.deck.discard_pile[-1])
                        action = None
                    if game.turn.active:
                        action = getAction(game)
                    # print("action",action)
                    _ = game.step(action)

                elif game.turn == players[1]:
                    # update_reward(game.turn.hand,game.deck.discard_pile[-1])
                    _ = game.step(game.moveAI(game.turn))
                    # if action=="Fold":
                    # update_table((players[0].hand[:],game.deck.discard_pile[-1]),prev_state,action)

            curr_state = game.state
            if curr_state is State.ROUND_BEGIN:
                prev_state = None
    # print(qtable)
    print('.........')
    print(list(qtable.values()).count([0, 0, 0, 0]), len(list(qtable.keys())))
    print('.........')
    c = 0
    l = []
    for i in qtable.keys():
        if full_list(qtable[i]):
            # print(i,qtable[i])
            c += 1
    print(c)

    for i in qtable.keys():
        for j in range(0, len(qtable[i])):
            l.append(((i, j), qtable[i][j]))

    print(sorted(l, key=lambda x: x[1])[0:5])

    print(sorted(l, key=lambda x: x[1])[:-5:-1])

    f1 = open("reward_table1.pickle", "wb")
    f2 = open("poss_moves_table1.pickle", "wb")
    f3 = open("q_table1.pickle", "wb")
    pickle.dump(reward_dict, f1)
    pickle.dump(possible_moves, f2)
    pickle.dump(qtable, f3)
    f1.close()
    f2.close()
    f3.close()
    # print(reward_dict)
    sys.exit(0)
