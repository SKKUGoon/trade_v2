import requests

class LineNotifier:
    TARGET_URL = 'https://notify-api.line.me/api/notify'
    # TOKEN = 'uSOq9RQUp10fzq3kmli56waLpuqKvWUV41SR65vbQyL'  <- Y's token key
    def __init__(self, token='XWU0ewiUw2QxVAcF7ViCqR4QKdz5YjIbZiUb5fAC9Z0'):
        self.TOKEN = token
        pass

    def post_message(self, msg):
        response = requests.post(
            self.TARGET_URL,
            headers={
                'Authorization': 'Bearer ' + self.TOKEN
            },
            data={
                'message': msg
            }
        )

        return response
