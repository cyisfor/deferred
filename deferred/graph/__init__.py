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
                stage = Node((id(self),len(self.callbacks)),"derp")
                contexts[stage] = list(reversed(traceback.extract_stack()[:-2]))
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
            frame = Node('{}:{}:{}'.format(*(frame[:3])),'{}:{}'.format(frame[2],frame[1]))
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
    doCTX = backtraceShower(graph)
    buddies = []
    stages = []
    with graph.subgraph('deferred') as dgraph:
        if not d.callbacks: return
        lastStage = None
        for stage in range(len(d.callbacks)):            
            stage = Node((id(d),stage),"stage {}".format(stage))
            dgraph.defers(d,stage)
            dgraph.nodes.add(stage)
            stages.append(stage)
            ctx = contexts.get(stage)
            if ctx:
                contexts.pop(stage)
                doCTX(stage,ctx)
            if lastStage is not None:
                dgraph.nextStage(stage,lastStage)
            lastStage = stage
    def process(side,errback=False):
        nonlocal graph
        if errback:
            name = 'errbacks'
        else:
            name = 'callbacks'
        side = tuple(tuple(i) for i in side)
        lastStage = None
        firstStage = None
        for stage,thing in enumerate(side):            
            if hasattr(thing[0],'__self__') and isinstance(thing[0].__self__,deferred.Deferred):
                thing = thing[0].__self__
                isDeferred = True
            else:
                isDeferred = False
            stage = stages[stage]
            with graph.subgraph(name) as subgraph:
                if errback:
                    subgraph.errback(stage,thing)
                else:
                    print('callback',stage,thing)
                    subgraph.callback(stage,thing)
                if isDeferred:
                    subgraph.chain(d,thing)
                    buddies.append(thing)
    process((thing[0] for thing in d.callbacks),False)
    process((thing[1] for thing in d.callbacks),True)
    for buddy in buddies:
        tree(buddy,graph)

def extra(graph):
    if len(contexts)==0: return
    doCTX = backtraceShower(graph)
    with graph.subgraph("extra"):
        for cb,ctx in contexts.items():
            doCTX(cb,ctx)
