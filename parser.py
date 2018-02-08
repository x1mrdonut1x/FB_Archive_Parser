from html.parser import HTMLParser
from datetime import datetime, timedelta
import pickle
import os.path
from os import listdir, walk
import operator
import sys
import matplotlib.pyplot as plt
import numpy as np
import re
from scipy.interpolate import spline
import time

directory = './messages'

def load_all_conversations():
    files = []
    for (dirpath, dirnames, filenames) in walk('{}'.format(directory)):
        files.extend(filenames)
        for filename in files:
            with open('{}/{}'.format(directory, filename), 'r', encoding="utf8") as f:
                if not os.path.isfile("./saved/{}_data.pickle".format(filename[:-5])):
                    print('Parsing {}...'.format(filename), end="\r")
                    content = f.read()
                    parser = ParseHTMLForData()
                    parser.feed(content)
                    with open("./saved/{}_data.pickle".format(filename[:-5]), 'wb') as fp:
                        print('Saving {}...'.format(filename), end="\r")
                        data = { 
                            'conversation': parser.conversationName,
                            'messages': parser.msgs
                        }
                        pickle.dump(data, fp)
        break

def list_all_conversations():
    conversations = []
    files = []
    for (dirpath, dirnames, filenames) in walk('{}'.format(directory)):
        files.extend(filenames)
        for filename in files:
            with open('{}/{}'.format(directory, filename), 'r', encoding="utf8") as f:
                content = f.read()
                walker = ParseHTMLForUsers()
                try:
                    walker.feed(content)
                except StopIteration:
                    name = walker.conversationName
                    entry = {}
                    entry['name'] = name
                    entry['size'] = os.path.getsize('{}/{}'.format(directory, filename))
                    entry['filename'] = filename
                    conversations.append(entry)
        break

    sorted_conversations = sorted(conversations, key=lambda x:x['size'])
    for entry in sorted_conversations:
        print('{:<20} Size: {:.2f}MB, Filename: {}'.format(
            entry['name'][:18],
            (entry['size']/1024),
            entry['filename']))


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
        self.name = data['conversation']
        self.totalMessages = len(self.messages)
        self.users = list(self.getSenders().keys())
        
        print('\nConversation with {}'.format(self.name))
        print('Total messages: {}\n'.format(self.totalMessages))
        # self.printUserStats()
        # self.getAllWords(15)
        # self.plotByUserByWeek()
        self.compute_breaks()

    def getSenders(self):
        senders = {}
        for message in self.messages:
            sender = message['user']

            if sender in senders:
                senders[sender] += 1
            else:
                senders[sender] = 1

        return senders
    
    def printUserStats(self):
        senders = self.getSenders()
        sorted_senders = sorted(senders.items(), key=lambda x:x[1])
        print('User Stats:')
        for sender in reversed(sorted_senders):
            print('{:<18} {} {:<6} ({:.2f}%)'.format(sender[0], '-', sender[1], (sender[1]/self.totalMessages)*100))
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

    def get_name(self, string):
        return string.split(' ', 1)[0]

    def sort_dict(self, dictionary): 
        return reversed(sorted(dictionary.items(), key=lambda x:x[1]))

    def get_difference_in_hours(self, date1, date2):
        diff = date1 - date2
        days, seconds = diff.days, diff.seconds
        hours = days * 24 + seconds // 3600
        return hours

def getopts(argv):
    opts = {}
    while argv:
        if argv[0][0] == '-':
            if len(argv) > 1:
                opts[argv[0]] = argv[1]
            else:
                opts[argv[0]] = True
        argv = argv[1:]
    return opts

if __name__ == "__main__":
    args = getopts(sys.argv)

    if '-A' in args:
        print('Parsing ALL the files! This might take a while...')
        load_all_conversations()

    if '-f' in args:
        filename = args['-f']
        print("Opening {}/{}".format(directory, filename))
        with open("{}/{}".format(directory, filename), 'r', encoding="utf8") as f:
            if not os.path.isfile("./saved/{}_data.pickle".format(filename[:-5])):
                print('Parsing Data...')
                content = f.read()
                parser = ParseHTMLForData()
                parser.feed(content)
                with open("./saved/{}_data.pickle".format(filename[:-5]), 'wb') as fp:
                    print('Saving Data...')
                    data = { 
                        'conversation': parser.conversationName,
                        'messages': parser.msgs
                    }
                    pickle.dump(data, fp)

            with open ("./saved/{}_data.pickle".format(filename[:-5]), 'rb') as fp:
                print('Loading Data...')
                print('\n')
                data = pickle.load(fp)
                analytics = ComputeCoolStuff(data)
                print('\n')

    else:
        list_all_conversations()
        print()
        print('Select a filename to run the program on.')
        print('Example Use:')
        print('py -3 parser.py -f 760.html')

