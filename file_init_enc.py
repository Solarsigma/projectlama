import pickle
import sys

xp = sys.argv[1]
d = {}
f = open(f"qtables_enc/q_table_{xp}.pickle","wb")
pickle.dump(d, f)
f.close()

print("Refreshed",f"qtables_enc/q_table_{xp}.pickle")

