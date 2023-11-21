import sys, json
inFile = sys.argv[1]
outFile = sys.argv[2]

results = {}

with open(inFile,'r') as i:
    lines = i.readlines()
    for domain in lines:
        results[domain] = {}

with open(outFile , "w") as f :
    json.dump(results, f, sort_keys=True, indent =4)