import deferred
import random

from contextlib import contextmanager
from itertools import count

from deferred._defer import passthru,Deferred

def info(type):
    if type == 'errback':
        return '[color="0.0,1.0,1.0",label="errback",w=2.0,len=5]'
    elif type == 'function':
        return '[color="0.4,1.0,1.0",label="added by",w=1.0,len=2]'
    elif type == 'back':
        return '[color="0.8,1.0,1.0",label="back",w=1.0,len=2]'
    elif type== 'next':
        return '[color="0.0,0.0,0.0",label="next",w=2.0,len=1]'
    elif type == 'callback':
        return '[color="0.6,1.0,1.0",w=1.0,len=2,label="callback"]'
    elif type == 'same':
        return '[color="0.0,0.0,0.5",w=1.0,label="same"]'
    elif type == 'defers':
        return '[color="0.5,0.0,0.5",w=1.0,label="defers"]'
    elif type == 'chain':
        return '[color="0.5,0.5,0.5",w=1.0,label="chains"]'
    else:
        raise RuntimeError("What is",type)

from functools import total_ordering
@total_ordering
class Node:
    def __init__(self,id,label=None,comment=None):
        self.id = id
        self.name = str(id)
        self.comment = comment
        if label is None:
            label = self.labelOf(self.id)
        self.label = label
    def __hash__(self):
        return hash(repr(self.id))
    def __lt__(self,other):
        return self.id < other.id
    def __eq__(self,other):
        return self.id == other.id
    def __repr__(self):
        return repr(self.id)
    def labelOf(self,what):
        if hasattr(what,'label'):
            return what.label
        elif hasattr(what,'f_name'):
            return what.f_name
        elif hasattr(what,'__name__'):
            name = what.__name__
            if name == '<lambda>':
                co = what.__code__
                name = '<lambda '+co.co_filename+':'+str(co.co_firstlineno)+'>'
            return name
        elif hasattr(what,'name'):
            return what.name
        elif hasattr(what,'f_code'):
            code = what.f_code
            label = '{}:{}'.format(code.co_filename,code.co_firstlineno)
            return label
        elif isinstance(what,int):
            return 'intoderp '+str(what)
        elif isinstance(what,str):
            return what
        elif isinstance(what,tuple):
            if what[0] is passthru: return
            return self.labelOf(what[0]) + '+ args'
        elif hasattr(what,'name'):
            return what.name
        else:
            return str(what)
            #raise RuntimeError(self,type(node),dir(node))

tab = ' '

colors = {
    'callbacks': 'seagreen1',
    'deferred': 'yellow',
    'errbacks': 'red',
    'extra': 'mediumpurple',
}

def colorOf(what):
    if isinstance(what,Deferred):
        return colors['deferred']
    return colors.get(what,'blue')

def toNode(a):
    if isinstance(a,Node): return a
    return Node(a)

counter = count(0)

class Graph:
    buffering = False
    gotSub = False
    level = 0
    def __init__(self,dest,root=None,sub=False):
        if root is None:
            self.root = self
        else:
            self.root = root
        self.dest = dest
        self.nodes = set()
        self.relationships = set()
        self.counter = 0
        self.sub = sub
        self.subs = []
        self.headers = []
    def write(self,what):
        if self.level:
            self.dest.write(tab*self.level)
        self.dest.write(what)
    def defers(self,d,first):
        self.update(d,first,'defers')
    def nextStage(self,current,last):
        self.update(last,current,'next')
    def chain(self,d,b):
        self.update(d,b,'chain')
    def update(self,a,b,type):
        assert a is not None
        assert b is not None
        if a is passthru: return
        if b is passthru: return
        if hasattr(a,'__getitem__') and a[0] is passthru: return
        if hasattr(b,'__getitem__') and b[0] is passthru: return
        a = toNode(a)
        b = toNode(b)
        if not a.label or not b.label: return
        self.root.relationships.add((a,b,type))
        self.nodes.add(a)
        self.nodes.add(b)
    def header(self,a):
        self.headers.append(a)
    @contextmanager
    def subgraph(self,titular=''):
        titular = toNode(titular)
        sub = Graph(self,self.root,sub=titular)
        sub.nodes.add(titular)
        sub.header("color={};\n".format(colorOf(titular.id)))
        sub.header('label="'+titular.label+'";\n')
        self.subs.append(sub)
        yield sub
    def callback(self,stage,cb):
        self.update(stage,cb,'callback')
    def errback(self,stage,eb):
        self.update(stage,eb,'errback')
    def function(self,cb,ctx):
        self.update(cb,ctx,'function')
    def back(self,low,high):
        self.update(low,high,'back')
    donedid = None
    def finish(self):
        if self.root.donedid is None:
            self.root.donedid = set()
        dest = self.dest
        if self.sub:
            self.write("subgraph /* {} */ cluster_{} ".format(self.sub.label,next(counter))+ '{ \n')
        else:
            self.write('digraph {\n')
        self.level += 1

        for sub in self.subs:
            sub.level = self.level
            sub.finish()
        for node in self.nodes:
            if not node in self.root.donedid:
                self.write('"'+repr(node)+'" [label="'+node.label+'"]')
                if node.comment:
                    self.write('/* '+node.comment.replace('/*','..').replace('*/','..')+' */')
                self.write('\n')
                self.root.donedid.add(node)
        for header in self.headers:
            self.write(header)
        for a,b,type in self.relationships:
            self.write('"{}" -> "{}" {}\n'.format(a,b,info(type)))
        self.level -= 1
        self.write('}\n')

from contextlib import contextmanager
@contextmanager
def graph(path):
    with open(path,'wt') as out:
        g = None
        try:
            g = Graph(out)
            yield g
        finally:
            if g:
                g.finish()

