import re
from conv import ONE,log
NUC={'aa','ae','ah','ao','aw','ax','ay','eh','ey','ih','ix','iy','ow','oy','uh','uw','yu','rr','ir','er','ar','or','ur','el','en'}
def parse(lg):
    arp=[];wid=[];sylls=[];w=0
    for line in lg.splitlines():
        m=re.match(r'\[:syll\s+.*?-->\s*(.*)\]\s*$',line)
        if m:sylls.append(m.group(1).strip());continue
        for chunk in re.split(r'\s{2,}|[,.!?;:]',line):
            ph=re.findall(r'us_((?:(?!us_)[a-z])+)',chunk)
            if ph:arp+=ph;wid+=[w]*len(ph);w+=1
    # syllable boundary flags from the syllable log, aligned to the phoneme sequence
    brk=[False]*len(arp);j=0
    for s in sylls:
        pend=False
        for c in s:
            if c=='-':pend=True;continue
            nm=ONE.get(c)
            if nm is None or j>=len(arp):continue
            if arp[j]!=nm:
                if c=='^':continue
                k=next((k for k in range(j,min(j+3,len(arp))) if arp[k]==nm),None)
                if k is not None:j=k
            if pend:brk[j]=True;pend=False
            j+=1
    words=[]
    for i,ph in enumerate(arp):
        if i==0 or wid[i]!=wid[i-1]:words.append([[]])
        elif brk[i]:words[-1].append([])
        words[-1][-1].append(ph)
    # fold vowel-less fragments into a neighbour inside the same word
    out=[]
    for wd in words:
        sy=[s for s in wd if s]
        k=0
        while k<len(sy):
            if not any(p in NUC for p in sy[k]) and len(sy)>1:
                if k+1<len(sy):sy[k+1]=sy[k]+sy[k+1]
                else:sy[k-1]=sy[k-1]+sy[k]
                sy.pop(k);continue
            k+=1
        out.append(sy)
    return out
