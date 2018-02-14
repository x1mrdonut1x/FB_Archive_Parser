# FB Archive Parser

Facebook gives you the ability to download all the data you ever gave to them. From messages, through shared pictures and new profile pics, to reactions and your friends list activity over the years.

This script can retrieve all your messages and perform a couple of tasks on them.
The coolest one is plotting messages between users in specific conversations.

### Prerequisites

You will need Python 3 and the required packages.

```
pip install -r requirements.txt 
```

## Usage

```
usage: [-A] parse all .html files

       List items:
       [-files] list all .html files with conversation, size and path
       [-list] list all conversations with number of messages

       Run algorithms on specific items:
       [-load <filename>] parse and load specific file
       [-find <conversation name>] find specific parsed conversation

       Algorithms:
       [-breaks] Computes breaks of >8h you had in conversation
       [-wordstats] Shows how many words users wrote
       [-topwords] Shows top words in conversation
       [-stats] Shows distribution of messages sent
       [-activity] Shows activity in conversation from beginning
       [-plot] Shows messages sent by users by week
```

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
