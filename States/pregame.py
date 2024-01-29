



class Pregame:
    def __init__(self, Requests):
        self.Requests = Requests
        self.response = ""



    def get_pregame_match_id(self):
        global response
        try:
            response = self.Requests.fetch(url_type="glz", endpoint=f"/pregame/v1/players/{self.Requests.puuid}", method="get")
            if response.get("errorCode") == "RESOURCE_NOT_FOUND":
                return 0
            match_id = response['MatchID']
            print(f"[+] retrieved pregame match id: '{match_id}'")
            return match_id
        except (KeyError, TypeError):
            print(f"cannot find pregame match id: {response}")
            try:
                self.response = self.Requests.fetch(url_type="glz", endpoint=f"/pregame/v1/players/{self.Requests.puuid}", method="get")
                match_id = self.response['MatchID']
                print(f"retrieved pregame match id: '{match_id}'")
                return match_id
            except (KeyError, TypeError):
                print(f"[-] No match id found. {self.response}")
            return 0

    def get_pregame_stats(self):
        match_id = self.get_pregame_match_id()
        if match_id != 0:
            return self.Requests.fetch("glz", f"/pregame/v1/matches/{match_id}", "get")
        else:
            return None
        
    def Hover(self):
        match_id = self.get_pregame_match_id()
        hover = self.Requests.fetch('glz', f"/pregame/v1/matches/{match_id}/lock/add6443a-41bd-e414-f6ad-e58d267f4e95",'post')
        return hover