import subprocess,re
ONE={'e':'ey','a':'aa','i':'iy','E':'eh','A':'ay','I':'ih','O':'oy','o':'ow','u':'uw','^':'ah','W':'aw','Y':'yu','R':'rr','c':'ao','@':'ae','U':'uh','|':'ix','x':'ax',
 'p':'p','t':'t','k':'k','f':'f','T':'th','s':'s','S':'sh','C':'ch','w':'w','y':'yx','h':'hx','l':'ll','L':'el','N':'en','b':'b','d':'d','g':'g','v':'v','D':'dh','z':'z','Z':'zh','J':'jh',
 'm':'m','n':'n','G':'nx','r':'r','q':'q','Q':'tx','&':'dx','F':'df','B':'ir','K':'er','P':'ar','M':'or','j':'ur'}
p=subprocess.Popen(['/home/claude/engine/dtserver-x86'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd='/tmp/rt');p.stdout.readline()
def log(text):
    p.stdin.write(f'PHON\t/tmp/rt/lg.txt\t18\t{text}\n');p.stdin.flush();p.stdout.readline();return open('/tmp/rt/lg.txt',encoding='latin1').read()
def parse(lg):
    arp=[];sylls=[]
    for line in lg.splitlines():
        m=re.match(r'\[:syll\s+.*?-->\s*(.*)\]\s*$',line)
        if m:sylls.append(m.group(1).strip())
        else:arp+=re.findall(r'us_((?:(?!us_)[a-z])+)',line)
    j=0;words=[];issues=0
    for w in sylls:
        cur=[];out=[]
        for c in w:
            if c=='-':
                if cur:out.append(cur);cur=[]
                continue
            nm=ONE.get(c)
            if nm is None:continue
            if j<len(arp) and arp[j]==nm:cur.append(nm);j+=1;continue
            if c=='^':continue           # phrase marker, not the 'ah' vowel
            # allophone or inserted phoneme: look a little ahead in the phoneme log
            ahead=next((k for k in range(j,min(j+3,len(arp))) if arp[k]==nm),None)
            if ahead is not None:
                cur+=arp[j:ahead+1] if False else [nm];j=ahead+1;issues+=1;continue
            if j<len(arp):cur.append(arp[j]);j+=1;issues+=1   # substituted allophone
        if cur:out.append(cur)
        if out:words.append(out)
    return words,issues,len(arp)-j
