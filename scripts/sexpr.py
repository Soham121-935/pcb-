import re
def tokenize(s):
    i=0;n=len(s)
    while i<n:
        c=s[i]
        if c in ' \t\r\n': i+=1; continue
        if c=='(': yield '('; i+=1; continue
        if c==')': yield ')'; i+=1; continue
        if c=='"':
            j=i+1; buf=[]
            while True:
                ch=s[j]
                if ch=='\\': buf.append(s[j+1]); j+=2; continue
                if ch=='"': break
                buf.append(ch); j+=1
            yield ('STR',''.join(buf)); i=j+1; continue
        j=i
        while j<n and s[j] not in ' \t\r\n()': j+=1
        yield s[i:j]; i=j
def parse(s):
    toks=list(tokenize(s)); pos=0
    def rd():
        nonlocal pos
        t=toks[pos]; pos+=1
        if t=='(':
            lst=[]
            while toks[pos]!=')':
                lst.append(rd())
            pos+=1
            return lst
        if isinstance(t,tuple): return ('S',t[1])
        return ('A',t)
    return rd()
def val(x):
    if isinstance(x,tuple): return x[1]
    return x
def find(node,key):
    return [c for c in node if isinstance(c,list) and c and c[0]==('A',key)]
def first(node,key):
    r=find(node,key); return r[0] if r else None
