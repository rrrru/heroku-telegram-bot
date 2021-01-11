import telegram, logging, os, requests, json, random, string
from functools import wraps
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext


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
    def wrapped(bot, update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            update.message.reply_text('You are not allowed to open my door!')
            return
        return func(bot, update, *args, **kwargs)
    return wrapped



@restricted

def build_menu(bot, update):
    button_list = [ "/list", "/delete" ]
    for i in base_requests()["types"]:
        button_list.append(i["name"])
    #["/create"],
    #["/delete"],
    #["/list"]
    #]
    reply_markup = telegram.ReplyKeyboardMarkup(button_list, resize_keyboard=True)
    update.message.reply_text('use /create /delete or /list', reply_markup=reply_markup)

def random_name():
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(12))

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)

def base_requests():
    try:
        info_req = requests.get(f'{ENDPOINT}/clients/current', headers=headers)
        list_req = requests.get(f'{ENDPOINT}/servers', headers=headers)
        type_req = requests.get(f'{ENDPOINT}hetzner/server_types', headers=headers)
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
        return {
            "balance" : balance,
            "servers" : servers,
            "types"   : types,
        }
    except:
        return f'err in base requests'



def create(bot, update):
    
    try:
        server_name = random_name()
        data = {'name': server_name, 'sshKeys': [], 'image': IMAGE_ID, 'serverType': 3, 'datacenter': 3, 'options': {}}
        requests.post(f'{ENDPOINT}/servers', headers=headers, data=json.dumps(data))
        update.effective_message.reply_text(base_requests()["servers"])
    except:
        update.effective_message.reply_text('err')

def list(bot, update):
    try:
        rsp = f'balance: {base_requests()["balance"]}\n'
        for i in base_requests()["servers"]:
           rsp += f'{i["name"]} {i["ipv4"]} {i["status"]}\n' 
        update.effective_message.reply_text(rsp)
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

    dp.add_handler(MessageHandler(Filters.text, build_menu))
    dp.add_error_handler(error)

    # Start the webhook
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TG_TOKEN)
    updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(NAME, TG_TOKEN))
    updater.idle()
