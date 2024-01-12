import base64
import json
import time
from json.decoder import JSONDecodeError
import requests
import os
from requests.exceptions import ConnectionError

class Requests:
    def __init__(self):
        self.lockfile = self.get_lockfile()
        self.region = self.get_region()
        self.pd_url = f"https://pd.{self.region[0]}.a.pvp.net"
        self.glz_url = f"https://glz-{self.region[1][0]}.{self.region[1][1]}.a.pvp.net"
        self.region = self.region[0]
        self.headers = {}

        self.puuid = '9783a546-2a5d-53ec-bd8f-a46d311425e0'
        #fetch puuid so its avaible outside
        if not self.get_headers(init=True):
            self.get_lockfile(ignoreLockfile=True)
        
    def fetch(self, url_type: str, endpoint: str, method: str, rate_limit_seconds=5):
        try:
            if url_type == "glz":
                response = requests.request(method, self.glz_url + endpoint, headers=self.get_headers(), verify=False)
                print(f"fetch: url: '{url_type}', endpoint: {endpoint}, method: {method},"
                    f" response code: {response.status_code}")

                if response.status_code == 404:
                    return response.json()

                try:
                    if response.json().get("errorCode") == "BAD_CLAIMS":
                        print("detected bad claims")
                        self.headers = {}
                        return self.fetch(url_type, endpoint, method)
                except JSONDecodeError:
                    pass
                if not response.ok:
                    if response.status_code == 429:
                        print("response not ok glz endpoint: rate limit 429")
                    else:
                        print("response not ok glz endpoint: " + response.text)
                    time.sleep(rate_limit_seconds+5)
                    self.headers = {}
                    self.fetch(url_type, endpoint, method)
                return response.json()
            elif url_type == "pd":
                response = requests.request(method, self.pd_url + endpoint, headers=self.get_headers(), verify=False)
                print(
                    f"fetch: url: '{url_type}', endpoint: {endpoint}, method: {method},"
                    f" response code: {response.status_code}")
                if response.status_code == 404:
                    return response

                try:
                    if response.json().get("errorCode") == "BAD_CLAIMS":
                        print("detected bad claims")
                        self.headers = {}
                        return self.fetch(url_type, endpoint, method)
                except JSONDecodeError:
                    pass

                if not response.ok:
                    if response.status_code == 429:
                        print(f"response not ok pd endpoint, rate limit 429")
                    else:
                        print(f"response not ok pd endpoint, {response.text}")
                    time.sleep(rate_limit_seconds+5)
                    self.headers = {}
                    return self.fetch(url_type, endpoint, method, rate_limit_seconds=rate_limit_seconds+5)
                return response
            elif url_type == "local":
                local_headers = {'Authorization': 'Basic ' + base64.b64encode(
                    ('riot:' + self.lockfile['password']).encode()).decode()}
                
                while True:
                    try:
                        response = requests.request(method, f"https://127.0.0.1:{self.lockfile['port']}{endpoint}",
                                                    headers=local_headers,
                                                    verify=False)
                        if response.json().get("errorCode") == "RPC_ERROR":
                            print("RPC_ERROR waiting 5 seconds")
                            time.sleep(5)
                        else:
                            break
                    except ConnectionError:
                        print("Connection error, retrying in 5 seconds")
                        time.sleep(5)
                if endpoint != "/chat/v4/presences":
                    print(
                        f"fetch: url: '{url_type}', endpoint: {endpoint}, method: {method},"
                        f" response code: {response.status_code}")
                return response.json()
            elif url_type == "custom":
                response = requests.request(method, f"{endpoint}", headers=self.get_headers(), verify=False)
                print(
                    f"fetch: url: '{url_type}', endpoint: {endpoint}, method: {method},"
                    f" response code: {response.status_code}")
                if not response.ok: self.headers = {}
                return response.json()
        except json.decoder.JSONDecodeError:
            print(f"JSONDecodeError in fetch function, resp.code: {response.status_code}, resp_text: '{response.text}")
            print(response)
            print(response.text)

    def get_region(self):
        path = os.path.join(os.getenv('LOCALAPPDATA'), R'VALORANT\Saved\Logs\ShooterGame.log')
        with open(path, "r", encoding="utf8") as file:
            while True:
                line = file.readline()
                if '.a.pvp.net/account-xp/v1/' in line:
                    pd_url = line.split('.a.pvp.net/account-xp/v1/')[0].split('.')[-1]
                elif 'https://glz' in line:
                    glz_url = [(line.split('https://glz-')[1].split(".")[0]),
                               (line.split('https://glz-')[1].split(".")[1])]
                if "pd_url" in locals().keys() and "glz_url" in locals().keys():
                    print(f"got region from logs '{[pd_url, glz_url]}'")
                    if pd_url == "pbe":
                        return ["na", "na-1", "na"]
                    return [pd_url, glz_url]

    def get_current_version(self):
        path = os.path.join(os.getenv('LOCALAPPDATA'), R'VALORANT\Saved\Logs\ShooterGame.log')
        with open(path, "r", encoding="utf8") as file:
            while True:
                line = file.readline()
                if 'CI server version:' in line:
                    version_without_shipping = line.split('CI server version: ')[1].strip()
                    version = version_without_shipping.split("-")
                    version.insert(2, "shipping")
                    version = "-".join(version)
                    print(f"got version from logs '{version}'")
                    return version

    def get_lockfile(self, ignoreLockfile=False):
        path = os.path.join(os.getenv('LOCALAPPDATA'), R'Riot Games\Riot Client\Config\lockfile')
        
        with open(path) as lockfile:
            print("opened lockfile")
            data = lockfile.read().split(':')
            keys = ['name', 'PID', 'port', 'password', 'protocol']
            return dict(zip(keys, data))


    def get_headers(self, refresh=False, init=False):
        if self.headers == {} or refresh:
            try_again = True
            while try_again:
                local_headers = {'Authorization': 'Basic ' + base64.b64encode(
                    ('riot:' + self.lockfile['password']).encode()).decode()}
                try:
                    response = requests.get(f"https://127.0.0.1:{self.lockfile['port']}/entitlements/v1/token",
                                            headers=local_headers, verify=False)
                    print(f"https://127.0.0.1:{self.lockfile['port']}/entitlements/v1/token\n{local_headers}")
                except ConnectionError:
                    print(f"https://127.0.0.1:{self.lockfile['port']}/entitlements/v1/token\n{local_headers}")
                    print("Connection error, retrying in 1 seconds, getting new lockfile")
                    time.sleep(1)
                    self.lockfile = self.get_lockfile()
                    continue
                entitlements = response.json()
                if entitlements.get("message") == "Entitlements token is not ready yet":
                    try_again = True
                    time.sleep(1)
                elif entitlements.get("message") == "Invalid URI format":
                    print(f"Invalid uri format: {entitlements}")
                    if init:
                        return False
                    else:
                        try_again = True
                        time.sleep(5)
                else:
                    try_again = False

            self.puuid = entitlements['subject']
            headers = {
                'Authorization': f"Bearer {entitlements['accessToken']}",
                'X-Riot-Entitlements-JWT': entitlements['token'],
                'X-Riot-ClientPlatform': "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjog"
                                         "IldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5"
                                         "MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
                'X-Riot-ClientVersion': self.get_current_version(),
                "User-Agent": "ShooterGame/13 Windows/10.0.19043.1.256.64bit"
            }
            self.headers = headers
        return self.headers