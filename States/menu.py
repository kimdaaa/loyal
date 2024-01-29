




class Menu:
    def __init__(self, Requests, presences):
        self.Requests = Requests
        self.presences = presences

    def get_party_json(self, GamePlayersPuuid, presencesDICT):
        party_json = {}
        for presence in presencesDICT:
            if presence["puuid"] in GamePlayersPuuid:
                decodedPresence = self.presences.decode_presence(presence["private"])
                if decodedPresence["isValid"]:
                    if decodedPresence["partySize"] > 1:
                        try:
                            party_json[decodedPresence["partyId"]].append(presence["puuid"])
                        except KeyError:
                            party_json.update({decodedPresence["partyId"]: [presence["puuid"]]})

        #remove non-in-game parties from with one player in game
        parties_to_delete = []
        for party in party_json:
            if len(party_json[party]) == 1:
                parties_to_delete.append(party)
        for party in parties_to_delete:
            del party_json[party]

        print(f"retrieved party json: {party_json}")
        return party_json

    def get_party_members(self, self_puuid, presencesDICT):
        res = []
        for presence in presencesDICT:
            if presence["puuid"] == self_puuid:
                decodedPresence = self.presences.decode_presence(presence["private"])
                if decodedPresence["isValid"]:
                    party_id = decodedPresence["partyId"]
                    res.append({"Subject": presence["puuid"], "PlayerIdentity": {"AccountLevel":
                                                                                     decodedPresence["accountLevel"]}})
        for presence in presencesDICT:
            decodedPresence = self.presences.decode_presence(presence["private"])
            if decodedPresence["isValid"]:
                if decodedPresence["partyId"] == party_id and presence["puuid"] != self_puuid:
                    res.append({"Subject": presence["puuid"], "PlayerIdentity": {"AccountLevel":
                                                                                     decodedPresence["accountLevel"]}})
        print(f"retrieved party members: {res}")
        return res
    def get_party_id(self,puuid):
        global response
        try:
            response = self.Requests.fetch('glz', f"/parties/v1/players/{puuid}", 'get')

            if 'CurrentPartyID' in response:
                current_party_id = response['CurrentPartyID']
                print(f"Current Party ID: {current_party_id}")
                return current_party_id
            else:
                print("No CurrentPartyID found in the response.")
                return 0
        except (KeyError, TypeError):
            print("Error in retrieving Party ID.")
            return 0
    
        
