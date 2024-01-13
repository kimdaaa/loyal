class utilities:
    def __init__(self, Request):
        self.Request = Request

    def dodge(self, match_id):
        Dodge = self.Request.fetch(url_type= 'glz', endpoint=f"/pregame/v1/matches/{match_id}/quit", method="post")
        print('queue should be dodged fr')
        return Dodge
    




