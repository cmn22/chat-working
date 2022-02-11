import json
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from .models import Message, User


User = get_user_model()

class ChatConsumer(WebsocketConsumer):

    def fetch_messages(self, data):
        messages = Message.last_10_messages()
        rev_messages = list()
        messages = Message.objects.order_by('-timestamp').all()[:10]
        for i in range(len(messages)-1,-1,-1):
            rev_messages.append(messages[i])
        content = {
            'command': 'messages',
            'messages': self.messages_to_json(rev_messages)
        }
        self.send_message(content)

    def new_message(self, data):
        sender = data['sender']
        sender_user = User.objects.filter(username=sender)[0]
        receiver = data['receiver']
        receiver_user = User.objects.filter(username=receiver)[0]
        message = Message.objects.create(
            sender = sender_user,
            receiver = receiver_user,
            message = data['message']
        )
        content = {
            'command': 'new_message',
            'message': self.message_to_json(message)
        }
        return self.send_chat_message(content)

    def messages_to_json(self, messages):
        result = []
        for message in messages:
            result.append(self.message_to_json(message))
        return result

    def message_to_json(self, message):
        return {
            'sender': message.sender.username,
            'receiver': message.receiver.username,
            'message': message.message,
            'timestamp': str(message.timestamp)
        }

    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message
    }

    def connect(self):
        async_to_sync(self.channel_layer.group_add)("chat", self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)("chat", self.channel_name)

    def receive(self, text_data):
        data = json.loads(text_data)
        self.commands[data['command']](self, data)

    def send_chat_message(self, message):
        async_to_sync(self.channel_layer.group_send)(
            'chat',
            {
                'type': 'chat_message',
                'message': message
            }
        )

    def send_message(self, message):
        self.send(text_data=json.dumps(message))

    def chat_message(self, event):
        message = event['message']
        self.send(text_data=json.dumps(message))
