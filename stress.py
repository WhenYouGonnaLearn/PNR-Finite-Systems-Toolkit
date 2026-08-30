import random,tempfile,sys
from pnr12 import PNR,canonical,digest
random.seed(1337)
# Canonical persistence fuzz including nested typed containers.
for i in range(300):
 d=tempfile.mkdtemp();p=PNR(d);vals=[None,True,False,i,-i,i/7,"s"+str(i),bytes([i%256]),(i,i+1),frozenset({i,i+1})]
 x={"a":[random.choice(vals) for _ in range(4)],frozenset({1,2}):random.choice(vals)}
 e=p.add_evidence(x,["x"],[f"r{i}"]);q=PNR(d)
 assert digest(q.evidence[e]["value"])==digest(x);assert q.audit()["status"]=="PASS"
# Random finite unary languages + huge-step lifting vs independent cycle reference.
for i in range(200):
 n=random.randint(2,5);dom=list(range(n));mapping=[random.randrange(n) for _ in dom];rows=[{"in":[x],"out":mapping[x]} for x in dom]
 p=PNR(tempfile.mkdtemp());g=p.generate_finite_extension("PNR12_BASE",f"f{i}",[dom],dom,rows[:-1],rows[-1:]);h=random.randint(0,10**6);a=p.compile_generated_algorithm(g["language_id"],f"f{i}",h);start=random.choice(dom);out=p.externalize(p.run_generated_algorithm(a["artifact_id"],start,h),reason="stress")
 seen={};seq=[];x=start
 while x not in seen:seen[x]=len(seq);seq.append(x);x=mapping[x]
 mu=seen[x];cyc=seq[mu:];x=seq[h] if h<len(seq) else cyc[(h-mu)%len(cyc)]
 assert out==x;assert p.audit()["status"]=="PASS"
print('stress PASS: 300 persistence fuzz + 200 generated-transition differential cases')
