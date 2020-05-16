import pickle
import sys

num_players = sys.argv[1]
xp = sys.argv[2]
d = {}
f = open(f"p{num_players}/q_table_{xp}.pickle","wb")
pickle.dump(d, f)
f.close()

print("Refreshed",f"p{num_players}/q_table_{xp}.pickle")

