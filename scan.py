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

        url = "http://" + domain
        status = re.findall(r"(?<=HTTP\/).* [0-9]{3}", result)[0].split(" ")[1]
        print(status)
        if int(status) >= 500:
            results[domain]["insecure_http"] = False
            results[domain]["redirect_to_https"] = False
        else:
            results[domain]["insecure_http"] = True
            redirects = 0
            while (300 <= int(status) < 400) and redirects < 10:
                # use regex to find the redirection url
                url = re.findall(r'(?<=[L|l]ocation: ).*', result)[0][:-1]
                if url.split(":")[0] == "https":
                    results[domain]["redirect_to_https"] = True
                    break
                try:
                    result = subprocess.check_output(["curl", "-v", url], timeout = 2, stderr=subprocess.STDOUT).decode("utf-8")
                except:
                    result = ""
                    print("timed out")
                    break
                redirects += 1
                status = re.findall(r"(?<=HTTP\/).* [0-9]{3}", result)[0].split(" ")[1]
                print(status)
            if "redirect_to_https" not in results[domain]:
                results[domain]["redirect_to_https"] = False

        curl_process = subprocess.Popen(["curl", "-s", "-D-", url], stdout = subprocess.PIPE)
        grep_process = subprocess.Popen(["grep", "-i", "Strict-Transport-Security"], stdin=curl_process.stdout, stdout = subprocess.PIPE)
        hsts, error = grep_process.communicate()
        results[domain]["hsts"] = bool(hsts)

        try:
            nmap_out = subprocess.check_output(["nmap", "--script", "ssl-enum-ciphers", "-p", "443", domain], timeout = 2, stderr=subprocess.STDOUT).decode("utf-8")
        except subprocess.TimeoutExpired:
            print("timed out")
        tls = [d[0] for d in re.findall(r"((TLS|SSL)v.*(?=:))", nmap_out)]
        try:
            openssl_out = subprocess.check_output(["openssl", "s_client", "-connect", domain+":443"], input=b'', timeout = 2, stderr=subprocess.STDOUT).decode("utf-8")
            root_ca = re.findall(r"O = (.*), .*(?=Root CA)", openssl_out)[0].split(",")[0]
        except Exception as e:
            root_ca = None
            if e == subprocess.TimeoutExpired:
                print("timed out")
        
        results[domain]["tls_versions"] = tls
        results[domain]["root_ca"] = root_ca

        addresses = []
        for addr in results[domain]["ipv4_addresses"]:
            try:
                dig_out = subprocess.check_output(["dig", "+answer", "-x", addr], timeout = 2, stderr=subprocess.STDOUT).decode("utf-8")
                # regex for PTR
                addresses += dig_out
            except Exception as e:
                if e == subprocess.TimeoutExpired:
                    print("timed out")
        results[domain]["rdns_names"] = addresses