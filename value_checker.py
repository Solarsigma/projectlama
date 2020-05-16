import sys
import pickle


f1 = open("reward_table1.pickle", "rb")
f2 = open("poss_moves_table1.pickle", "rb")
f3 = open("q_table1.pickle", "rb")
reward_dict = pickle.load(f1)
possible_moves = pickle.load(f2)
qtable = pickle.load(f3)
f1.close()
f2.close()
f3.close()


print(qtable[sys.argv[1]])
