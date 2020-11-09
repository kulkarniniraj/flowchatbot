# Flow Chatbot library
> A chatbot library to build bots from flowchart


This is a small library to create flow based chatbots, like getting information from user, filling forms, asking multiple choice questions etc. 

Need for this arose when we built a chatbot for various domains mainly for customer interaction and feedback and realised that most of the requirements are satisfied with a deterministic flow based bot.

Few class names given in API were inspired from fluid/water piping model.

## Install

Clone this repo and copy flowchatbot folder in your source folder

## How to use

### Concepts

It is easier to understand classes from regular flowchart elements. 
- A `Pipe` is baseclass defining few properties for all elements
- A `Segment` and its subclasses are regular process element of flowchart definig one operation
- A `Splitter`/`SkipSplitter` is decision making element
- A `Composite`/`LoopComposite` is Subroutine element which contains a bunch of child elements

Each element takes a string key argument in constructor. This is used for:
- identifying children dynamically
- saving current chatbot position in data dict to maintain session
- as a key in data dict to save element's data

A bot generally consists of parent `Composite` object with all flow defined inside.
Each element supports `question` and `answer` method for interaction. `question` is where you get question corresponding to data it seeks from user. `answer` is response returned after obtaining data, including error messages.

Data and state for each element is stored in a `dict` object passed to it. For hierarchical elements like `Composite`, data dict nest data dict of child elements.
So a nested dict may look like:
- A
    - data for A
    - B
        - data for B
        - E
            - data for E
    - C
        - data for C
    - D
        - data for D

An adapter is built on top to simplify question answer process. Given `TextAdapater` had just one method, `respond` which first call answer method of root node with user response, then seeks next question and prints it.

`TextAdapter` stores all data in redis for session management. An alternative adapter can use any available method for session management if redis does not server purpose. Chatbot implementation and data persistance management are separated.

### A simple hello world bot

```python
from flowchatbot import *

bot = TextAdapter(
            Composite('key1',
                Segment('key2', '', 'Hello World!')
                           ))
bot.r.flushall() # clear all old sessions

print(bot.respond('hi', 0)) # 0 is session id, used as key in redis
```

    composite answer current key2 data {'pos': 'key2'}
    composite question current key2 data {'key2': {'data': 'hi'}, 'pos': 'key2'}
    adapter data {'key2': {'data': 'hi'}, 'pos': 'key2'}
    Hello World!
    


First 3 lines are debug output showing chatbot's state 
Last line shows response to input 'hi'
The blank last line means bot has restarted from top and has a blank question.

Let's add some question

```python
from flowchatbot import *

bot = TextAdapter(
            Composite('key1',
                Segment('key2', 'Loop again?', 'Hello World!')
                           ))
bot.r.flushall() # clear all old sessions

print(bot.respond('hi', 0)) # 0 is session id, used as key in redis

print(bot.respond('hello', 0))
```

    composite answer current key2 data {'pos': 'key2'}
    composite question current key2 data {'key2': {'data': 'hi'}, 'pos': 'key2'}
    adapter data {'key2': {'data': 'hi'}, 'pos': 'key2'}
    Hello World!
    Loop again?
    composite answer current key2 data {'key2': {'data': 'hi'}, 'pos': 'key2'}
    composite question current key2 data {'key2': {'data': 'hello'}, 'pos': 'key2'}
    adapter data {'key2': {'data': 'hello'}, 'pos': 'key2'}
    Hello World!
    Loop again?

