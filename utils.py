class utilities:
    def __init__(self, Request):
        self.Request = Request

    def dodge(self, match_id):
        Dodge = self.Request.fetch(url_type= 'glz', endpoint=f"/pregame/v1/matches/{match_id}/quit", method="post")
        return Dodge
    def Queue(self, party_id):
        queue = self.Request.fetch(url_type= 'glz', endpoint=  f"/parties/v1/parties/{party_id}/matchmaking/join", method="post")
        return queue
    




