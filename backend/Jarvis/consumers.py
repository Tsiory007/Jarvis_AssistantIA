#views but for websockets

from channels.generic.websocket import WebsocketConsumer

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def receive(self, text_data):
        self.send(text_data=f"You said {text_data}")
    
    def disconnect(self, close_code):
        pass