# AUTOGENERATED! DO NOT EDIT! File to edit: multiprocess-bot.ipynb (unless otherwise specified).

__all__ = ['get_chained_data', 'set_chained_data', 'tryint', 'CHAT_RET', 'Pipe', 'Segment', 'ValidatedSegment',
           'MultiChoiceSegment', 'ComputeSegment', 'Composite', 'LoopComposite', 'TextAdapter', 'Splitter',
           'SkipSplitter']

# Cell
import redis
import enum
import json
import re

# Cell
def get_chained_data(data, *keys):
    d = data
    for key in keys:
        if key not in d:
            return None
        d = d[key]
    return d

def set_chained_data(data, *keys, val=0):
    d = data
    for key in keys[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]
    d[keys[-1]] = val


# Cell
def tryint(x):
    try:
        return int(x)
    except:
        return -1


# Cell
class CHAT_RET(enum.Enum):
    STAY = 0
    NEXT = 1

# Cell
class Pipe:
    def __init__(self, on_question=None, on_answer=None):
        self.key = ''
        self.next = None
        self.on_question = on_question
        self.on_answer = on_answer

    def __repr__(self):
        return f'{type(self)}: {self.key}'

    def question(self):
        pass

    def answer(self, resp):
        pass

# Cell
class Segment(Pipe):
    def __init__(self, key, q, a, **kwargs):
        super().__init__(**kwargs)
        self.q = q
        self.a = a
        self.key = key

    def question(self, data):
        if self.on_question:
            self.on_question(data)
        return {'txt': self.q}

    def answer(self, resp, data):
        data['data'] = resp
        if self.on_answer:
            self.on_answer(data)
        return CHAT_RET.NEXT, {'txt': self.a}


# Cell
class ValidatedSegment(Segment):
    def __init__(self, key, q, a, errmsg, valid_fn):
        super().__init__(key, q, a)
        self.err = errmsg
        self.valid_fn = valid_fn

    def answer(self, resp, data):
        if self.valid_fn(resp):
            return super().answer(resp, data)
        data['data'] = ''
        return CHAT_RET.STAY, {'txt': self.err}


# Cell
class MultiChoiceSegment(Segment):
    def __init__(self, key, q, resp_lst, ans, **kwargs):
        super().__init__(key, q, ans, **kwargs)
        self.resp_lst = resp_lst

    def question(self, data):
        return {'txt': self.q + '\n' + '\n'.join([f'{i+1}. {q}' for (i,q) in enumerate(self.resp_lst)])}

    def answer(self, resp, data):
        if 0 < tryint(resp) <= len(self.resp_lst):
            data['data'] = (tryint(resp) - 1, self.resp_lst[tryint(resp) - 1])
            return CHAT_RET.NEXT, {'txt': self.a}
        return CHAT_RET.STAY, {'txt': f'Please enter one of 1..{len(self.resp_lst)} as answer'}


# Cell
class ComputeSegment(Segment):
    def answer(self, resp, data):
        return super().answer(resp, data)

# Cell
class Composite(Pipe):
    def __init__(self, key, *args):
        super().__init__()
        for i in range(len(args) - 1):
            args[i].next = args[i+1]

        self.args = args
        self.key = key

        self.nodes = {}
        for a in args:
            self.nodes[a.key] = a

    def getpos(self, data):
        pos = get_chained_data(data, 'pos')
        if pos is None:
            pos = self.args[0].key
            set_chained_data(data, 'pos', val=pos)

        return self.nodes[pos]

    def setpos(self, data, pos):
        set_chained_data(data, 'pos', val=pos.key)

    def getdata(self, data, key):
        val = get_chained_data(data, key)
        if val is None:
            val = {}
            set_chained_data(data, key, val=val)
        return val

    def question(self, data):
        cur = self.getpos(data)
        print(f'composite question current {cur.key} data {data}')
        curdata = self.getdata(data, cur.key)

        if isinstance(cur, Splitter):
            q = cur.question(data)
        else:
            q = cur.question(curdata)

        return q

    def move(self, cur, cmd, data):
        if cmd == CHAT_RET.NEXT:
            nxt = cur.next
            if nxt == None: # self.args[-1]:
                data.pop('pos')
                return CHAT_RET.NEXT
        else:
            nxt = cur

        self.setpos(data, nxt)
        return CHAT_RET.STAY

    def answer(self, resp, data):
        cur = self.getpos(data)
        print(f'composite answer current {cur.key} data {data}')
        curdata = self.getdata(data, cur.key)

        if isinstance(cur, SkipSplitter):
            if cur.decider_fn(data) == 1:
                mov, ans = cur.answer(resp, data)
                return self.move(cur, mov, data), ans
            else:
                cur = cur.next
                self.setpos(data, cur)
                curdata = self.getdata(data, cur.key)

        if isinstance(cur, Splitter):
            mov, ans = cur.answer(resp, data)
        elif isinstance(cur, ComputeSegment):
            mov, ans = cur.answer(resp, data)
        else:
            mov, ans = cur.answer(resp, curdata)
        return self.move(cur, mov, data), ans


# Cell
class LoopComposite(Composite):
    def move(self, cur, cmd, data):
        if cmd == CHAT_RET.NEXT:
            nxt = cur.next
            if nxt == None: # self.args[-1]:
                data.pop('pos')
                return CHAT_RET.STAY
        else:
            nxt = cur

        self.setpos(data, nxt)
        return CHAT_RET.STAY

# Cell
class TextAdapter(Pipe):
    def __init__(self, root):
        super().__init__()
        self.root = root
        self.r = redis.Redis()

    def respond(self, inp, session):
        if self.r.exists(session):
            data = json.loads(self.r.get(session))
        else:
            data = {}
        n, d1 = self.root.answer(inp, data)
#         if n == CHAT_RET.NEXT:
#             data.pop('pos')
        d2 = self.root.question(data)
        print(f'adapter data {data}')
        self.r.set(session, json.dumps(data))
        return f"{d1['txt']}\n{d2['txt']}"

# Cell
class Splitter(Pipe):
    def __init__(self, key, *branches, decider_fn=lambda _: 0, default = 0):
        super().__init__()
        self.key = key
        self.branches = branches
        self.nodes = {}
        for a in branches:
            self.nodes[a.key] = a

        self.default = default
        self.decider_fn = decider_fn

    def decide(self, data):
        '''
        Based on parent level data decide branch and return branch key
        '''
        val = self.decider_fn(data)
        print(f'decider {self.key} {val}')
        if val >= len(self.branches):
            val = self.default
        self.branches[val].next = self.next
        return self.branches[val].key

    def question(self, data):
        '''
        Parent data for splitter
        '''
        print(f'splitter question data {data}')
        pos = self.decide(data)
        set_chained_data(data, self.key, 'pos', val = pos)
        print(f'splitter question data after pos set {self.key} {pos} {data}')
        cur = self.nodes[pos]
        curdata = get_chained_data(data, self.key, cur.key)
        if curdata is None:
            curdata = {}
            set_chained_data(data, self.key, cur.key, val=curdata)
        return cur.question(curdata)

    def answer(self, resp, data):
        print(f'splitter answer data {data}')
        pos = self.decide(data)
        set_chained_data(data, self.key, 'pos', val = pos)

        cur = self.nodes[pos]

        curdata = get_chained_data(data, self.key, cur.key)
        if curdata is None:
            curdata = {}
            set_chained_data(data, self.key, cur.key, val=curdata)

        mov, ans = cur.answer(resp, curdata)

        if mov == CHAT_RET.NEXT:
            return CHAT_RET.NEXT, ans

        return CHAT_RET.STAY, ans


# Cell
class SkipSplitter(Splitter):
    def __init__(self, key, branch, decider_fn=lambda _: 0, default = 0):
        super().__init__(key, branch, decider_fn=decider_fn, default=default)

    def decide(self, data):
        '''
        Based on parent level data decide if branch to be taken
        '''
        val = self.decider_fn(data)
        return val

    def getpos(self, data):
        if (self.key in data) and  ('pos' in data[self.key]):
            return self.nodes[data[self.key]['pos']]

        data[self.key]['pos'] = self.branches[0].key
        return self.branches[0]

    def setpos(self, data, pos):
        data['pos'] = pos.key

    def getdata(self, data, key):
        if self.key in data:
            if key in data[self.key]:
                return data[self.key][key]
            else:
                data[self.key][key] = {}
                return data[self.key][key]
        data[self.key] = {}
        data[self.key][key] = {}
        return data[self.key][key]

    def question(self, data):
        '''
        Parent data for splitter
        '''
        print(f'skip question data {data}')
        if self.decide(data) == 1:
            # take branch
            cur = self.getpos(data)
            curdata = self.getdata(data, cur.key)
            return cur.question(curdata)
        else:
            # skip branch
            data['pos'] = self.next.key
            return self.next.question({})

    def answer(self, resp, data):
        print(f'skip answer data {data}')
        cur = self.getpos(data)
        curdata = self.getdata(data, cur.key)

        mov, ans = cur.answer(resp, curdata)

        if mov == CHAT_RET.NEXT:
            return CHAT_RET.NEXT, ans

        return CHAT_RET.STAY, ans
