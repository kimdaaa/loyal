class utilities:
    def __init__(self, Request):
        self.Request = Request

    def dodge(self, match_id):
        Dodge = self.Request.fetch(url_type= 'glz', endpoint=f"/pregame/v1/matches/{match_id}/quit", method="post")
        return Dodge
    def Queue(self, party_id):
    
      #  type = self.Request.fetch('glz', f'parties/v1/parties/{party_id}/makedefault?queueID=competitive', 'post')
        queu = self.Request.fetch(url_type= 'glz', endpoint=  f"/parties/v1/parties/{party_id}/matchmaking/join", method="post")
        return queu
    def SOloEXp(self, puuid):

        soloexp = self.Request.fetch('glz', f'/parties/v1/players/{puuid}/startsoloexperience', 'post')
        return soloexp
    
    




