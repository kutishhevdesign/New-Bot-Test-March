from flask import Flask, request, jsonify
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file

app = Flask(__name__)

COMMANDS = {
    'TEXT': 'Получить текстовую справку',
    'IMAGE': 'Получить картинку',
    'DOCUMENT': 'Получить документ',
    'VIDEO': 'Получить видео',
    'CONTACT': 'Send contact',
    'PRODUCT': 'Send product',
    'GROUP_CREATE': 'Create group',
    'GROUP_TEXT': 'Simple text message for the group',
    'GROUPS_IDS': "Get the id's of your three groups"
}

FILES = {
    'IMAGE': '/root/whatsappbot/New-Bot-Test-March/files/file_example_JPG_100kB.jpg',
    'DOCUMENT': '/root/whatsappbot/New-Bot-Test-March/files/file-example_PDF_500_kB.pdf',
    'VIDEO': '/root/whatsappbot/New-Bot-Test-March/files/file_example_MP4_480_1_5MG.mp4',
    'VCARD': '/root/whatsappbot/New-Bot-Test-March/files/sample-vcard.txt'
}


def send_whapi_request(endpoint, params=None, method='POST'):
    headers = {
        'Authorization': f"Bearer {os.getenv('TOKEN')}"
    }
    url = f"{os.getenv('API_URL')}/{endpoint}"
    if params:
        if 'media' in params:
            details = params.pop('media').split(';')
            with open(details[0], 'rb') as file:
                m = MultipartEncoder(fields={**params, 'media': (details[0], file, details[1])})
                headers['Content-Type'] = m.content_type
                response = requests.request(method, url, data=m, headers=headers)
        elif method == 'GET':
            response = requests.get(url, params=params, headers=headers)
        else:
            headers['Content-Type'] = 'application/json'
            response = requests.request(method, url, json=params, headers=headers)
    else:
        response = requests.request(method, url, headers=headers)
    print('Whapi response:', response.json())
    return response.json()

def set_hook():
    if os.getenv('BOT_URL'):
        settings = {
            'webhooks': [
                {
                    'url': os.getenv('BOT_URL'),
                    'events': [
                        {'type': "messages", 'method': "post"}
                    ],
                    'mode': "method"
                }
            ]
        }
        send_whapi_request('settings', settings, 'PATCH')


@app.route('/hook/messages', methods=['POST'])
def handle_new_messages():
    try:
        messages = request.json.get('messages', [])
        endpoint = None
        for message in messages:
            if message.get('from_me'):
                continue
            sender = {'to': message.get('chat_id')}
            command_input = message.get('text', {}).get('body', '').strip()
            command = list(COMMANDS.keys())[int(command_input) - 1] if command_input.isdigit() else None

            if command == 'TEXT':
                sender['body'] = 'Вам необходимо отправить сообщение с ответами на данные вопросы. Отредактировать сообщение будет нельзя, внимательно проверяйте информацию. После, бот заного отправит вам сообщение со списком комманд.\n\n1. Ваше полное ФИО\n\n2. Ваш возраст\n\n3. Для какой цели вам необходимы наши услуги? (Кредит/Ипотика)\n\n4. Есть ли у вас ИП или ООО?\n\n'
                endpoint = 'messages/text'
            elif command == 'IMAGE':
                sender['caption'] = 'Текст под фотографией.'
                sender['media'] = FILES['IMAGE'] + ';image/jpeg'
                endpoint = 'messages/image'
            elif command == 'DOCUMENT':
                sender['caption'] = 'Текст под PDF документом.'
                sender['media'] = FILES['DOCUMENT'] + ';application/pdf'
                endpoint = 'messages/document'
            elif command == 'VIDEO':
                sender['caption'] = 'Текст под видео.'
                sender['media'] = FILES['VIDEO'] + ';video/mp4'
                endpoint = 'messages/video'
            elif command == 'CONTACT':
                sender['name'] = 'Whapi Test'
                with open(FILES['VCARD'], 'r') as vcard_file:
                    sender['vcard'] = vcard_file.read()
                    endpoint = 'messages/contact'
            elif command == 'PRODUCT':
                # Example: You need to replace config.product with an actual product ID
                product_id = os.getenv('PRODUCT_ID')  # Replace with your product ID
                endpoint = f'business/products/{product_id}'
            elif command == 'GROUP_CREATE':
                # Example: You need to replace config.phone with an actual phone number
                participants = [message.get('chat_id').split('@')[0]]  # Replace with the phone number
                response = send_whapi_request('groups', {'subject': 'Whapi.Cloud Test', 'participants': participants})
                sender['body'] = f"Group created. Group id: {response.get('group_id')}" if response.get('group_id') else 'Error'
                endpoint = 'messages/text'
            elif command == 'GROUP_TEXT':
                sender['to'] = os.getenv('GROUP_ID')  # Replace with your group ID
                sender['body'] = 'Simple text message for the group'
                endpoint = 'messages/text'
            elif command == 'GROUPS_IDS':
                groups_response = send_whapi_request('groups', {'count': 3}, 'GET')
                groups = groups_response.get('groups', [])
                sender['body'] = ',\n '.join(f"{group['id']} - {group['name']}" for group in groups) if groups else 'No groups'
                endpoint = 'messages/text'
            else:
                sender['body'] = "Вас приветствует WhatsApp бот компании Credit Consulting. С моей помощью получится ускорить процесс подготовки и как можно быстрее перейти к делу!\nБот все еще в разработке, могут возникнуть баги,спасибо за понимание.\nОтправьте номер желаемой услуги для получения дальнейшей информации.\n\n" + \
                                 '\n'.join(f"{i + 1}. {text}" for i, text in enumerate(COMMANDS.values()))
                endpoint = 'messages/text'

        if endpoint is None:
            return 'Ok', 200
        response = send_whapi_request(endpoint, sender)
        print(f"Response from Whapi: {response}")
        return 'Ok', 200
    
    except Exception as e:
        print(e)
        return str(e), 500


@app.route('/', methods=['GET'])
def index():
    return 'Bot is running'


if __name__ == '__main__':
    set_hook()
    port = os.getenv('PORT') or (443 if os.getenv('BOT_URL', '').startswith('https:') else 80)
    app.run(port=port, debug=True)
