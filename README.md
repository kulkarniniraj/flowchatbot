# Flow Chatbot library
> A chatbot library to build bots from flowchart


This is a small library to create flow based chatbots, like getting information from user, filling forms, asking multiple choice questions etc. 

Need for this arose when we built a chatbot for various domains mainly for customer interaction and feedback and realised that most of the requirements are satisfied with a deterministic flow based bot.

Few class names given in API were inspired from fluid/water piping model.

## Install

Clone this repo and copy flowchatbot folder in your source folder

## Documentation
Please visit [docs](https://kulkarniniraj.github.io/flowchatbot/)

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
```
data = {'A': {
            'data': 'data for A',
            'B':{
                'data': 'data for B',
                'C':{
                    'data': 'data for C'
                }
            },
            'D':{
                'data': 'data for D'
            },
            'E':{
                'data': 'data for E'
            }
        }
    }
```

An adapter is built on top to simplify question answer process. Given `TextAdapater` had just one method, `respond` which first call answer method of root node with user response, then seeks next question and prints it.

`TextAdapter` stores all data in redis for session management. An alternative adapter can use any available method for session management if redis does not server purpose. Chatbot implementation and data persistance management are separated.

### A simple hello world bot

We'll write a simple bot that says 'Hello World!' on any user input and repeats the process.
Conceptual flow is shown in diagram below.


![Flow](images/1.png)

```python
from flowchatbot import *

bot = TextAdapter(
            Composite('key1',
                Segment('key2', '', 'Hello World!')
                           ))
bot.r.flushall() # clear all old sessions

print(bot.respond('hi', 0)) # 0 is session id, used as key in redis
```

    Hello World!
    


First line shows response to input 'hi'
The blank last line means bot has restarted from top and has a blank question.

Let's ask a question before starting again. So modified flow would be:
![Flow 2](images/2.png)

```python
from flowchatbot import *

bot = TextAdapter(
            Composite('key1',
                Segment('key2', 'Loop again?', 'Hello World!')
                           ))
bot.r.flushall() # clear all old sessions
```




    True



```python
print(bot.respond('hi', 0)) # 0 is session id, used as key in redis
```

    Hello World!
    Loop again?


```python
print(bot.respond('hello', 0))
```

    Hello World!
    Loop again?


### Q&A bot

Let's build a bot to ask series of questions, one after another. Basic flow is shown in figure below
![Fig 3](images/3.png)

```python
from flowchatbot import *
bot = TextAdapter(
            Composite('key1',
                  Segment('key2', '', 'Welcome to QnA bot'),
                  Segment('key3', 'Your name?', 'got it'),
                  Segment('key4', 'Your phone?', 'got it'),
                  Segment('key5', 'Your email?', 'got it'),
                           ))
bot.r.flushall() # clear all old sessions
```




    True



```python
print(bot.respond('hi', 0))
```

    Welcome to QnA bot
    Your name?


```python
print(bot.respond('Test123', 0))
```

    got it
    Your phone?


```python
print(bot.respond('12312313', 0))
```

    got it
    Your email?


```python
print(bot.respond('a@b.c', 0))
```

    got it
    


#### Validate inputs
For now, the inputs are not validated. ValidatedSegment takes a validating function as parameter. User response will be passed to this function and the same question will repeat till input is validated. Let's add validation to phone number and email address. So flow will be like this:
![Flow 4](images/4.png)

```python
import re
def validate_phone(data):
    if re.match('\d{10}', data) is not None:
        return 1
    return 0

def validate_email(data):
    if re.match('[a-zA-Z0-9_]+@[a-zA-Z0-9_.]+\.[a-zA-Z0-9_]', data) is not None:
        return 1
    return 0

```

```python
from flowchatbot import *
bot = TextAdapter(
            Composite('key1',
                  Segment('key2', '', 'Welcome to QnA bot'),
                  Segment('key3', 'Your name?', 'got it'),
                  ValidatedSegment('key4', 'Your phone?', 'got it',
                                  'phone num should be 10 digits', validate_phone),
                  ValidatedSegment('key5', 'Your email?', 'got it',
                      'Email should be of format user@server.domain', validate_email),
                           ))
bot.r.flushall() # clear all old sessions
```




    True



```python
print(bot.respond('hi', 0))
```

    Welcome to QnA bot
    Your name?


```python
print(bot.respond('Test123', 0))
```

    got it
    Your phone?


```python
print(bot.respond('12312', 0))
```

    phone num should be 10 digits
    Your phone?


```python
print(bot.respond('1231231312', 0))
```

    got it
    Your email?


```python
print(bot.respond('a@b', 0))
```

    Email should be of format user@server.domain
    Your email?


```python
print(bot.respond('a@b.c', 0))
```

    got it
    


Get chatbot data at end with

```python
bot.get_data(0)
```




    {'key2': {'data': 'hi'},
     'key3': {'data': 'Test123'},
     'key4': {'data': '1231231312'},
     'key5': {'data': 'a@b.c'},
     'pos': 'key2'}



### Chatbot with decision making elements

Let's build a sample bot that asks if soap or hand sanitizer is needed and quotes unit price accordingly

### 1. Ask for choice

A multichoice segment takes a list of possible responses as argument. User response is validated to be in range 1...N (for N choices). Both user response and actual choice is stored in data

```python
from flowchatbot import *
bot = TextAdapter(
            Composite('key1',
                  Segment('key2', '', 'Welcome to Shop bot'),
                  Segment('name', 'Your name?', 'got it'),
                  MultiChoiceSegment('choice', 'Which item do you want?',
                                    ['Soap',
                                    'Hand Sanitizer'], 'Sure'), # ask for choice
                      
                           ))
bot.r.flushall() # clear all old sessions
```




    True



```python
print(bot.respond('hi', 1))
```

    Welcome to Shop bot
    Your name?


```python
print(bot.respond('Testing', 1))
```

    got it
    Which item do you want?
    1. Soap
    2. Hand Sanitizer


```python
print(bot.respond('3', 1))
```

    Please enter one of 1..2 as answer
    Which item do you want?
    1. Soap
    2. Hand Sanitizer


```python
print(bot.respond('1', 1))
```

    Sure
    


```python
bot.get_data(1)
```




    {'key2': {'data': 'hi'},
     'name': {'data': 'Testing'},
     'choice': {'data': [0, 'Soap']},
     'pos': 'key2'}



### 2. Take branch as per choice

A splitter is flowchart decision making element. It takes a splitter function argument which is passed with data of parent container (usually `Composite`) and actual user response. It returns index of branch to take.

So, in our case, flow will look like:
![Flow 5](images/5.png)

```python
from flowchatbot import *

def decide_product(data):
    return get_chained_data(data, 'choice', 'data')[0]

bot = TextAdapter(
            Composite('key1',
                  Segment('key2', '', 'Welcome to Shop bot'),
                  Segment('name', 'Your name?', 'got it'),
                  MultiChoiceSegment('choice', 'Which item do you want?',
                                    ['Soap',
                                    'Hand Sanitizer'], 'Sure'), # ask for choice
                  Splitter('split1', 
                           Segment('soap', 'Price of one soap is 30 Rs.', 'got it'),
                           Segment('sanitize', 
                                   'Price of hand sanitizer bottle is 60 Rs.', 'got it'),
                          decider_fn = decide_product
                           )))
bot.r.flushall() # clear all old sessions
```




    True



```python
print(bot.respond('hi', 1))
print(bot.respond('Testing', 1))
```

    Welcome to Shop bot
    Your name?
    got it
    Which item do you want?
    1. Soap
    2. Hand Sanitizer


```python
print(bot.respond('3', 1))
```

    Please enter one of 1..2 as answer
    Which item do you want?
    1. Soap
    2. Hand Sanitizer


```python
print(bot.respond('2', 1))
```

    Sure
    Price of hand sanitizer bottle is 60 Rs.


### 3. Add computation at the end

So far each segment has been a plain question answer or validation or decision making segment. We haven't associated any action with it. E.g. at the end of conversation we may want to send a mail to bot owner about customer interaction and contact details. Also if we want OTP validation for phone/email we need to interact with APIs in that particular segment.

For such cases, it is useful to implement a subclass of `ComputeSegment` and override answer method. It is just like a plain segment, but answer gets data of parent (`Composite`) segment.

Let's build a bot based on previous example. Here we'll add a compute segment at end to ask how many units customer wants to buy and compute price according to choice. This can be easily implemented without decision making element, but we'll use it anyway just for sake of continuity,

```python
from flowchatbot import *

def decide_product(data):
    return get_chained_data(data, 'choice', 'data')[0]

class PriceCompute(ComputeSegment):
    def answer(self, resp, data):
        ch = get_chained_data(data, 'choice', 'data')[0]
        price = [30, 60]
        try:
            vol = int(resp)
        except:
            vol = 0
        cost = vol * price[ch]
        set_chained_data(data, 'calculate', 'data', val=cost)
        return CHAT_RET.NEXT, {'txt': f'Total cost is {cost} Rs.'}
    
bot = TextAdapter(
            Composite('key1',
                  Segment('key2', '', 'Welcome to Shop bot'),
                  Segment('name', 'Your name?', 'got it'),
                  MultiChoiceSegment('choice', 'Which item do you want?',
                                    ['Soap',
                                    'Hand Sanitizer'], 'Sure'), # ask for choice
                  Splitter('split1', 
                           Segment('soap', 'Price of one soap is 30 Rs. ' +
                           'Put the order?', 'got it'),
                           Segment('sanitize', 
                                   'Price of hand sanitizer bottle is 60 Rs. ' +
                                   'Put the order?', 'got it'),
                          decider_fn = decide_product
                           ),
                  PriceCompute('calculate', 'How many units do you want?', '')))
bot.r.flushall() # clear all old sessions
```




    True



```python
print(bot.respond('hi', 1))
print(bot.respond('Testing', 1))
print(bot.respond('3', 1))
print(bot.respond('2', 1))
```

    Welcome to Shop bot
    Your name?
    got it
    Which item do you want?
    1. Soap
    2. Hand Sanitizer
    Please enter one of 1..2 as answer
    Which item do you want?
    1. Soap
    2. Hand Sanitizer
    Sure
    Price of hand sanitizer bottle is 60 Rs. Put the order?


```python
print(bot.respond('yes', 1))
```

    got it
    How many units do you want?


```python
print(bot.respond('5', 1))
```

    Total cost is 300 Rs.
    


```python
bot.get_data(1)
```




    {'key2': {'data': 'hi'},
     'name': {'data': 'Testing'},
     'choice': {'data': [1, 'Hand Sanitizer']},
     'split1': {'pos': 'sanitize', 'sanitize': {'data': 'yes'}},
     'calculate': {'data': 300},
     'pos': 'key2'}



## Footer
