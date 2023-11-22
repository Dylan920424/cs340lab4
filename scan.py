import sys, json, time, subprocess, re
inFile = sys.argv[1]
outFile = sys.argv[2]

results = {}

def addressFetch(domain, type):
    try:
        result = subprocess.check_output(["nslookup", "-type="+type, domain, "8.8.8.8"], timeout = 2, stderr=subprocess.STDOUT).decode("utf-8")
    except:
        result = []
        print("timed out")
    print("Result for domain " + domain + " of type " + type + ":")
    print(result)
    addresses = re.findall(r"(?<=Address:).*", result)[1:]
    for i in range(len(addresses)):
        addresses[i] = addresses[i][1:]
    if type == "A":
        results[domain]["ipv4_addresses"] = addresses
    else:
        results[domain]["ipv6_addresses"] = addresses

with open(inFile,'r') as i:
    lines = i.read().splitlines()
    for domain in lines:
        results[domain] = {}
        results[domain]["scan_time"] = time.time()
        addressFetch(domain, "A")
        addressFetch(domain, "AAAA")
        try:
            result = subprocess.check_output(["curl", "-v", "http://"+domain], timeout = 2, stderr=subprocess.STDOUT).decode("utf-8")
        except:
            result = ""
            print("timed out")
        server = re.findall(r"(?<=Server:).*", result)
        if len(server) > 0:
            results[domain]["http_server"] = server[0][1:-1]
        else:
            results[domain]["http_server"] = None
        # r = requests.get("https://"+domain)
        # if "Server" in r.headers:
        #     results[domain]["http_server"] = r.headers["Server"]
        # else:
        #     results[domain]["http_server"] = None
        
        

with open(outFile , "w") as f :
    json.dump(results, f, sort_keys=True, indent =4)