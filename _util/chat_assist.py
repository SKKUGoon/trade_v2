import requests

class LineNotifier:
    TARGET_URL = 'https://notify-api.line.me/api/notify'
    TOKEN = 'XWU0ewiUw2QxVAcF7ViCqR4QKdz5YjIbZiUb5fAC9Z0'  # Your Token Here

    def __init__(self):
        ...

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
