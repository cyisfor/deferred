import deferred.graph as g
import deferred as d

def callbackA(e): return e
def errbackA(e): return e
def errbackB(e): return e 
def callbackC(e): return e
def errbackC(e): return e

class Deferred(d.Deferred):
    def __init__(self,name):
        super().__init__()
        self._name = name
    def __str__(self):
        return 'deferred '+self._name
    def __repr__(self):
        return '<Deferred '+self._name+'>'

def main():
    with g.graph('test') as graph:
        a = Deferred('A')
        b = Deferred('B')
        c = Deferred('C')
        a.addCallback(callbackA)
        b.addErrback(errbackB)
        a.addErrback(errbackA)
        c.addCallbacks(callbackC,errbackC)
        a.chainDeferred(b)
        b.chainDeferred(c)
        g.tree(a,graph)
        g.extra(graph)
main()
