import datetime
import os
import telebot
from dotenv import load_dotenv
from tb_forms import TelebotForms, BaseForm, fields
from supabase import create_client, Client

load_dotenv()

bot = telebot.TeleBot(os.environ.get('BOT_KEY'))
tbf = TelebotForms(bot)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# ----------------------------------------------- INITIALISE -------------------------------------------------------


@bot.message_handler(commands=['start'])
def initialize(message):
    if message.chat.type == 'private':
        user_id = message.from_user.id

        # Create new user if not in db
        create_user(user_id)
        bot.reply_to(message, "I have added you to the database")
    else:
        bot.reply_to(message, "I cant handle all of you at once :(, pm me /start to be added to the database!")


def create_user(user_id):
    res = supabase.table('user').select('*').eq('user_id', user_id).execute()

    if len(res.data) == 0:
        # No user found, so we need to create a new user
        print('Creating new user')
        data, count = supabase.table('user').insert({"user_id": user_id}).execute()
        if len(data) == 0:
            print('Error in creating user')
        print('User created successfully')
    else:
        # User already exists
        print(f'User already exists: {res.data[0]["user_id"]}')

# ---------------------------------------------- SUBMISSION ---------------------------------------------------------


# A submission has the following : Name of problem, Method to solve, Time complexity, Date of completion, Difficulties


class SubmissionForm(BaseForm):
    update_name = "submission_form"
    form_title = "Leetcode Submission"
    freeze_mode = True
    close_form_but = False
    default_step_by_step = True
    submit_button_text = "Submit"
    canceled_text = "Cancel"

    name = fields.StrField("name", "Enter Name of the problem")
    solve_method = fields.StrField("solve_method", "How did you solve it ?")
    time_complexity = fields.StrField("time_complexity", "What is the time complexity ?")
    difficulty = fields.StrField("difficulty", "How did you find this problem ? (optional)", required=False)


@bot.message_handler(commands=['submission'])
def start_update(message):
    if message.chat.type == "private":
        form = SubmissionForm()
        tbf.send_form(message.chat.id, form)
    else:
        bot.reply_to(message, "To make a submission, dm me ;)")


@tbf.form_submit_event("submission_form")
def submit_register_update(call, form_data):

    user_id = call.from_user.id

    name = form_data.name
    solve_method = form_data.solve_method
    time_complexity = form_data.time_complexity
    difficulty = ""

    if form_data.difficulty is None:
        difficulty = ""
    else:
        difficulty = form_data.difficulty

    res = create_submission(user=user_id, name=name, solve_method=solve_method, time_complexity=time_complexity, difficulty=difficulty)

    if res:
        bot.send_message(call.message.chat.id, "Submission Successful")
    else:
        bot.send_message(call.message.chat.id, "Submission Unsuccessful")


def create_submission(user, name, solve_method, time_complexity, difficulty):
    data, count = (supabase.table('submission')
                   .insert({
                        "user": user,
                        "name": name,
                        "solve_method": solve_method,
                        "time_complexity": time_complexity,
                        "difficulty": difficulty
                    })
                   .execute())
    if len(data) == 0:
        print('Error in creating submission')
        return False
    print('submission created successfully')

    return True

# ------------------------------------------ STATUS -----------------------------------------------------------


@bot.message_handler(commands=['status'])
def show_status(message):
    chat_id = message.chat.id
    status_message = ""

    # Fetch the submissions of the users and display in a nice format
    if message.chat.type == "private":
        uid = message.from_user.id
        username = message.from_user.username
        text = get_status_text(uid=uid, username=username, forToday=False)
        status_message += text
        bot.reply_to(message, status_message)

    else:
        all_users = get_usernames()

        for user in all_users:
            # Get the user id
            uid = user['user_id']

            # Check if they exist in this group & get their submissions
            try:
                userObj = bot.get_chat_member(chat_id, uid)
                text = get_status_text(uid=uid, username=userObj.user.username, forToday=True)
                status_message += text

            except telebot.apihelper.ApiTelegramException as e:
                if e.error_code == 400 and "user not found" in e.description:
                    print("User not found in the group")
                else:
                    print("An error occurred:", e)

        bot.reply_to(message, status_message)


def get_status_text(uid, username, forToday=True):

    today = datetime.datetime.today().isoformat()
    if forToday:
        data, count = supabase.table('submission').select('*').eq('user', uid).eq('created_at', today).execute()
        user_submissions = data[1]

        text = "*************************************" + '\n'
        text += username + " submissions: " + '\n' + '\n'

        for sub in user_submissions:
            text += f"Name of Problem : {sub['name']}" + '\n'
            text += f"Solution : {sub['solve_method']}" + '\n'
            text += f"Time Complexity : {sub['time_complexity']}" + '\n'
            text += f"Difficulty : {sub['difficulty']}" + '\n'
            text += '\n'

        return text
    else:
        data, count = supabase.table('submission').select('*').eq('user', uid).execute()
        user_submissions = data[1]

        text = "*************************************" + '\n'
        text += username + " submissions: " + '\n' + '\n'

        for sub in user_submissions:
            text += f"Date : {sub['created_at']}" + '\n'
            text += f"Name of Problem : {sub['name']}" + '\n'
            text += f"Solution : {sub['solve_method']}" + '\n'
            text += f"Time Complexity : {sub['time_complexity']}" + '\n'
            text += f"Difficulty : {sub['difficulty']}" + '\n'
            text += '\n'

        return text


def get_usernames():
    res = supabase.table('user').select('user_id').execute()
    return res.data


bot.infinity_polling()