import base64
import json
import time
from json.decoder import JSONDecodeError
import requests
import os
from requests.exceptions import ConnectionError
import urllib3
from colorama import Fore, Style, init # Keeping these imports, but will log through self.logger instead of direct print for consistency

class Requests:
    # 1. ADD logger=None PARAMETER HERE
    def __init__(self, logger=None): 
        # 2. ASSIGN THE LOGGER ATTRIBUTE
        self.logger = logger if logger else self._default_logger # Use a default logger if none provided

        self.lockfile = self.get_lockfile()
        self.region = self.get_region()
        self.pd_url = f"https://pd.{self.region[0]}.a.pvp.net"
        self.glz_url = f"https://glz-{self.region[1][0]}.{self.region[1][1]}.a.pvp.net"
        self.region = self.region[0]
        self.headers = {}
        self.puuid = None # Initialize puuid here

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        #fetch puuid so its avaible outside
        # Changed get_headers to be called explicitly for initial auth,
        # and ensure puuid is set early.
        self.logger("Initializing Requests authentication...", tag="info")
        if not self.get_headers(init=True):
            self.logger("Initial header fetching failed. Trying to get new lockfile and re-authenticate.", tag="warning")
            self.get_lockfile(ignoreLockfile=True) # This might need to be self.get_lockfile(True) depending on usage
            self.get_headers(refresh=True) # Try fetching headers again

    # Helper for default logging if no logger is passed
    def _default_logger(self, message, tag="info"):
        """A simple print-based logger fallback."""
        if tag == "error":
            print(f"{Fore.RED}[{tag.upper()}] {message}{Style.RESET_ALL}")
        elif tag == "warning":
            print(f"{Fore.YELLOW}[{tag.upper()}] {message}{Style.RESET_ALL}")
        elif tag == "success":
            print(f"{Fore.GREEN}[{tag.upper()}] {message}{Style.RESET_ALL}")
        elif tag == "debug":
             # Only print debug if you want a lot of console output
             # print(f"[DEBUG] {message}") 
             pass # By default, suppress debug for cleaner console unless explicitly enabled
        else:
            print(f"[{tag.upper()}] {message}")


    def fetch(self, url_type: str, endpoint: str, method: str, rate_limit_seconds=5):
        try:
            full_url = ""
            if url_type == "glz":
                full_url = self.glz_url + endpoint
            elif url_type == "pd":
                full_url = self.pd_url + endpoint
            elif url_type == "local":
                full_url = f"https://127.0.0.1:{self.lockfile['port']}{endpoint}"
            elif url_type == "custom":
                full_url = endpoint # For custom URLs, endpoint is the full URL

            headers_to_use = self.get_headers() if url_type in ["glz", "pd", "custom"] else {'Authorization': 'Basic ' + base64.b64encode(('riot:' + self.lockfile['password']).encode()).decode()}

            response = None # Initialize response outside try block
            
            # Handle local endpoint specifically due to its retry logic
            if url_type == "local":
                while True:
                    try:
                        response = requests.request(method, full_url, headers=headers_to_use, verify=False)
                        if response.json().get("errorCode") == "RPC_ERROR":
                            self.logger("RPC_ERROR waiting 5 seconds", tag="warning")
                            time.sleep(5)
                        else:
                            break
                    except ConnectionError:
                        self.logger("Connection error to local API, retrying in 5 seconds", tag="error")
                        time.sleep(5)
            else:
                response = requests.request(method, full_url, headers=headers_to_use, verify=False)
            
            # Common handling for all responses
            self.logger(
                f"[!] fetch: url: '{url_type}', endpoint: {endpoint}, method: {method},"
                f" response code: {response.status_code}", tag="debug")

            if response.status_code == 404:
                # For 404, just return the JSON if available, otherwise response object
                try:
                    return response.json()
                except JSONDecodeError:
                    return response # Return raw response if not JSON

            try:
                # Check for "BAD_CLAIMS" on all JSON responses
                if response.json().get("errorCode") == "BAD_CLAIMS":
                    self.logger("Detected BAD_CLAIMS, refreshing headers and retrying.", tag="warning")
                    self.headers = {} # Clear headers to force refresh
                    return self.fetch(url_type, endpoint, method, rate_limit_seconds) # Retry with refreshed headers
            except JSONDecodeError:
                pass # Not a JSON response or errorCode not present

            if not response.ok:
                if response.status_code == 429:
                    self.logger(f"Response not ok for '{url_type}' endpoint: rate limit 429. Retrying after sleep.", tag="warning")
                    time.sleep(rate_limit_seconds + 5)
                    self.headers = {} # Clear headers, though rate limit usually means wait, not re-auth
                    # Rerun the fetch with the same parameters
                    return self.fetch(url_type, endpoint, method, rate_limit_seconds=rate_limit_seconds + 5)
                else:
                    self.logger(f"Response not ok for '{url_type}' endpoint: {response.status_code} - {response.text}", tag="error")
                    # If it's not OK and not 429, we still might want to return the response
                    # or an empty dict, depending on how downstream code handles it.
                    # For now, let's just return the response object for inspection.
                    return response.json() if response.text else response # Attempt to return json, else raw response

            return response.json() # Successful response, return JSON

        except JSONDecodeError:
            self.logger(f"JSONDecodeError in fetch function. Status: {response.status_code}, Text: '{response.text}'", tag="error")
            return None # Indicate failure to decode JSON
        except ConnectionError as e:
            self.logger(f"Connection error during fetch: {e}", tag="error")
            return None
        except Exception as e:
            self.logger(f"An unexpected error occurred in fetch: {e}", tag="error")
            return None

    def get_region(self):
        path = os.path.join(os.getenv('LOCALAPPDATA'), R'VALORANT\Saved\Logs\ShooterGame.log')
        try:
            with open(path, "r", encoding="utf8") as file:
                pd_url = None
                glz_url = None
                for line in file: # Iterate through lines instead of while True and readline()
                    if '.a.pvp.net/account-xp/v1/' in line:
                        pd_url = line.split('.a.pvp.net/account-xp/v1/')[0].split('.')[-1]
                    if 'https://glz' in line:
                        # Ensure to get the correct parts for glz (e.g., 'eu-1', 'eu')
                        parts = line.split('https://glz-')[1].split(".a.pvp.net")[0].split('.')
                        glz_url = [parts[0], parts[1]] if len(parts) > 1 else [parts[0], parts[0]] # Handle single part regions
                    
                    if pd_url and glz_url: # Both found
                        self.logger(f"Got region from logs: {[pd_url, glz_url]}", tag="debug")
                        if pd_url == "pbe":
                            return ["na", ["na-1", "na"]] # PBE often maps to NA
                        return [pd_url, glz_url]
                self.logger("Could not find region in logs. Is Valorant running and logs up-to-date?", tag="error")
                return ["na", ["na-1", "na"]] # Default to NA if not found
        except FileNotFoundError:
            self.logger(f"ShooterGame.log not found at {path}. Is Valorant running?", tag="error")
            return ["na", ["na-1", "na"]] # Default to NA
        except Exception as e:
            self.logger(f"Error reading ShooterGame.log for region: {e}", tag="error")
            return ["na", ["na-1", "na"]] # Default to NA


    def get_current_version(self):
        path = os.path.join(os.getenv('LOCALAPPDATA'), R'VALORANT\Saved\Logs\ShooterGame.log')
        try:
            with open(path, "r", encoding="utf8") as file:
                for line in file:
                    if 'CI server version:' in line:
                        version = line.split('CI server version: ')[1].strip()
                        self.logger(f"Got client version from logs: '{version}'", tag="debug")
                        return version
                self.logger("Could not find client version in logs.", tag="error")
                return "0.0.0.0" # Default version if not found
        except FileNotFoundError:
            self.logger(f"ShooterGame.log not found at {path}. Cannot get client version.", tag="error")
            return "0.0.0.0"
        except Exception as e:
            self.logger(f"Error reading ShooterGame.log for version: {e}", tag="error")
            return "0.0.0.0"


    def get_lockfile(self, ignoreLockfile=False):
        path = os.path.join(os.getenv('LOCALAPPDATA'), R'Riot Games\Riot Client\Config\lockfile')
        
        while True: # Loop to continuously try reading lockfile
            try:
                with open(path) as lockfile:
                    data = lockfile.read().strip().split(':')
                    keys = ['name', 'PID', 'port', 'password', 'protocol']
                    lockfile_data = dict(zip(keys, data))
                    self.logger("Lockfile data obtained.", tag="success")
                    return lockfile_data
            except FileNotFoundError:
                self.logger("Lockfile not found. Is Valorant or Riot Client running? Retrying in 2 seconds...", tag="warning")
                time.sleep(2)
            except Exception as e:
                self.logger(f"Error reading lockfile: {e}. Retrying in 2 seconds...", tag="error")
                time.sleep(2)

    def get_headers(self, refresh=False, init=False):
        if not self.headers or refresh: # Check if headers are empty or refresh is requested
            try_again = True
            while try_again:
                local_headers = {'Authorization': 'Basic ' + base64.b64encode(
                    ('riot:' + self.lockfile['password']).encode()).decode()}
                try:
                    # Use self.fetch for consistency, even for local calls
                    response_data = self.fetch(url_type="local", endpoint="/entitlements/v1/token", method="get")
                    
                    if response_data is None: # fetch returned None due to error
                        self.logger("Failed to get entitlements token (response was None). Retrying.", tag="error")
                        time.sleep(1)
                        self.lockfile = self.get_lockfile() # Get a fresh lockfile
                        continue # Retry loop
                    
                    if response_data.get("message") == "Entitlements token is not ready yet":
                        self.logger("Entitlements token not ready yet. Retrying in 1 second.", tag="warning")
                        try_again = True
                        time.sleep(1)
                    elif response_data.get("message") == "Invalid URI format":
                        self.logger(f"Invalid URI format for entitlements: {response_data}", tag="error")
                        if init:
                            return False # Indicate initial setup failure
                        else:
                            try_again = True
                            time.sleep(5)
                    elif response_data.get("errorCode"): # Any other error code from API
                        self.logger(f"Error in entitlements token response: {response_data.get('errorCode')}. Response: {response_data}", tag="error")
                        if init:
                            return False
                        else:
                            try_again = True
                            time.sleep(5)
                    else:
                        # Success case: entitlements token received
                        try_again = False
                        entitlements = response_data

                except ConnectionError:
                    self.logger("Connection error to local API for entitlements. Retrying in 1 second, getting new lockfile.", tag="error")
                    time.sleep(1)
                    self.lockfile = self.get_lockfile() # Get a fresh lockfile
                    continue
                except Exception as e:
                    self.logger(f"Unexpected error getting entitlements: {e}. Retrying.", tag="error")
                    time.sleep(1)
                    continue

            # Ensure entitlements are set before trying to access
            if 'entitlements' not in locals() or not entitlements:
                 self.logger("Failed to obtain entitlements. Cannot set headers.", tag="error")
                 return {} # Return empty headers on failure

            self.puuid = entitlements.get('subject') # Assign PUUID to self.puuid
            
            headers = {
                'Authorization': f"Bearer {entitlements.get('accessToken')}",
                'X-Riot-Entitlements-JWT': entitlements.get('token'),
                'X-Riot-ClientPlatform': "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjog"
                                         "IldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5"
                                         "MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
                'X-Riot-ClientVersion': self.get_current_version(),
                "User-Agent": "ShooterGame/13 Windows/10.0.19043.1.256.64bit"
            }
            self.headers = headers
            self.logger("Headers successfully obtained and set.", tag="success")
        return self.headers