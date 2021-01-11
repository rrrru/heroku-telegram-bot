import telegram, logging, os, requests, json, random, string, re
from functools import wraps
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

# envs
NAME = 'hetnzer-provisioner'

ADMINS = [int(x) for x in (os.environ.get( "ADMINS", "72679202")).split(",")]
BEARER = os.environ.get("BEARER_TOKEN", "qwerty")
TG_TOKEN = os.environ.get("TG_TOKEN", "qwerty")
IMAGE_ID = int(os.environ.get("IMAGE_ID", 29368999))
ENDPOINT = 'https://hetzner.abcd.cloud/backend'

headers = {
    'authorization': f'Bearer {BEARER}',
    'Content-Type': 'application/json',
}

def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            update.message.reply_text('You are not allowed to open my door!')
            return
        return func(bot, update, *args, **kwargs)
    return wrapped

def split(arr, size):
     arrs = []
     while len(arr) > size:
         pice = arr[:size]
         arrs.append(pice)
         arr   = arr[size:]
     arrs.append(arr)
     return arrs

@restricted


def build_menu(bot, update):
    button_list = [ ["/list", "/delete"] ]
    types_list = []

    for i in (base_requests()["types"]):
       if re.match(r"^[^\W_]+$", i["name"]):
           types_list.append(i["name"])

    types_list = split(types_list, 4)
    for i in types_list:
        button_list.append(i)


    reply_markup = telegram.ReplyKeyboardMarkup(button_list, resize_keyboard=True)
    update.message.reply_text('use /delete or /list', reply_markup=reply_markup)

def random_name():
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(12))

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)

def base_requests():
    try:
        info_req = requests.get(f'{ENDPOINT}/clients/current', headers=headers)
        list_req = requests.get(f'{ENDPOINT}/servers', headers=headers)
        type_req = requests.get(f'{ENDPOINT}/hetzner/server_types', headers=headers)
        type_rsp = json.loads(type_req.text)
        info_rsp = json.loads(info_req.text)
        list_rsp = json.loads(list_req.text)
        balance = f'{info_rsp["deposit"]}'
        servers = []
        types = []
        for i in list_rsp:
            servers.append(i)
        for i in type_rsp:
            types.append(i)

        status = f'balance: {balance}\n'
        for i in  servers:
            status += f'{i["name"]} {i["ipv4"]} {i["status"]}\n' 

        return {
            "balance" : balance,
            "servers" : servers,
            "types"   : types,
            "status"  : status,
        }
    except:
        return f'err in base requests'


def create(bot, update):
    full_rsp = base_requests()
    type_id = [x["id"] for x in full_rsp["types"] if x["name"] == update.message.text]
    try:
        server_name = random_name()
        data = {'name': server_name, 'sshKeys': [], 'image': IMAGE_ID, 'serverType': type_id[0], 'datacenter': 3, 'options': {}}
        requests.post(f'{ENDPOINT}/servers', headers=headers, data=json.dumps(data))
        update.effective_message.reply_text(base_requests()["status"])
    except:
        update.effective_message.reply_text('err')

def list(bot, update):
    try:
        update.effective_message.reply_text(base_requests()["status"])
    except:
        update.effective_message.reply_text('err list')


def delete(bot, update):
    try:
        server_json = base_requests()["servers"][0]
        del_req = requests.delete(f'{ENDPOINT}/servers/{server_json["id"]}', headers=headers)
        del_rsp = json.loads(del_req.text)
        update.effective_message.reply_text(f'{server_json["name"]} has been deleted: {del_rsp}')
    except:
        update.effective_message.reply_text('del err')


if __name__ == "__main__":
    # Port is given by Heroku
    PORT = os.environ.get('PORT', 5000)

    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Set up the Updater
    updater = Updater(TG_TOKEN)
    dp = updater.dispatcher
    # Add handlers
    dp.add_handler(CommandHandler('delete', delete))
    dp.add_handler(CommandHandler('list', list))
    dp.add_handler(CommandHandler('create', create))
    dp.add_handler(CommandHandler('start', build_menu))
    dp.add_handler(MessageHandler(Filters.regex(r"[a-z]"), create)) 

    dp.add_error_handler(error)

    # Start the webhook
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TG_TOKEN)
    updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(NAME, TG_TOKEN))
    updater.idle()
