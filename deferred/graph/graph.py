import deferred
import random

from contextlib import contextmanager
from itertools import count

from deferred._defer import passthru,Deferred

# XXX: this is so roundabout


def nameOf(node):
    if hasattr(node,'f_name'):
        return node.f_name
    elif hasattr(node,'__name__'):
        name = node.__name__
        if name == '<lambda>':
            co = node.__code__
            name = '<lambda '+co.co_filename+':'+str(co.co_firstlineno)+'>'
        return name
    elif hasattr(node,'f_code'):
        code = node.f_code
        label = '{}:{}'.format(code.co_filename,code.co_firstlineno)
        return label
    elif isinstance(node,int):
        return 'stage '+str(node)
    elif isinstance(node,str):
        return node
    elif isinstance(node,tuple):
        if node[0] is passthru: return
        return nameOf(node[0])
    elif isinstance(node,Deferred):
        return str(node)
    elif hasattr(node,'name'):
        return node.name
    else:
        raise RuntimeError(node,type(node),dir(node))

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
    def __init__(self,id,label=None):
        self.id = id
        self.name = str(id)
        if label is None:
            label = self.name
        self.label = label
    def __hash__(self):
        return hash(self.id)
    def __lt__(self,other):
        return self.id < other.id
    def __eq__(self,other):
        return self.id == other.id
    def __repr__(self):
        return repr(self.id)

tab = ' '

def defid(d):
    return '<Deferred '+hex(id(d))+'>'

colors = {
    'callbacks': 'seagreen1',
    'deferred': 'palegoldenrod',
    'errbacks': 'red',
    'extra': 'mediumpurple',
}

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
    def hashh(self,a):
        if isinstance(a,Node): return a
        try:
            return Node(hash(a),nameOf(a))
        except TypeError:
            return Node(id(a),nameOf(a))
    def defers(self,d,first):
        self.update(defid(d),first,'defers')
    def nextStage(self,last,current):
        self.update(last,current,'next')
    def chain(self,d,b):
        self.update(defid(d),b,'chain')
    def update(self,a,b,type):
        assert a is not None
        assert b is not None
        if a is passthru: return
        if b is passthru: return
        a = self.hashh(a)
        b = self.hashh(b)
        if not a.label or not b.label: return
        if (a,b,type) in self.relationships: return
        self.root.relationships.add((a,b,type))
        if self.root is not self:
            self.nodes.add(a)
            self.nodes.add(b)
    def header(self,a):
        self.headers.append(a)
    @contextmanager
    def subgraph(self,name=''):
        print('subgraph',self.sub,name)
        sub = Graph(self,self.root,sub=name)
        sub.header("color={};\n".format(colors.get(name,'blue')))
        sub.header("label="+name+";\n")
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
            self.write("subgraph cluster{}_{} ".format(self.sub,next(counter))+ '{ \n')
        else:
            self.write('digraph {\n')
        self.level += 1
        for node in self.nodes:
            if not node in self.root.donedid:
                self.write('"'+node.name+'" [label="'+node.label+'"]'+'\n')
                self.root.donedid.add(node)
        for sub in self.subs:
            print(self.level)
            sub.level = self.level
            sub.finish()
        for header in self.headers:
            self.write(header)
        for a,b,type in self.relationships:
            self.write('"{}" -> "{}" {}\n'.format(a,b,info(type)))
        print('-')
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

