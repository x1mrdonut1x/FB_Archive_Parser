from html.parser import HTMLParser
import pickle
import os.path
from os import listdir, walk
import operator
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import re
from scipy.interpolate import spline
import datetime

def parse_all_files():
    files = []
    for (dirpath, dirnames, filenames) in walk('{}'.format('./messages')):
        files.extend(filenames)
        for filename in files:
            parse_file(filename)
        break
    print("Done.")


def load_all_saved_files():
    conversations = []
    files = []
    for (dirpath, dirnames, filenames) in walk('{}'.format('./saved')):
        files.extend(filenames)
        print('Loading Data...')
        for filename in files:
            if(filename.endswith('.pickle')):
                with open ("./saved/{}".format(filename), 'rb') as fp:
                    data = pickle.load(fp)
                    conversations.append(data)
        break
    return conversations


def analyze_all_files(conversations):
    messages_by_conversation = {}
    total_messages = 0
    total_conversations = 0
    for conversation in conversations:
        num_messages = len(conversation['messages'])
        messages_by_conversation[conversation['name']] = num_messages
        total_messages += num_messages
        if num_messages > 1:
            total_conversations += 1
    
    print('Total Messages: {:,}'.format(total_messages))
    print('Total Conversations: {:,}'.format(total_conversations))

    for entry in sorted(messages_by_conversation.items(), key=lambda x:x[1]):
        if entry[1] > 1:
            print('{:<20} - {:,} Messages'.format(entry[0][:19], entry[1]))
        

def list_all_files():
    conversations = []
    files = []
    for (dirpath, dirnames, filenames) in walk('{}'.format('./messages')):
        files.extend(filenames)
        for filename in files:
            with open('{}/{}'.format('./messages', filename), 'r', encoding="utf8") as f:
                content = f.read()
                walker = ParseHTMLForUsers()
                try:
                    walker.feed(content)
                except StopIteration:
                    name = walker.conversationName
                    entry = {}
                    entry['name'] = name
                    entry['size'] = os.path.getsize('{}/{}'.format('./messages', filename))
                    entry['filename'] = filename
                    conversations.append(entry)
        break
    return conversations


def print_listed_files(conversations):
    sorted_conversations = sorted(conversations, key=lambda x:x['size'])
    for entry in sorted_conversations:
        print('{:<20} Size: {:.2f}MB, Path: {}'.format(
            entry['name'][:18],
            (entry['size']/1024),
            entry['filename']))


def find_file_by_conversation_name(conversation_name):
    conversations = load_all_saved_files()
    for conversation in conversations:
        if conversation['name'].startswith(conversation_name):
            return conversation
    
    conversations = list_all_files()
    for conversation in conversations:
        if conversation['name'].startswith(conversation_name):
            return conversation
    
    print("Could not find specified conversation.\n")


def parse_file(filename):
    with open("{}/{}".format('./messages', filename), 'r', encoding="utf8") as f:
        # If file already parsed skip this step
        if not os.path.isfile("./saved/{}_data.pickle".format(filename[:-5])):
            print('Parsing {}...'.format(filename), end="\r")
            content = f.read()
            parser = ParseHTMLForData()
            parser.feed(content)
            with open("./saved/{}_data.pickle".format(filename[:-5]), 'wb') as fp:
                print('Saving {}...'.format(filename), end="\r")
                data = { 
                    'name': parser.conversationName,
                    'messages': parser.msgs
                }
                pickle.dump(data, fp)


class ParseHTMLForData(HTMLParser):
    def __init__(self):
        super(ParseHTMLForData, self).__init__()
        self.msgs = []
        self.isUser      = False
        self.isDate      = False
        self.isMessage   = False
        self.isTitle     = False
        self.endOfHeader = False
        self.goToAdd     = False

        self.lastEndTag = ''
        self.lastStartTag = ''

        self.currentUser = ''
        self.currentMessage = ''
        self.currentDate = ''

    def handle_starttag(self, tag, attrs):
        currentClass = ''
        attrs = dict(attrs)

        if 'class' in attrs:
            currentClass = attrs['class']
            
        if tag == 'title':
            self.isTitle = True
        elif tag == 'span' and currentClass == 'user':
            self.isUser = True
        elif tag == 'span' and currentClass == 'meta':
            self.isDate = True
        elif tag == 'p' and self.endOfHeader:
            self.isMessage = True
        
        self.lastStartTag = tag

    def handle_data(self, data):
        global conversationName

        if self.isUser:
            self.isUser = False
            self.currentUser = data

        elif self.isDate:
            self.isDate = False
            self.currentDate = data

        elif self.isMessage:
            self.isMessage = False
            self.endOfHeader = False
            self.goToAdd = True
            self.currentMessage = data

        elif self.isTitle:
            self.isTitle = False
            self.conversationName = data[18:]

    def handle_endtag(self, tag):
        if tag == 'div' and self.lastEndTag == 'div':
            self.endOfHeader = True
        
        if self.isUser:
            self.isUser = False
            self.currentUser = 'Deleted'

        if self.goToAdd:
            self.handleNewMessage(self.currentDate, self.currentUser, self.currentMessage)
            self.isMessage = False
            self.isDate = False
            self.isUser = False
            self.isTitle = False
            self.goToAdd = False

        self.lastEndTag = tag
 
    def handleNewMessage(self, date, user, message):
        tmp = ''
        msg = {}
        try:
            tmp = datetime.strptime(date, '%A, %d %B %Y at %H:%M %Z')
        except ValueError as e:
            date = date[:-3]
            tmp = datetime.strptime(date, '%A, %d %B %Y at %H:%M %Z')
        msg['user'] = user
        msg['message'] = message
        msg['date'] = tmp

        self.msgs.append(msg)


class ParseHTMLForUsers(HTMLParser):
    isTitle = False
    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.isTitle = True

    def handle_data(self, data):
        if self.isTitle:
            self.conversationName = data[18:]
            raise StopIteration


class ComputeCoolStuff():
    def __init__(self, data):
        self.messages = data['messages']
        self.name = data['name']
        self.totalMessages = len(self.messages)
        self.users = list(self.get_num_of_messages_by_user().keys())
        
        print('\nConversation with {}'.format(self.name))
        print('Total messages: {:,}\n'.format(self.totalMessages))

    def get_num_of_messages_by_user(self):
        senders = {}
        for message in self.messages:
            sender = message['user']

            if sender in senders:
                senders[sender] += 1
            else:
                senders[sender] = 1

        return senders
    
    def printUserStats(self):
        senders = self.get_num_of_messages_by_user()
        sorted_senders = self.sort_dict(senders)
        print('User Stats:')
        for sender in sorted_senders:
            print('{:<18} - {:,} Messages({:.2f}%)'.format(sender[0], sender[1], (sender[1]/self.totalMessages)*100))
        print()

    def week_range(self, date):
        year, week, dow = date.isocalendar()
        if dow == 7:
            start_date = date
        else:
            start_date = date - timedelta(dow)
            
        end_date = start_date + timedelta(6)
        return (start_date.date(), end_date.date())

    def messagesByWeek(self):
        weeks = {}
        for message in self.messages:
            weekRange = self.week_range(message['date'])
            start = weekRange[0]
            end = weekRange[1]

            if start in weeks:
                weeks[start] += 1
            else:
                weeks[start] = 1
        return weeks  
        
    def messagesByDay(self):
        days = {}
        
        for message in self.messages:
            day = message['date'].date()

            if day in days:
                days[day] += 1
            else:
                days[day] = 1
        return days

    def getAllWords(self, n):
        min_length = 3
        all_words = []
        words_count = {}
        for message in self.messages:
            words = message['message'].split()
            words = [w for w in words if len(w) > min_length]
            words = [w.lower() for w in words]
            words = [re.sub('[ ,.]','', w) for w in words]
            words = [re.sub('ą','a', w) for w in words]
            words = [re.sub('ę','e', w) for w in words]
            words = [re.sub('ć','c', w) for w in words]
            words = [re.sub('ó','o', w) for w in words]
            words = [re.sub('ń','n', w) for w in words]
            words = [re.sub('ż','z', w) for w in words]
            words = [re.sub('ź','z', w) for w in words]
            words = [re.sub('ś','s', w) for w in words]
            words = [re.sub('ł','l', w) for w in words]
            
            for word in words:
                all_words.append(word)
            
        for word in all_words:
            if word in words_count:
                words_count[word] += 1
            else:
                words_count[word] = 1
        
        sorted_words = sorted(words_count.items(), key=operator.itemgetter(1))
        print('Top {} Words:'.format(n))
        for word in sorted_words[-n:]:
            if word[1] > 5: # If count bigger than 5
                print('{:<8} - {}'.format(word[0], word[1]))
        print()

    def getMessagesByUserByWeek(self):
        users = dict((user, {}) for user in self.users)
        weeks = {}
        for message in self.messages:
            currentUser = message['user']
            weekRange = self.week_range(message['date'])
            start = weekRange[0]

            if start in users[currentUser]:
                users[currentUser][start] += 1
            else:
                users[currentUser][start] = 1

        return users      
        
    def getMessagesByUserByDay(self):
        users = dict((user, {}) for user in self.users)
        weeks = {}
        for message in self.messages:
            currentUser = message['user']
            day = message['date'].date()

            if day in users[currentUser]:
                users[currentUser][day] += 1
            else:
                users[currentUser][day] = 1
                
            
        return users

    def plotByUserByWeek(self):
        users = self.getMessagesByUserByWeek()

        for user in users:
            x_axis = list(users[user].keys())
            y_axis = list(users[user].values())

            plt.plot(x_axis, y_axis, label=user)

        plt.xticks(rotation=30)
        plt.xlabel('Weeks')
        plt.ylabel('# Messages')
        plt.legend()
        plt.grid()
        plt.title("Number of Messages by Week by User")

        plt.show()

    def plotByUserByDay(self):
        users = self.getMessagesByUserByDay()
        for user in users:
            temp = {k: v for k, v in users[user].items() if v < 50}
            
            x_axis = list(temp.keys())
            y_axis = list(temp.values())
            

            plt.plot(x_axis, y_axis, label=user)

        plt.xticks(rotation=30)
        plt.xlabel('Days')
        plt.ylabel('# Messages')
        plt.legend()
        plt.grid()
        plt.title("Number of Messages by Week by User")

        plt.show()

    def compute_breaks(self):
        max_difference = 10
        longest_break = 0
        longest_streak = 0
        longest_streak_start = ''
        start_streak = ''
        end_streak = ''

        started_by_user = dict((user, 0) for user in self.users)
        ended_by_user = dict((user, 0) for user in self.users)

        msgs = self.messages
        for i in range(len(msgs) - 1):
            msg1 = msgs[i]     # Newer message
            msg2 = msgs[i + 1] # Older message

            if start_streak == '':
                start_streak = msg2

            hours_diff = self.get_difference_in_hours(msg1['date'], msg2['date'])
            
            if longest_break < hours_diff:
                longest_break = hours_diff

            if hours_diff > max_difference:
                started_by_user[msg1['user']] += 1
                ended_by_user[msg2['user']] += 1
                
                end_streak = msg2
                current_streak = self.get_difference_in_hours(start_streak['date'], end_streak['date']) // 24
                if longest_streak < current_streak:
                    longest_streak_start = start_streak['date']
                    longest_streak = current_streak
                
                start_streak = msg2
            

        print("Conversations started by:")
        for entry in self.sort_dict(started_by_user):
            print('{:<9} - {}'.format(self.get_name(entry[0]), entry[1]))
        print("\nConversations ended by:")
        for entry in self.sort_dict(ended_by_user):
            print('{:<9} - {}'.format(self.get_name(entry[0]), entry[1]))
        print("\nThe longest break was {} days :(".format(longest_break//24))
        print("But your longest streak was {} days! It started on {}".format(longest_streak, longest_streak_start))

    def compute_total_words_by_user(self):
        users = dict((user, {
                'total_words': 0, 
                'total_letters': 0, 
                'total_msgs': 0,
            }) for user in self.users)

        for message in self.messages:
            temp = re.sub('[ ,.:;]','', message['message'])
            num_letters = len(temp)
            num_words = len(message['message'].split())

            user = message['user']
            users[user]['total_letters'] += num_letters
            users[user]['total_words'] += num_words
            users[user]['total_msgs'] += 1
        
        tmp = self.sort_dict(self.get_num_of_messages_by_user())
        for entry in tmp:
            user = entry[0]
            print('{:<8} - Total Messages: {}, Total Words: {}\n {:>8} Avg Words per Message: {:.2f}, Avg Letters per Message: {:.2f}'.format(
                self.get_name(user), users[user]['total_msgs'], 
                users[user]['total_words'],
                '',
                users[user]['total_words']/users[user]['total_msgs'], 
                users[user]['total_letters']/users[user]['total_words']))
            print()

    def get_name(self, string):
        return string.split(' ', 1)[0]

    def sort_dict(self, dictionary): 
        return reversed(sorted(dictionary.items(), key=lambda x:x[1]))

    def get_difference_in_hours(self, date1, date2):
        diff = date1 - date2
        days, seconds = diff.days, diff.seconds
        hours = days * 24 + seconds // 3600
        return hours
    
    def plot_daily_activity(self):
        arr = self.get_messages_every_5_minutes(self.messages)
        x_axis = [i[0] for i in arr]
        y_axis = [i[1] for i in arr]

        fig, ax = plt.subplots()
        ax.plot(x_axis, y_axis)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        fig.autofmt_xdate()

        plt.xticks(rotation=30)
        plt.xlabel('Hour')
        plt.ylabel('# Messages')
        plt.title('Daily Messages per 5 Minutes with {}'.format(self.name))

        plt.show()

    def get_messages_every_5_minutes(self, messages):
        out = {}
        for msg in messages:
            date = msg['date']
            minute = ((date.minute // 5) * 5)
            hour = (date.hour)
            entry = datetime.datetime.strptime('{} {}'.format(hour, minute), '%H %M')
            if entry in out:
                out[entry] += 1
            else:
                out[entry] = 1
        sorted_out = sorted(out.items(), key=lambda x:x[0])
        return sorted_out
    
def getopts(argv):
    opts = {}
    while argv:
        if argv[0][0] == '-':
            if len(argv) > 1 and argv[1][0] != '-':
                opts[argv[0]] = argv[1]
            else:
                opts[argv[0]] = True
        argv = argv[1:]
    return opts


if __name__ == "__main__":
    args = getopts(sys.argv)

    if '-h' in args:
        print('\nusage: [-A] parse all .html files')
        print('       [-files] list all .html files with conversation, size and path')
        print('       [-list] list all conversations with number of messages')
        print('       [-load] load specific file')
        print('       [-find <conversation name>] find specific conversation\n')

    if '-A' in args:
        print('Parsing ALL the files! This might take a while...')
        parse_all_files()
    
    if '-list' in args:
        analyze_all_files(load_all_saved_files())

    if '-files' in args:
        print_listed_files(list_all_files())
    elif '-find' in args or '-load' in args:
        if '-find' in args:
            if (type(args['-find']) != bool):
                data = find_file_by_conversation_name(args['-find'])
            else:
                print('Enter a name to find')

        if '-load' in args:
            filename = args['-load']
            print("Opening {}/{}".format('./messages', filename))
            parse_file(filename)

            with open ("./saved/{}_data.pickle".format(filename[:-5]), 'rb') as fp:
                print('Loading {}...'.format(filename))
                data = pickle.load(fp)

        analytics = ComputeCoolStuff(data)
        if '-breaks' in args:
            analytics.compute_breaks()
        
        if '-wordstats' in args:
            analytics.compute_total_words_by_user()

        if '-topwords' in args:
            analytics.getAllWords(15)

        if '-stats' in args:
            analytics.printUserStats()

        if '-activity' in args:
            analytics.plot_daily_activity()
        
        if '-plot' in args:
            analytics.plotByUserByWeek()

    if '-test' in args:
        all_messages = []
        tmp = load_all_saved_files()
        for x in tmp:
            for msg in x['messages']:
                all_messages.append(msg)
        data = { 
            'name': 'All Conversations',
            'messages': all_messages
        }
        analytics = ComputeCoolStuff(data)
        analytics.plot_daily_activity()
