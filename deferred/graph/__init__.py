#import locator
from graph import Node,graph
import deferred
from deferred._defer import passthru

from functools import reduce

import traceback
import sys

contexts = {}

oldacbs = deferred.Deferred.addCallbacks
def newacbs(self, callback, errback=None,
                     callbackArgs=None, callbackKeywords=None,
                     errbackArgs=None, errbackKeywords=None):
    for cb in (callback,errback):
        if cb:
            if cb is passthru: continue
            try:
                raise ZeroDivisionError
            except ZeroDivisionError:
                stage = Node((self,len(self.callbacks)),"derp")                
                stack = traceback.extract_stack()[:-1]
                print(repr(stack[-1][2]))
                if stack and stack[-1][2] in ('addCallback','addErrback','chainDeferred'):
                    stack = stack[:-1]
                stack.reverse()
                contexts[stage] = stack
    return oldacbs(self,callback,errback,callbackArgs,callbackKeywords,errbackArgs,errbackKeywords)
if oldacbs is not newacbs:
    deferred.Deferred.addCallbacks = newacbs

oldcallback = deferred.Deferred.callback

def backtraceShower(graph):
    def doCTX(cb,tb):
        nonlocal graph
        lastFrame = None
        firstFrame = None
        for frame in tb:
            frame = Node('{}:{}:{}'.format(*(frame[:3])),'{}:{}'.format(frame[0],frame[1]),comment="{} ({})".format(frame[3],frame[2]))
            if lastFrame:
                graph.back(lastFrame,frame)
            lastFrame = frame
            if not firstFrame:
                firstFrame = frame
        if firstFrame:
            graph.function(cb,firstFrame)
    return doCTX

deferred.Deferred.graphed = False

def tree(d,graph):
    if d.graphed: return
    d.graphed = True
    if not d.callbacks: return
    buddies = []
    stages = []

    def process(create,chain,stage,thing):
        if hasattr(thing[0],'__self__') and isinstance(thing[0].__self__,deferred.Deferred):
            thing = thing[0].__self__
            isDeferred = True
        else:
            isDeferred = False
        if isDeferred:
            chain(stage,thing)
            buddies.append(thing)
        else:
            create(stage,thing)
    doCTX = backtraceShower(graph)
    with graph.subgraph(d) as dgraph:
        if not d.callbacks: return
        lastStage = None
        
        for stage,(callback,errback) in enumerate(d.callbacks):
            stage = Node((d,stage),"stage {}".format(stage))
            dgraph.defers(d,stage)
            with dgraph.subgraph(stage) as subgraph:
                process(subgraph.callback,subgraph.chain,stage,callback)
                process(subgraph.errback,subgraph.chain,stage,errback)
            ctx = contexts.get(stage)
            if ctx:
                contexts.pop(stage)
                doCTX(stage,ctx)
            if lastStage is not None:
                dgraph.nextStage(stage,lastStage)
            lastStage = stage
    for buddy in buddies:
        tree(buddy,graph)

def extra(graph):
    if len(contexts)==0: return
    doCTX = backtraceShower(graph)
    with graph.subgraph("extra"):
        for cb,ctx in contexts.items():
            doCTX(cb,ctx)
