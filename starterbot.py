import os
import time
import re
from slackclient import SlackClient

from allennlp.data.tokenizers.word_tokenizer import WordTokenizer
from allennlp.data.tokenizers.word_filter import WordFilter, StopwordFilter
import allennlp.data.dataset_readers.semantic_dependency_parsing as sdp
from allennlp.predictors.predictor import Predictor


# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Not sure what you mean"
    default_food_response = "I didn't quite catch that, but I see that you mentioned something about food. If you want me to order some food, try: @Starter Bot Order <<food>>"

    # Finds and executes the given command, filling in response
    # This is where you start to implement more commands!
    response = None

    verb_list=['order','place','make']
    food_list = [line.rstrip('\n') for line in open('food.txt')]

    print("Made the lists")

    predictor = Predictor.from_path("srl-model-2018.05.25.tar.gz")
    result=predictor.predict(command)
    print(result)

    for dictionary in result['verbs']:
        verb = dictionary['verb']
        if verb in verb_list:
            if verb=='order':
                try:
                    response = dictionary['description']
                    response=response.split('ARG1: ')[1].replace(']','')
                except:
                    print("We did an oopsie here")

    print("Went through the dictionaries")

    if response == None:
        for word in command:
            if word in food_list:
                response=default_food_response
                break

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
