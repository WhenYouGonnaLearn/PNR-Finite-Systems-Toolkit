from __future__ import annotations
import hashlib, itertools, json, math, os
from dataclasses import dataclass, field
from collections import namedtuple
from enum import Enum
from pathlib import Path
VERSION="1.3.0";SCHEMA="pnr12.v1.3.0";UNIT=1e-4;MAX_SEARCH=10**5;EXACT="EXACT_UNDER_ASSUMPTIONS";RETRACTED="RETRACTED_BY_COUNTEREXAMPLE";DEAD=("PROPOSED",RETRACTED)
class PNRError(RuntimeError):
    def __init__(self,kind:str,**detail): super().__init__(kind); self.kind=kind; self.detail=detail
    def to_dict(self): return {"kind":self.kind,**self.detail}
Residual=PNRError
def _form(x):
    if x is None:return ["n"]
    if isinstance(x,bool):return ["b",x]
    if isinstance(x,int):return ["i",str(x)]
    if isinstance(x,float):
        if not math.isfinite(x):raise TypeError("non-finite float")
        return ["f",x.hex()]
    if isinstance(x,str):return ["s",x]
    if isinstance(x,bytes):return ["y",x.hex()]
    if isinstance(x,list):return ["l",[_form(v) for v in x]]
    if isinstance(x,tuple):return ["t",[_form(v) for v in x]]
    if isinstance(x,set):return ["e",sorted((_form(v) for v in x),key=lambda v:json.dumps(v,separators=(",",":")))]
    if isinstance(x,frozenset):return ["r",sorted((_form(v) for v in x),key=lambda v:json.dumps(v,separators=(",",":")))]
    if isinstance(x,dict):return ["d",sorted(([_form(k),_form(v)] for k,v in x.items()),key=lambda v:json.dumps(v[0],separators=(",",":")))]
    if isinstance(x,Enum):return ["m",x.__class__.__name__,_form(x.value)]
    raise TypeError(f"unsupported value: {type(x).__name__}")
def _unform(f):
    t=f[0]
    if t=="n":return None
    if t=="b":return bool(f[1])
    if t=="i":return int(f[1])
    if t=="f":return float.fromhex(f[1])
    if t=="s":return f[1]
    if t=="y":return bytes.fromhex(f[1])
    if t=="l":return [_unform(v) for v in f[1]]
    if t=="t":return tuple(_unform(v) for v in f[1])
    if t=="e":return set(_unform(v) for v in f[1])
    if t=="r":return frozenset(_unform(v) for v in f[1])
    if t=="d":return {_unform(k):_unform(v) for k,v in f[1]}
    if t=="m":return _unform(f[2])
    raise ValueError("bad canonical tag")
def canonical(x): return json.dumps(_form(x),separators=(",",":"),ensure_ascii=False).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def _same(a,b): return digest(a)==digest(b)
def _clone(x): return _unform(_form(x))
def _reject(test,kind,**detail):
    if test:raise Residual(kind,**detail)
class _FD(dict):
    def _no(self,*a,**k): raise TypeError("record is immutable")
    __setitem__=__delitem__=clear=pop=popitem=setdefault=update=__setattr__=_no
    def __getattr__(self,n):
        try:return self[n]
        except KeyError as e:raise AttributeError(n) from e
class _FL(list):
    def _no(self,*a,**k): raise TypeError("record is immutable")
    __setitem__=__delitem__=append=clear=extend=insert=pop=remove=reverse=sort=__iadd__=__imul__=_no
def _freeze(x):
    if x is None or isinstance(x,(bool,int,float,str,bytes)):return x
    if isinstance(x,dict):return _FD({_freeze(k):_freeze(v) for k,v in x.items()})
    if isinstance(x,list):return _FL([_freeze(v) for v in x])
    if isinstance(x,tuple):return tuple(_freeze(v) for v in x)
    if isinstance(x,(set,frozenset)):return frozenset(_freeze(v) for v in x)
    raise TypeError(type(x).__name__)
def _ids(v,field="ids"):
    if v is None:return ()
    if isinstance(v,str):v=(v,)
    try:v=tuple(v)
    except TypeError as e:raise Residual("IDENTIFIER_LIST_INVALID",field=field) from e
    if any(not isinstance(x,str) or not x for x in v):raise Residual("IDENTIFIER_INVALID",field=field)
    return tuple(sorted(set(v)))
def _safe_keys(values,field="carrier"):
    vals=list(values); ds=[digest(v) for v in vals]
    if len(ds)!=len(set(ds)):raise Residual("CANONICAL_CARRIER_DUPLICATE",field=field)
    try:n=len(set(vals))
    except TypeError as e:raise Residual("PYTHON_KEY_UNHASHABLE",field=field) from e
    if n!=len(vals):raise Residual("PYTHON_KEY_SEMANTIC_COLLISION",field=field)
    return vals
Occurrence=namedtuple("Occurrence","seq occurrence_id kind payload parents prev_digest record_digest")
ProposalLanguage=namedtuple("ProposalLanguage","language_id parent_language_id primitives generated_primitives status bridge_certificate_id assumptions validity_scope artifact_dependencies counterexamples",defaults=[(),"PROPOSED",None,(),None,(),()])
GeneratedArtifact=namedtuple("GeneratedArtifact","artifact_id artifact_kind language_id program assumptions validity_scope artifact_dependencies standing certificate_id counterexamples",defaults=[(),None,(),"PROPOSED",None,()])
@dataclass(frozen=True,eq=False)
class ProducedValue:
    _value:object=field(repr=False); artifact_id:str=""; occurrence_id:str=""
    def __repr__(self):return f"ProducedValue(by={self.artifact_id!r}, occurrence={self.occurrence_id!r})"
    def __bool__(self):raise TypeError("tracked output is opaque; externalize it first")
    def __eq__(self,o):
        if isinstance(o,ProducedValue):return (self.artifact_id,self.occurrence_id)==(o.artifact_id,o.occurrence_id)
        raise TypeError("tracked output is opaque; externalize it first")
    def __hash__(self):return hash((self.artifact_id,self.occurrence_id))
_ST=(EXACT,*"BOUNDED_UNDER_ASSUMPTIONS CALIBRATED_EMPIRICAL HELDOUT_EMPIRICAL SUPPORTED_HYPOTHESIS UNRESOLVED_EQUIVALENCE_CLASS TYPED_RESIDUAL".split(),RETRACTED)
StandingKind=Enum("StandingKind",{x:x for x in _ST},type=str)
ClaimStanding=namedtuple("ClaimStanding","claim_id kind scope assumptions evidence_roots dependency_status sufficiency_coverage verifier counterexample_status",defaults=["CLEAR"])
@dataclass(frozen=True)
class Experiment:
    experiment_id:str; cost:float=1.0; risk:float=0.0; irreversible:bool=False
    def __post_init__(self):
        if not isinstance(self.experiment_id,str) or not self.experiment_id:raise ValueError("experiment_id must be non-empty")
        if not isinstance(self.irreversible,bool):raise ValueError("irreversible must be bool")
        for n,v in (("cost",self.cost),("risk",self.risk)):
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)) or v<0:raise ValueError(f"{n} invalid")
BASE={
 "identity_bool":{"kind":"finite_table","domains":[[False,True]],"codomain":[False,True],"table":[{"in":[False],"out":False},{"in":[True],"out":True}]},
 "not_bool":{"kind":"finite_table","domains":[[False,True]],"codomain":[False,True],"table":[{"in":[False],"out":True},{"in":[True],"out":False}]},
}
class Bridge:
    def check_primitive(self,s):
        if not isinstance(s,dict) or s.get("kind")!="finite_table":raise Residual("BRIDGE_PRIMITIVE_KIND_UNSUPPORTED",primitive_kind=s.get("kind") if isinstance(s,dict) else None)
        d,c,t=s.get("domains"),s.get("codomain"),s.get("table")
        if not isinstance(d,list) or not d or not isinstance(c,list) or not c or not isinstance(t,list):raise Residual("BRIDGE_MALFORMED_PRIMITIVE")
        for q in d:
            if not isinstance(q,list) or not q:raise Residual("BRIDGE_DOMAIN_REQUIRED")
            if len({digest(x) for x in q})!=len(q):raise Residual("BRIDGE_DOMAIN_DUPLICATE")
        if len({digest(x) for x in c})!=len(c):raise Residual("BRIDGE_CODOMAIN_DUPLICATE")
        rows=[list(x) for x in itertools.product(*d)];want={digest(x) for x in rows};codes={digest(x) for x in c}
        if len(t)!=len(rows):raise Residual("BRIDGE_TABLE_NOT_TOTAL",expected=len(rows),actual=len(t))
        got={}
        for r in t:
            if not isinstance(r,dict) or not isinstance(r.get("in"),list) or "out" not in r:raise Residual("BRIDGE_TABLE_ROW_MALFORMED")
            k=digest(r["in"]);
            if k in got:raise Residual("BRIDGE_TABLE_NOT_FUNCTION")
            if k not in want:raise Residual("BRIDGE_TABLE_INPUT_OUTSIDE_DOMAIN")
            if digest(r["out"]) not in codes:raise Residual("BRIDGE_TABLE_OUTPUT_OUTSIDE_CODOMAIN")
            got[k]=r["out"]
        return {"semantic_digest":digest(sorted(((k,digest(v)) for k,v in got.items()))),"rows":len(rows),"arity":len(d)}
    def check_language(self,p):return {"primitives":{n:self.check_primitive(s) for n,s in sorted(p.items())},"semantic_digest":digest({n:self.check_primitive(s) for n,s in sorted(p.items())})}
    def evaluate_primitive(self,s,args):
        self.check_primitive(s); k=digest(list(args))
        for r in s["table"]:
            if digest(r["in"])==k:return _clone(r["out"])
        raise Residual("BRIDGE_INPUT_OUTSIDE_DOMAIN",input=args)
class PNR:
    def __init__(self,state_dir,*,expect_digest=None,expect_anchor=None):
        self.path=Path(state_dir);self.path.mkdir(parents=True,exist_ok=True);self.log=self.path/"occurrences.jsonl";self.watermark=self.path/".pnr12-high-water.json";self.lockfile=self.path/".pnr12.lock";self.bridge=Bridge();self._watermark_degraded=False
        self._occ=[];self.by_id={};self.languages={};self.artifacts={};self._certs={};self._artifact_certs={};self._outputs={};self.resource_used=0.0;self.resource_limit=float("inf");self._resource_contract_set=False
        self._load();self._rebuild();self._seal();self._install_base();self._validate_watermark();self._validate_external(expect_digest,expect_anchor);self._seal()
    @property
    def occurrences(self):return tuple(self._occ)
    def _seal(self):
        self._resource_seal=digest((self.resource_used,"inf" if math.isinf(self.resource_limit) else self.resource_limit,self._resource_contract_set));self._reason_seal=digest(self._reason_state());self._authority_seal=digest(self.authority)
    def _check_seals(self):
        if self._resource_seal!=digest((self.resource_used,"inf" if math.isinf(self.resource_limit) else self.resource_limit,self._resource_contract_set)):raise Residual("RESOURCE_STATE_MUTATED_OUT_OF_BAND")
        if self._reason_seal!=digest(self._reason_state()):raise Residual("REASONING_STATE_MUTATED_OUT_OF_BAND")
        if self._authority_seal!=digest(self.authority):raise Residual("AUTHORITY_STATE_MUTATED_OUT_OF_BAND")
    def _encode(self,o):return json.dumps({"seq":o.seq,"id":o.occurrence_id,"kind":o.kind,"payload":_form(dict(o.payload)),"parents":list(o.parents),"prev":o.prev_digest,"hash":o.record_digest},separators=(",",":"))+"\n"
    def _decode(self,line):
        try:r=json.loads(line);p=_unform(r["payload"]);core={"seq":r["seq"],"kind":r["kind"],"payload":p,"parents":r["parents"],"prev":r["prev"]};h=digest(core)
        except Exception as e:raise Residual("OCCURRENCE_LOG_PARSE_ERROR") from e
        if h!=r.get("hash"):raise Residual("OCCURRENCE_HASH_INVALID")
        return Occurrence(r["seq"],r["id"],r["kind"],_freeze(p),tuple(r["parents"]),r["prev"],h)
    def _load(self):
        if not self.log.exists():self.log.touch()
        raw=self.log.read_bytes();self._disk_size=len(raw)
        if raw and not raw.endswith(b"\n"):raise Residual("OCCURRENCE_LOG_PARSE_ERROR")
        prev="0"*64
        for i,line in enumerate(raw.decode().splitlines(),1):
            o=self._decode(line);_reject(o.seq!=i or o.prev_digest!=prev or o.occurrence_id!="o_"+o.record_digest[:24],"OCCURRENCE_CHAIN_INVALID");_reject(any(p not in self.by_id for p in o.parents),"OCCURRENCE_PARENT_UNKNOWN");self._occ.append(o);self.by_id[o.occurrence_id]=o;prev=o.record_digest
    def _lock(self):
        class L:
            def __init__(s,p):s.f=open(p,"a+b")
            def __enter__(s):
                if os.name=="nt":import msvcrt;s.f.seek(0,2);s.f.write(b"\0") if not s.f.tell() else None;s.f.flush();s.f.seek(0);msvcrt.locking(s.f.fileno(),msvcrt.LK_LOCK,1)
                else:import fcntl;fcntl.flock(s.f,fcntl.LOCK_EX)
                return s
            def __exit__(s,*a):
                if os.name=="nt":import msvcrt;s.f.seek(0);msvcrt.locking(s.f.fileno(),msvcrt.LK_UNLCK,1)
                else:import fcntl;fcntl.flock(s.f,fcntl.LOCK_UN)
                s.f.close()
        return L(self.lockfile)
    def _append(self,kind,payload,parents=()):
        self._check_seals();parents=_ids(parents,"parents")
        if any(x not in self.by_id for x in parents):raise Residual("OCCURRENCE_PARENT_UNKNOWN")
        with self._lock():
            raw=self.log.read_bytes()
            if len(raw)!=self._disk_size:raise Residual("CONCURRENT_STATE_MODIFICATION")
            if raw and self._occ and not raw.endswith(self._encode(self._occ[-1]).encode()):raise Residual("CONCURRENT_STATE_MODIFICATION")
            seq=len(self._occ)+1;prev=self._occ[-1].record_digest if self._occ else "0"*64;p=_clone(payload);core={"seq":seq,"kind":kind,"payload":p,"parents":list(parents),"prev":prev};h=digest(core);o=Occurrence(seq,"o_"+h[:24],kind,_freeze(p),parents,prev,h);enc=self._encode(o).encode()
            with open(self.log,"ab") as f:f.write(enc);f.flush();os.fsync(f.fileno())
            self._disk_size+=len(enc);self._occ.append(o);self.by_id[o.occurrence_id]=o;self._project(o)
            try:self._write_local_watermark()
            except OSError:self._watermark_degraded=True
            self._seal();return o.occurrence_id
    def append(self,*a,**k):raise Residual("RESERVED_OCCURRENCE_INGRESS")
    def _prefix_head(self,n):return "0"*64 if n==0 else self._occ[n-1].record_digest
    def anchor(self):return {"schema":"pnr12.anchor.v1","seq":len(self._occ),"head_digest":self._prefix_head(len(self._occ))}
    def _write_local_watermark(self):
        tmp=self.watermark.with_suffix(".tmp");tmp.write_text(json.dumps(self.anchor(),sort_keys=True));os.replace(tmp,self.watermark)
    def _validate_watermark(self):
        if not self.watermark.exists():self._write_local_watermark();return
        try:m=json.loads(self.watermark.read_text());n=int(m["seq"]);h=m["head_digest"]
        except Exception as e:raise Residual("FABRIC_HIGH_WATER_INVALID") from e
        if n>len(self._occ):raise Residual("FABRIC_ROLLBACK_DETECTED")
        if n<0 or n and (n>len(self._occ) or self._prefix_head(n)!=h):raise Residual("FABRIC_HIGH_WATER_INVALID")
        if n==len(self._occ) and h!=self._prefix_head(n):raise Residual("FABRIC_HIGH_WATER_INVALID")
        if n<len(self._occ):self._write_local_watermark()
    def _validate_external(self,expect_digest,expect_anchor):
        if expect_digest is not None and self.fabric_digest()!=expect_digest:raise Residual("FABRIC_EXTERNAL_ANCHOR_MISMATCH")
        if expect_anchor is not None:
            n=int(expect_anchor.get("seq",-1));h=expect_anchor.get("head_digest")
            if n>len(self._occ):raise Residual("FABRIC_EXTERNAL_ROLLBACK_DETECTED")
            if n<0 or self._prefix_head(n)!=h:raise Residual("FABRIC_EXTERNAL_DIVERGENCE_DETECTED")
    def _disk_check(self):
        raw=self.log.read_bytes()
        if len(raw)!=self._disk_size or raw!=b"".join(self._encode(o).encode() for o in self._occ):raise Residual("OCCURRENCE_DISK_STATE_DIVERGED")
    def fabric_digest(self):return digest([o.record_digest for o in self._occ])
    def _rebuild(self):
        self.languages={};self.artifacts={};self._certs={};self._artifact_certs={};self._outputs={};self.resource_used=0.0;self.resource_limit=float("inf");self._resource_contract_set=False
        self.assumptions=_FD();self.obligations=_FD();self.evidence=_FD();self.standings=_FD();self.constitutions=_FD();self.performed_experiments=_FD();self.authority={"max_risk":1.0,"allow_irreversible":True};self._authority_contract_set=False;self._falsified=set();self._retracted_claims=set();self._counterexample_ids=set()
        for o in self._occ:self._project(o,replay=True)
    def _reason_state(self):
        st={k:(v.kind.value,list(v.assumptions),list(v.evidence_roots),v.dependency_status,list(v.sufficiency_coverage),v.counterexample_status) for k,v in self.standings.items()}
        return {"a":dict(self.assumptions),"o":dict(self.obligations),"e":dict(self.evidence),"s":st,"c":dict(self.constitutions),"p":dict(self.performed_experiments),"f":sorted(self._falsified),"r":sorted(self._retracted_claims),"x":sorted(self._counterexample_ids)}
    def _project(self,o,replay=False):
        p=dict(o.payload);k=o.kind
        if k=="ResourceCharge":self.resource_used=math.fsum([self.resource_used,float(p["cost"])])
        elif k=="RuntimeContract":self.authority={"max_risk":float(p["max_risk"]),"allow_irreversible":bool(p["allow_irreversible"])};self.resource_limit=float("inf") if p.get("budget") is None else float(p["budget"]);self._resource_contract_set=True;self._authority_contract_set=True
        elif k=="ProposalLanguageOccurrence":self.languages[p["language_id"]]=ProposalLanguage(p["language_id"],p.get("parent_language_id"),_freeze(p["primitives"]),tuple(p.get("generated_primitives",[])),"PROPOSED",None,tuple(p.get("assumptions",[])),_freeze(p.get("validity_scope",{})),tuple(p.get("artifact_dependencies",[])))
        elif k=="BridgeCertificateOccurrence":self._certs[p["certificate_id"]]=o
        elif k in ("ProposalLanguageQualifiedOccurrence","LanguageCommitted"):
            lid=p["language_id"]
            if k=="LanguageCommitted":self.languages[lid]=ProposalLanguage(lid,p["parent_language_id"],_freeze(p["primitives"]),tuple(p["generated_primitives"]),"QUALIFIED",p["certificate_id"],tuple(p.get("assumptions",[])),_freeze(p.get("validity_scope",{})),tuple(p.get("artifact_dependencies",[])))
            else:self.languages[lid]=self.languages[lid]._replace(status="QUALIFIED",bridge_certificate_id=p["certificate_id"])
        elif k=="LanguageRetracted":self.languages[p["language_id"]]=self.languages[p["language_id"]]._replace(status="RETRACTED",counterexamples=tuple(sorted(set((*self.languages[p["language_id"]].counterexamples,p["counterexample_id"])))))
        elif k=="ArtifactCommitted":self.artifacts[p["artifact_id"]]=GeneratedArtifact(p["artifact_id"],p["artifact_kind"],p["language_id"],_freeze(p["program"]),tuple(p.get("assumptions",[])),_freeze(p.get("validity_scope",{})),tuple(p.get("artifact_dependencies",[])),p["standing"],p["certificate_id"]);self._artifact_certs[p["certificate_id"]]=o
        elif k=="ArtifactProposed":self.artifacts[p["artifact_id"]]=GeneratedArtifact(p["artifact_id"],p["artifact_kind"],p["language_id"],_freeze(p["program"]),tuple(p.get("assumptions",[])),_freeze(p.get("validity_scope",{})),tuple(p.get("artifact_dependencies",[])))
        elif k=="ArtifactQualified":self.artifacts[p["artifact_id"]]=self.artifacts[p["artifact_id"]]._replace(standing=p["standing"],certificate_id=p["certificate_id"]);self._artifact_certs[p["certificate_id"]]=o
        elif k=="ArtifactRetracted":self.artifacts[p["artifact_id"]]=self.artifacts[p["artifact_id"]]._replace(standing=RETRACTED,counterexamples=tuple(sorted(set((*self.artifacts[p["artifact_id"]].counterexamples,p["counterexample_id"])))))
        elif k=="Output":self._outputs[o.occurrence_id]=(p["artifact_id"],_freeze(p["value"]),tuple(p.get("producer_artifacts",[])))
        elif k=="Assumption":dict.__setitem__(self.assumptions,p["assumption_id"],_freeze({"statement":p["statement"],"occurrence_id":o.occurrence_id}))
        elif k=="Obligation":dict.__setitem__(self.obligations,p["claim_id"],_freeze(p))
        elif k=="Evidence":dict.__setitem__(self.evidence,o.occurrence_id,_freeze(p))
        elif k=="Standing":dict.__setitem__(self.standings,p["claim_id"],ClaimStanding(p["claim_id"],StandingKind(p["kind"]),_freeze(p.get("scope",{})),tuple(p.get("assumptions",[])),tuple(p["evidence_roots"]),p["dependency_status"],tuple(p["sufficiency_coverage"]),p.get("verifier","PNR12")))
        elif k=="Constitution":dict.__setitem__(self.constitutions,p["constitution_id"],_FD(predictions=_freeze(p["predictions"]),assumptions=tuple(p.get("assumptions",[])),payload=_freeze(p.get("payload",{})),artifact_dependencies=tuple(p.get("artifact_dependencies",[])),active=True,excluded_by=None))
        elif k=="ConstitutionExcluded":
            if p["constitution_id"] in self.constitutions:
                q=dict(self.constitutions[p["constitution_id"]]);q.update(active=False,excluded_by=p["evidence_id"]);dict.__setitem__(self.constitutions,p["constitution_id"],_FD(q))
        elif k=="Experiment":dict.__setitem__(self.performed_experiments,p["experiment_id"],_freeze(p))
        elif k=="Counterexample":
            self._counterexample_ids.add(p["counterexample_id"]);self._falsified.update(p.get("falsified_assumptions",[]));self._retracted_claims.update(p.get("retracted_claim_ids",[]))
            for cid in p.get("retracted_claim_ids",[]):
                if cid in self.standings:dict.__setitem__(self.standings,cid,self.standings[cid]._replace(kind=StandingKind.RETRACTED_BY_COUNTEREXAMPLE,counterexample_status=p["counterexample_id"]))
            for cid in p.get("excluded_constitution_ids",[]):
                if cid in self.constitutions:q=dict(self.constitutions[cid]);q.update(active=False,excluded_by=p["counterexample_id"]);dict.__setitem__(self.constitutions,cid,_FD(q))
    def _install_base(self):
        if "PNR12_BASE" not in self.languages:self._append("ProposalLanguageOccurrence",{"language_id":"PNR12_BASE","parent_language_id":None,"primitives":BASE,"generated_primitives":[],"validity_scope":{"frozen_basis":True}})
        if self.languages["PNR12_BASE"].status=="PROPOSED":
            receipt=self.bridge.check_language(dict(self.languages["PNR12_BASE"].primitives));cid="c_"+digest(receipt)[:24];co=next((o for o in self._occ if o.kind=="BridgeCertificateOccurrence" and o.payload.get("certificate_id")==cid),None)
            if co is None:coid=self._append("BridgeCertificateOccurrence",{"certificate_id":cid,"language_id":"PNR12_BASE","receipt":receipt});co=self.by_id[coid]
            self._append("ProposalLanguageQualifiedOccurrence",{"language_id":"PNR12_BASE","certificate_id":cid},[co.occurrence_id])
    def _valid_assumptions(self,a):
        a=_ids(a,"assumptions")
        for x in a:_reject(x not in self.assumptions,"ASSUMPTION_OCCURRENCE_REQUIRED",assumption_id=x);_reject(x in self._falsified,"ASSUMPTION_RETRACTED_BY_COUNTEREXAMPLE",assumption_id=x)
        return a
    def set_budget(self,budget):return self.set_contracts(max_risk=self.authority["max_risk"],allow_irreversible=self.authority["allow_irreversible"],budget=budget)
    def set_contracts(self,*,max_risk=1.0,allow_irreversible=True,budget=float("inf")):
        self._check_seals();_reject(not isinstance(allow_irreversible,bool),"AUTHORITY_IRREVERSIBLE_FLAG_INVALID");_reject(isinstance(max_risk,bool) or not isinstance(max_risk,(int,float)) or not math.isfinite(max_risk) or max_risk<0,"AUTHORITY_RISK_INVALID");_reject(isinstance(budget,bool) or not isinstance(budget,(int,float)) or math.isnan(budget) or budget<0,"RESOURCE_BUDGET_INVALID")
        _reject(self._authority_contract_set and (max_risk>self.authority["max_risk"] or (allow_irreversible and not self.authority["allow_irreversible"])),"AUTHORITY_CONTRACT_CANNOT_LOOSEN");_reject(self._resource_contract_set and budget>self.resource_limit,"RESOURCE_BUDGET_CANNOT_INCREASE");_reject(budget<self.resource_used,"RESOURCE_BUDGET_BELOW_SPENT");return self._append("RuntimeContract",{"max_risk":float(max_risk),"allow_irreversible":allow_irreversible,"budget":None if math.isinf(budget) else float(budget)})
    def charge(self,cost,reason,parents=(),*,key=None):
        self._check_seals();_reject(isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(cost) or cost<0,"RESOURCE_COST_INVALID",cost=cost)
        if key:
            old=next((o for o in self._occ if o.kind=="ResourceCharge" and o.payload.get("key")==key),None)
            if old:return old.occurrence_id
        _reject(math.fsum([self.resource_used,float(cost)])>self.resource_limit+1e-15,"RESOURCE_EXHAUSTED",used=self.resource_used,cost=cost,limit=self.resource_limit);return self._append("ResourceCharge",{"cost":float(cost),"reason":str(reason),"key":key},parents)
    def add_assumption(self,assumption_id,statement):
        _reject(assumption_id in self.assumptions,"ASSUMPTION_ID_ALREADY_BOUND");return self._append("Assumption",{"assumption_id":assumption_id,"statement":str(statement)})
    def add_obligation(self,claim_id,claim_kind,required_dimensions,admissible_assumptions=(),**kw):
        _reject(claim_id in self.obligations,"CLAIM_OBLIGATION_ALREADY_BOUND");return self._append("Obligation",{"claim_id":claim_id,"claim_kind":str(claim_kind),"required_dimensions":list(_ids(required_dimensions)),"admissible_assumptions":list(_ids(admissible_assumptions)),**kw})
    def _producer_deps(self,eid):
        seen=set();stack=[eid];out=set()
        while stack:
            x=stack.pop()
            if x in seen:continue
            seen.add(x);e=self.evidence.get(x)
            if e:out.update(e.get("producer_artifacts",[]));stack.extend(e.get("parents",[]))
        return out
    def add_evidence(self,value,dimensions,lineage_roots,assertions=None,parents=(),producer_artifacts=()):
        self._check_seals();parents=_ids(parents,"parents");roots=set(_ids(lineage_roots,"lineage_roots"));prod=set(_ids(producer_artifacts,"producer_artifacts"))
        for p in parents:
            if p in self.evidence:roots.update(self.evidence[p].get("lineage_roots",[]));prod.update(self.evidence[p].get("producer_artifacts",[]))
        for a in prod:
            if a not in self.artifacts or self.artifacts[a].standing in DEAD:raise Residual("EVIDENCE_PRODUCER_NOT_EXECUTABLE",artifact_id=a)
            roots.add("artifact:"+a)
        return self._append("Evidence",{"value":value,"dimensions":list(_ids(dimensions)),"lineage_roots":sorted(roots),"assertions":assertions or {},"parents":list(parents),"producer_artifacts":sorted(prod)},parents)
    def add_transform(self,parent_id,transform_kind,input_value,output_value,lossy,detail=None):
        _reject(parent_id not in self.evidence,"UNKNOWN_EVIDENCE");e=self.evidence[parent_id];_reject(not _same(input_value,e["value"]),"TRANSFORM_INPUT_MISMATCH");_reject(not isinstance(lossy,bool),"TRANSFORM_LOSSY_FLAG_INVALID");return self.add_evidence(output_value,e["dimensions"],e["lineage_roots"],{"_transform":{"kind":str(transform_kind),"input":input_value,"lossy":lossy,"detail":detail}},[parent_id],e.get("producer_artifacts",()))
    def _dep(self,eids):
        roots=[set(self.evidence[e]["lineage_roots"]) for e in eids]
        if any(not r for r in roots):return "UNROOTED"
        if len(roots)>1 and any(roots[i]&roots[j] for i in range(len(roots)) for j in range(i)):return "CORRELATED"
        return "INDEPENDENT"
    def _producer_cap(self,kind,eids):
        rank={EXACT:60,"BOUNDED_UNDER_ASSUMPTIONS":50,"HELDOUT_EMPIRICAL":40,"CALIBRATED_EMPIRICAL":30,"SUPPORTED_HYPOTHESIS":20,"UNRESOLVED_EQUIVALENCE_CLASS":10,"TYPED_RESIDUAL":0}
        deps=set().union(*(self._producer_deps(e) for e in eids))
        if not deps:return kind
        cap=min(rank.get(self.artifacts[a].standing,0) for a in deps);return StandingKind(max((k for k,v in rank.items() if v<=min(rank[kind.value],cap)),key=lambda k:rank[k]))
    def assess_claim(self,claim_id,evidence_ids,assumptions=()):
        if claim_id not in self.obligations:raise Residual("CLAIM_OBLIGATION_REQUIRED")
        eids=_ids(evidence_ids,"evidence_ids");ass=self._valid_assumptions(assumptions);obl=self.obligations[claim_id]
        if any(a not in obl.get("admissible_assumptions",[]) for a in ass):raise Residual("ASSUMPTION_NOT_ADMISSIBLE")
        if any(e not in self.evidence for e in eids):raise Residual("UNKNOWN_EVIDENCE")
        dep=self._dep(eids);coverage=sorted(set().union(*(set(self.evidence[e]["dimensions"]) for e in eids)));req=set(obl["required_dimensions"]);vals={d:set() for d in req}
        for e in eids:
            for d,v in self.evidence[e].get("assertions",{}).items():
                if d in vals:vals[d].add(digest(v))
        kind=StandingKind.TYPED_RESIDUAL
        if dep=="INDEPENDENT" and req.issubset(coverage):kind=StandingKind.UNRESOLVED_EQUIVALENCE_CLASS if any(len(v)>1 for v in vals.values()) else StandingKind.EXACT_UNDER_ASSUMPTIONS
        kind=self._producer_cap(kind,eids);p={"claim_id":claim_id,"kind":kind.value,"scope":{},"assumptions":list(ass),"evidence_roots":list(eids),"dependency_status":dep,"sufficiency_coverage":coverage,"verifier":"PNR12"};self._append("Standing",p,eids);return self.standings[claim_id]
    def propose_constitution(self,predictions,assumptions=(),payload=None):
        ass=self._valid_assumptions(assumptions);cid="h_"+digest((predictions,ass,payload or {}))[:24]
        if cid not in self.constitutions:self._append("Constitution",{"constitution_id":cid,"predictions":predictions,"assumptions":list(ass),"payload":payload or {}})
        return cid
    def active_constitutions(self):return [x for x in self.constitutions.values() if x["active"]]
    def select_discriminating_experiment(self,experiments,claim_id=None,value=1.0):
        ex=list(experiments)
        if any(not isinstance(e,Experiment) for e in ex):raise Residual("EXPERIMENT_OBJECT_REQUIRED")
        if len({e.experiment_id for e in ex})!=len(ex):raise Residual("EXPERIMENT_ID_DUPLICATE")
        active=[h for h in self.active_constitutions() if claim_id is None or claim_id in h.payload.get("relevant_claims",[claim_id])];best=None
        for e in ex:
            if e.risk>self.authority["max_risk"] or (e.irreversible and not self.authority["allow_irreversible"]):continue
            counts={}
            for h in active:counts[digest(h.predictions.get(e.experiment_id))]=counts.get(digest(h.predictions.get(e.experiment_id)),0)+1
            score=len(active)-max(counts.values(),default=len(active));key=(score*value-e.cost,-e.risk,e.experiment_id)
            if best is None or key>best[0]:best=(key,e)
        if best is None:raise Residual("NO_ADMISSIBLE_EXPERIMENT")
        return best[1]
    def schedule_next(self,claim_id,experiments,protected_value=1.0):return {"experiment":self.select_discriminating_experiment(experiments,claim_id,protected_value)}
    def perform_experiment(self,e,observed):
        self._check_seals();_reject(not isinstance(e,Experiment),"EXPERIMENT_OBJECT_REQUIRED");_reject(e.risk>self.authority["max_risk"] or (e.irreversible and not self.authority["allow_irreversible"]),"EXPERIMENT_NOT_AUTHORIZED");oid=self._append("Experiment",{"experiment_id":e.experiment_id,"observed":observed,"cost":e.cost,"risk":e.risk})
        for cid,h in list(self.constitutions.items()):
            if h["active"] and e.experiment_id in h.predictions and not _same(h.predictions[e.experiment_id],observed):self._append("ConstitutionExcluded",{"constitution_id":cid,"evidence_id":oid},[oid])
        return oid
    def _language_table(self,parent,name,domains,codomain,evidence,check,assumptions=()):
        if parent not in self.languages or self.languages[parent].status!="QUALIFIED":raise Residual("QUALIFIED_PARENT_LANGUAGE_REQUIRED")
        ass=self._valid_assumptions(assumptions);domains=_clone(domains);codomain=_clone(codomain)
        if not isinstance(domains,list) or not domains or any(not isinstance(d,list) or not d for d in domains):raise Residual("LANGUAGE_DOMAIN_REQUIRED")
        tested=math.prod(map(len,domains));_reject(tested>MAX_SEARCH,"LANGUAGE_SEARCH_APERTURE_EXCEEDED",candidates=tested,limit=MAX_SEARCH);allrows=[list(x) for x in itertools.product(*domains)];rowkeys={digest(x) for x in allrows};codes={digest(x) for x in codomain};known={}
        for e in [*evidence,*check]:
            if not isinstance(e,dict) or not isinstance(e.get("in"),list) or "out" not in e:raise Residual("LANGUAGE_EVIDENCE_MALFORMED")
            k=digest(e["in"])
            if k not in rowkeys:raise Residual("LANGUAGE_EVIDENCE_INPUT_OUTSIDE_DOMAIN")
            if digest(e["out"]) not in codes:raise Residual("LANGUAGE_EVIDENCE_OUTPUT_OUTSIDE_CODOMAIN")
            if k in known and not _same(known[k],e["out"]):raise Residual("LANGUAGE_EVIDENCE_CONFLICT")
            known[k]=_clone(e["out"])
        self.charge(tested*UNIT,"finite_table_check",key="langcheck:"+digest((parent,name,domains,codomain,evidence,check))[:24])
        if len(known)!=tested:raise Residual("LANGUAGE_UNDERDETERMINED")
        table=[{"in":r,"out":known[digest(r)]} for r in allrows];spec={"kind":"finite_table","domains":domains,"codomain":codomain,"table":table};pr=dict(self.languages[parent].primitives);pr[name]=spec;receipt=self.bridge.check_language(pr);lid="l_"+digest((parent,name,spec,ass))[:24]
        if lid in self.languages:
            if self.languages[lid].status=="RETRACTED":raise Residual("LANGUAGE_REALIZATION_ALREADY_EXISTS",language_id=lid,status="RETRACTED")
            return {"language_id":lid,"tested":tested}
        cid="c_"+digest(receipt)[:24];self._append("LanguageCommitted",{"language_id":lid,"parent_language_id":parent,"primitives":pr,"generated_primitives":[*self.languages[parent].generated_primitives,name],"certificate_id":cid,"receipt":receipt,"assumptions":list(ass),"validity_scope":{},"artifact_dependencies":[]});return {"language_id":lid,"tested":tested}
    def generate_finite_extension(self,parent_id,new_name,domains,codomain,evidence,check,*,assumptions=()):return self._language_table(parent_id,new_name,domains,codomain,evidence,check,assumptions)
    def generate_boolean_extension(self,parent_id,new_name,arity,evidence,check,*,assumptions=()):return self._language_table(parent_id,new_name,[[False,True] for _ in range(arity)],[False,True],evidence,check,assumptions)
    def extend_language(self,*a,**k):raise Residual("DIRECT_LANGUAGE_COMMIT_NOT_PUBLIC")
    def _artifact(self,kind,language,program,standing,*,assumptions=(),scope=None,deps=(),identity=None):
        _reject(language not in self.languages or self.languages[language].status!="QUALIFIED","QUALIFIED_LANGUAGE_REQUIRED");ass=self._valid_assumptions(assumptions);deps=_ids(deps,"artifact_dependencies")
        for d in deps:_reject(d not in self.artifacts,"UNKNOWN_ARTIFACT_DEPENDENCY",artifact_id=d)
        aid="a_"+digest(identity if identity is not None else (kind,language,program,ass,scope or {},deps))[:24]
        if aid in self.artifacts:
            if self.artifacts[aid].standing==RETRACTED:raise Residual("ARTIFACT_REALIZATION_ALREADY_EXISTS",artifact_id=aid,standing=RETRACTED)
            return aid
        cid="ac_"+digest((aid,program,standing))[:24];self._append("ArtifactCommitted",{"artifact_id":aid,"artifact_kind":kind,"language_id":language,"program":program,"assumptions":list(ass),"validity_scope":scope or {},"artifact_dependencies":list(deps),"standing":standing,"certificate_id":cid,"program_digest":digest(program)});return aid
    def propose_sensor(self,pipeline,target_distinction,assumptions=(),validity_scope=None):
        ass=self._valid_assumptions(assumptions);aid="a_"+digest(("compat_sensor",pipeline,target_distinction,ass))[:24]
        if aid not in self.artifacts:self._append("ArtifactProposed",{"artifact_id":aid,"artifact_kind":"SensorProcedure","language_id":"PNR12_BASE","program":{"kind":"pipeline","pipeline":pipeline,"target":target_distinction},"assumptions":list(ass),"validity_scope":validity_scope or {},"artifact_dependencies":[]})
        return aid
    def _run_pipeline(self,pipe,x):
        cur=x
        for s in pipe:
            op=s.get("op")
            if op=="get":cur=cur.get(s["key"]) if isinstance(cur,dict) else None
            elif op=="identity":cur=cur
            elif op=="length":cur=len(cur) if hasattr(cur,"__len__") else 0
            elif op=="contains":cur=s.get("value") in cur if hasattr(cur,"__contains__") else False
            elif op=="eq":cur=_same(cur,s.get("value"))
            else:raise Residual("SENSOR_PRIMITIVE_NOT_ADMITTED",op=op)
        return cur
    def calibrate_sensor(self,aid,cases,negative_controls=None):
        _reject(aid not in self.artifacts or self.artifacts[aid].artifact_kind!="SensorProcedure","UNKNOWN_SENSOR");_reject(not cases,"CALIBRATION_INSUFFICIENT");a=self.artifacts[aid]
        for c in cases:_reject(not _same(self._run_pipeline(a.program["pipeline"],c["raw"]),c["label"]),"CALIBRATION_FAIL")
        cid="ac_"+digest((aid,cases))[:24];self._append("ArtifactQualified",{"artifact_id":aid,"standing":"CALIBRATED_EMPIRICAL","certificate_id":cid,"calibration_digest":digest(cases)});return aid
    def generate_sensor(self,language_id,primitive_name,input_keys,calibration,*,assumptions=()):
        _reject(language_id not in self.languages or primitive_name not in self.languages[language_id].primitives,"PRIMITIVE_NOT_IN_LANGUAGE");spec=self.languages[language_id].primitives[primitive_name];_reject(len(input_keys)!=len(spec["domains"]),"SENSOR_INPUT_ARITY_MISMATCH");_reject(not calibration,"CALIBRATION_INSUFFICIENT")
        for c in calibration:
            try:args=[c["raw"][k] for k in input_keys]
            except KeyError as e:raise Residual("SENSOR_INPUT_KEY_MISSING",key=e.args[0])
            if not _same(self.bridge.evaluate_primitive(spec,args),c["label"]):raise Residual("CALIBRATION_FAIL")
        program={"kind":"Sensor","primitive":primitive_name,"input_keys":list(input_keys),"calibration_digest":digest(calibration)};return self._artifact("Sensor",language_id,program,"CALIBRATED_EMPIRICAL",assumptions=assumptions,identity=("sensor",language_id,primitive_name,input_keys,calibration,assumptions))
    def _produce(self,aid,value,op,inputs=None):
        _reject(aid not in self.artifacts or self.artifacts[aid].standing in DEAD,"ARTIFACT_NOT_EXECUTABLE",artifact_id=aid);oid=self._append("Output",{"artifact_id":aid,"value":value,"operation":op,"inputs":inputs,"producer_artifacts":[aid]});return ProducedValue(_freeze(_clone(value)),aid,oid)
    def run_sensor(self,aid,raw,context=None):
        if aid not in self.artifacts or self.artifacts[aid].standing in DEAD:raise Residual("ARTIFACT_NOT_EXECUTABLE",artifact_id=aid)
        a=self.artifacts[aid]
        try:
            if a.artifact_kind=="SensorProcedure":v=self._run_pipeline(a.program["pipeline"],raw)
            else:
                keys=a.program["input_keys"]
                if not isinstance(raw,dict):raise Residual("SENSOR_INPUT_REQUIRED")
                if any(k not in raw for k in keys):raise Residual("SENSOR_INPUT_KEY_MISSING")
                v=self.bridge.evaluate_primitive(self.languages[a.language_id].primitives[a.program["primitive"]],[raw[k] for k in keys])
            if context is not None:_clone(context)
        except Residual:raise
        except Exception as e:raise Residual("SENSOR_RUNTIME_ERROR",error=type(e).__name__) from e
        return self._produce(aid,v,"sensor",raw)
    def externalize(self,value,*,reason):
        _reject(not isinstance(value,ProducedValue),"PRODUCED_VALUE_REQUIRED");_reject(not isinstance(reason,str) or not reason,"EXTERNALIZATION_REASON_REQUIRED");self._append("Externalization",{"source_occurrence_id":value.occurrence_id,"artifact_id":value.artifact_id,"reason":reason});return _clone(value._value)
    def observe(self,value,dimensions=(),roots=(),*,assertions=None,parents=(),produced_by=()):
        """Record an observation and preserve dependencies."""
        prod=set(_ids(produced_by,"produced_by"));raw=value
        if isinstance(value,ProducedValue):prod.add(value.artifact_id);parents=tuple(set((*parents,value.occurrence_id)));raw=value._value
        elif self._contains_produced(value):raise Residual("PRODUCED_VALUE_NESTING_REQUIRES_EXPLICIT_HANDLING")
        return self.add_evidence(raw,dimensions,roots,assertions,parents,prod)
    def _contains_produced(self,x):
        if isinstance(x,ProducedValue):return True
        if isinstance(x,dict):return any(self._contains_produced(k) or self._contains_produced(v) for k,v in x.items())
        if isinstance(x,(list,tuple,set,frozenset)):return any(self._contains_produced(v) for v in x)
        return False
    def require(self,claim_id,dimensions=(),*,kind="claim",assumptions=(),**scope):
        """Declare what evidence a claim requires."""
        return self.add_obligation(claim_id,kind,dimensions,assumptions,**scope)
    def extend(self,parent,name,domains,codomain,evidence,check):
        """Construct and verify a finite operation."""
        return self.generate_finite_extension(parent,name,domains,codomain,evidence,check)
    def synthesize(self,*,kind,language="PNR12_BASE",candidates,build,qualify,scope=None,standing=EXACT,court="GENERIC_VERIFIER",assumptions=(),depends_on=()):
        """Search bounded candidates and retain one independently verified program."""
        rejected=[]
        for i,c in enumerate(candidates):
            if i>=MAX_SEARCH:raise Residual("MORPHISM_SEARCH_APERTURE_EXCEEDED")
            self.charge(UNIT,"generic_synthesis")
            try:p=build(c);q=qualify(p)
            except Exception as e:rejected.append(getattr(e,"kind",type(e).__name__));continue
            aid=self._artifact(kind,language,p,standing,assumptions=assumptions,scope=scope,deps=depends_on,identity=(kind,language,p,scope,standing,assumptions,depends_on,court));return {"artifact_id":aid,"candidate":c,"verification":q}
        raise Residual("NO_LAWFUL_MORPHISM_IN_SEARCH_APERTURE",rejected=rejected)
    def refute(self,counterexample_id,**scope):
        """Record a counterexample and invalidate dependent results."""
        return self.counterexample(counterexample_id,**scope)
    def synthesize_transfer(self,source_states,source_actions,low,high,target_states,target_actions,source_observations=None,target_observations=None):
        _safe_keys(source_states,"source_states");_safe_keys(target_states,"target_states");_safe_keys(source_actions,"source_actions");_safe_keys(target_actions,"target_actions");space=math.perm(len(target_states),len(source_states))*math.perm(len(target_actions),len(source_actions));_reject(space>MAX_SEARCH,"MORPHISM_SEARCH_APERTURE_EXCEEDED",candidates=space,limit=MAX_SEARCH);self.charge(space*UNIT,"transfer_search")
        for tauvals in itertools.permutations(target_states,len(source_states)):
            tau=dict(zip(source_states,tauvals))
            if source_observations and any(not _same(source_observations[s],target_observations[tau[s]]) for s in source_states):continue
            for omegavals in itertools.permutations(target_actions,len(source_actions)):
                omega=dict(zip(source_actions,omegavals));ok=True
                for s,row in low.items():
                    for a,d in row.items():
                        if tau[s] not in high or omega[a] not in high[tau[s]] or not _same(high[tau[s]][omega[a]],tau[d]):ok=False;break
                    if not ok:break
                if ok:
                    aid=self._artifact("TransferMap","PNR12_BASE",{"tau":tau,"omega":omega},EXACT);return {"artifact_id":aid,"tau":self._produce(aid,tau,"transfer_tau"),"omega":self._produce(aid,omega,"transfer_omega")}
        raise Residual("NO_LAWFUL_MORPHISM_IN_SEARCH_APERTURE")
    def _eval_ast(self,x,env,lang=None):
        if isinstance(x,(bool,int,float)):return x
        if isinstance(x,dict) and "var" in x:return env[x["var"]]
        _reject(not isinstance(x,dict),"AST_MALFORMED")
        if "call" in x:return self.bridge.evaluate_primitive(lang.primitives[x["call"]],[self._eval_ast(a,env,lang) for a in x.get("args",[])])
        a=[self._eval_ast(v,env,lang) for v in x.get("args",[])];op=x.get("op")
        if op=="add":return a[0]+a[1]
        if op=="sub":return a[0]-a[1]
        raise Residual("AST_OP_UNSUPPORTED")
    def synthesize_rewrite(self,source_expr,examples,check,language_id="PNR12_BASE"):
        lang=self.languages[language_id];vars=sorted(self._vars(source_expr));atoms=[{"var":v} for v in vars];cands=[*atoms,*({"op":op,"args":[a,b]} for op in ("add","sub") for a in atoms for b in atoms)]
        for n in lang.generated_primitives:
            ar=len(lang.primitives[n]["domains"])
            if ar==1:cands += [{"call":n,"args":[a]} for a in atoms]
            elif ar==2:cands += [{"call":n,"args":[a,b]} for a in atoms for b in atoms]
        def fits(r,cases):
            try:return all(_same(self._eval_ast(r,c["env"],lang),c["expected"]) for c in cases)
            except (Residual,TypeError,KeyError,IndexError):return False
        for r in cands:
            if fits(r,examples):
                _reject(not fits(r,check),"REWRITE_HELDOUT_FAIL");aid=self._artifact("Rewrite",language_id,{"replacement":r},"HELDOUT_EMPIRICAL");return {"artifact_id":aid,"replacement":self._produce(aid,r,"rewrite")}
        raise Residual("NO_LAWFUL_MORPHISM_IN_SEARCH_APERTURE")
    def _vars(self,x):
        if isinstance(x,dict):
            if "var" in x:return {str(x["var"])}
            return set().union(*(self._vars(v) for v in x.values())) if x else set()
        if isinstance(x,list):return set().union(*(self._vars(v) for v in x)) if x else set()
        return set()
    def transport_language(self,language_id,target_scope,requalification_cases=None):
        _reject(language_id not in self.languages or self.languages[language_id].status!="QUALIFIED","QUALIFIED_LANGUAGE_REQUIRED");src=self.languages[language_id];cases=requalification_cases or {}
        for n,rows in cases.items():
            if n not in src.primitives:raise Residual("LANGUAGE_TRANSPORT_REQUALIFICATION_FAIL")
            for r in rows:_reject(not _same(self.bridge.evaluate_primitive(src.primitives[n],r["in"]),r["out"]),"LANGUAGE_TRANSPORT_REQUALIFICATION_FAIL")
        lid="l_"+digest((language_id,target_scope,src.primitives))[:24]
        if lid not in self.languages:
            receipt=self.bridge.check_language(dict(src.primitives));self._append("LanguageCommitted",{"language_id":lid,"parent_language_id":language_id,"primitives":dict(src.primitives),"generated_primitives":list(src.generated_primitives),"certificate_id":"c_"+digest(receipt)[:24],"receipt":receipt,"assumptions":list(src.assumptions),"validity_scope":target_scope,"artifact_dependencies":list(src.artifact_dependencies)})
        return lid
    def compile_generated_algorithm(self,language_id,primitive_name,max_steps):
        _reject(isinstance(max_steps,bool) or not isinstance(max_steps,int) or max_steps<0,"STEP_HORIZON_INVALID");spec=self.languages[language_id].primitives[primitive_name];_reject(len(spec["domains"])!=1,"TRANSITION_PRIMITIVE_MUST_BE_UNARY");nxt={digest(r["in"][0]):_clone(r["out"]) for r in spec["table"]};_reject(any(digest(v) not in nxt for v in nxt.values()),"TRANSITION_NOT_ENDOMORPHISM");c={"next":nxt,"max_steps":max_steps};aid=self._artifact("GeneratedAlgorithm",language_id,{"primitive":primitive_name,"compiled":c},EXACT,identity=("algorithm",language_id,primitive_name,max_steps));return {"artifact_id":aid,"levels":1,"table_entries":len(nxt)}
    def run_generated_algorithm(self,aid,start,steps):
        _reject(aid not in self.artifacts or self.artifacts[aid].standing in DEAD,"ARTIFACT_NOT_EXECUTABLE");c=self.artifacts[aid].program["compiled"];_reject(isinstance(steps,bool) or not isinstance(steps,int) or steps<0,"STEP_COUNT_INVALID");_reject(steps>c["max_steps"],"COMPILED_EXECUTOR_OUTSIDE_SCOPE");d=digest(start);_reject(d not in c["next"],"COMPILED_EXECUTOR_START_OUTSIDE_DOMAIN");seq=[];seen={};x=_clone(start)
        while (d:=digest(x)) not in seen:seen[d]=len(seq);seq.append(x);x=c["next"][d]
        k=seen[d];v=seq[steps] if steps<len(seq) else seq[k+(steps-k)%(len(seq)-k)];return self._produce(aid,v,"generated_algorithm",[start,steps])
    def execute(self,artifact_id,*args,**kwargs):
        a=self.artifacts[artifact_id]
        if a.artifact_kind in ("Sensor","SensorProcedure"):return self.run_sensor(artifact_id,*args,**kwargs)
        if a.artifact_kind=="GeneratedAlgorithm":return self.run_generated_algorithm(artifact_id,*args,**kwargs)
        raise Residual("ARTIFACT_KIND_NOT_EXECUTABLE")
    def synthesize_proof_program(self,language_id,candidates,context):
        rejected=[]
        for p in candidates:
            try:checks=self._verify_proof(p,context,self.languages[language_id])
            except Residual as e:rejected.append(e.kind);continue
            aid=self._artifact("ProofProgram",language_id,p,EXACT);return {"artifact_id":aid,"checks":checks}
        raise Residual("NO_LAWFUL_MORPHISM_IN_SEARCH_APERTURE",rejected=rejected)
    def _verify_proof(self,p,ctx,lang):
        clauses=p.get("clauses") if isinstance(p,dict) and p.get("kind")=="ProofProgram" else None
        if not clauses:raise Residual("PROOF_PROGRAM_EMPTY")
        checks=0
        def term(t,env):
            if isinstance(t,str) and t.startswith("$"):return env[t[1:]]
            if isinstance(t,dict) and "apply" in t:return self.bridge.evaluate_primitive(lang.primitives[t["apply"]],[term(x,env) for x in t.get("args",[])])
            return t
        def pred(q,env):
            nonlocal checks;checks+=1
            if q.get("op")=="ASSERT_EQ" and not _same(term(q.get("left"),env),term(q.get("right"),env)):raise Residual("PROOF_ASSERT_EQ_FAIL")
        for q in clauses:
            if q.get("op")=="FORALL_DOMAIN":
                for v in ctx.get("domains",{}).get(q["var"],[]):pred(q["body"],{q["var"]:v})
            else:pred(q,ctx.get("env",{}))
        return checks
    def compile_optimized_transition(self,transition,max_steps,*,reference_transition=None,model_evidence_id=None,reference_evidence_id=None,**kw):
        if model_evidence_id and not _same(self.evidence[model_evidence_id]["value"],transition):raise Residual("OPTIMIZER_EVIDENCE_VALUE_MISMATCH")
        if reference_evidence_id and not _same(self.evidence[reference_evidence_id]["value"],reference_transition):raise Residual("OPTIMIZER_EVIDENCE_VALUE_MISMATCH")
        dom=list(transition);n="transition_"+digest(transition)[:8];s={"kind":"finite_table","domains":[dom],"codomain":dom,"table":[{"in":[x],"out":transition[x]} for x in dom]};pr=dict(self.languages["PNR12_BASE"].primitives);pr[n]=s;r=self.bridge.check_language(pr);lid="l_"+digest(("exact",s))[:24]
        if lid not in self.languages:self._append("LanguageCommitted",{"language_id":lid,"parent_language_id":"PNR12_BASE","primitives":pr,"generated_primitives":[n],"certificate_id":"c_"+digest(r)[:24],"receipt":r,"assumptions":[],"validity_scope":{"source":"verified_transition"},"artifact_dependencies":[]})
        return self.compile_generated_algorithm(lid,n,max_steps)
    def optimize_finite_machine(self,states,observations,transitions,*,reference_observations=None,reference_transitions=None,model_evidence_id=None,reference_evidence_id=None,model_observation_evidence_id=None,reference_observation_evidence_id=None,action,max_steps):
        _safe_keys(states,"states")
        for eid,val in ((model_evidence_id,transitions),(reference_evidence_id,reference_transitions),(model_observation_evidence_id,observations),(reference_observation_evidence_id,reference_observations)):
            if eid and not _same(self.evidence[eid]["value"],val):raise Residual("OPTIMIZER_EVIDENCE_VALUE_MISMATCH")
        groups={};
        for s in states:groups.setdefault(digest(observations[s]),[]).append(s)
        changed=True
        while changed:
            changed=False;idx={s:i for i,g in enumerate(groups.values()) for s in g};new={}
            for s in states:new.setdefault((digest(observations[s]),tuple(sorted((a,idx[d]) for a,d in transitions.get(s,{}).items()))),[]).append(s)
            if len(new)!=len(groups):groups={digest(k):v for k,v in new.items()};changed=True
        gs=list(groups.values());q={s:f"q{i}" for i,g in enumerate(gs) for s in g};qt={f"q{i}":f"q{next(j for j,h in enumerate(gs) if transitions[g[0]][action] in h)}" for i,g in enumerate(gs)};comp=self.compile_optimized_transition(qt,max_steps);return {"quotient_states":len(gs),"state_count":len(gs),"executor_id":comp["artifact_id"],"program_id":comp["artifact_id"],"partition":q,"state_assignment":q}
    def run_optimized_transition(self,aid,start,steps):return self.run_generated_algorithm(aid,start,steps)
    def counterexample(self,counterexample_id,falsified_assumptions=(),detail=None,parents=(),affected_claims=(),affected_artifacts=(),affected_constitutions=(),*,language_ids=(),artifact_ids=()):
        _reject(counterexample_id in self._counterexample_ids,"COUNTEREXAMPLE_ID_ALREADY_BOUND");_reject(self._contains_produced(detail),"COUNTEREXAMPLE_DETERMINANT_INPUT_MUST_BE_EXTERNAL")
        for lid in language_ids:
            if lid not in self.languages:raise Residual("UNKNOWN_LANGUAGE",language_id=lid)
        for aid in artifact_ids:
            if aid not in self.artifacts:raise Residual("UNKNOWN_ARTIFACT",artifact_id=aid)
        fals=set(_ids(falsified_assumptions));langs=set(language_ids);arts=set(artifact_ids);claims=set(affected_claims);cons=set(affected_constitutions)
        for lid,l in self.languages.items():
            if fals&set(l.assumptions):langs.add(lid)
        for aid,a in self.artifacts.items():
            if fals&set(a.assumptions) or a.language_id in langs or set(a.artifact_dependencies)&arts:arts.add(aid)
        for cid,st in self.standings.items():
            if fals&set(st.assumptions) or any(self._producer_deps(e)&arts for e in st.evidence_roots):claims.add(cid)
        for cid,h in self.constitutions.items():
            if fals&set(h.assumptions) or set(h.artifact_dependencies)&arts:cons.add(cid)
        oid=self._append("Counterexample",{"counterexample_id":counterexample_id,"falsified_assumptions":sorted(fals),"retracted_claim_ids":sorted(claims),"excluded_constitution_ids":sorted(cons),"detail":detail or {}})
        for lid in sorted(langs):self._append("LanguageRetracted",{"language_id":lid,"counterexample_id":counterexample_id},[oid])
        for aid in sorted(arts):self._append("ArtifactRetracted",{"artifact_id":aid,"counterexample_id":counterexample_id},[oid])
        return {"counterexample_occurrence_id":oid,"retracted_languages":sorted(langs),"retracted_artifacts":sorted(arts),"retracted_claims":sorted(claims),"excluded_constitutions":sorted(cons)}
    def audit(self):
        self._check_seals();self._disk_check();self._validate_watermark()
        if abs(math.fsum(float(o.payload["cost"]) for o in self._occ if o.kind=="ResourceCharge")-self.resource_used)>1e-12:raise Residual("AUDIT_RESOURCE_ACCOUNTING_MISMATCH")
        for lid,l in self.languages.items():
            if l.status=="QUALIFIED":self.bridge.check_language(dict(l.primitives))
        for aid,a in self.artifacts.items():
            if a.standing not in DEAD:
                if a.language_id not in self.languages or self.languages[a.language_id].status!="QUALIFIED":raise Residual("AUDIT_LIVE_ARTIFACT_LANGUAGE_NOT_QUALIFIED")
                if a.certificate_id not in self._artifact_certs:raise Residual("AUDIT_ARTIFACT_CERTIFICATE_INVALID")
                cert=self._artifact_certs[a.certificate_id]
                if cert.payload.get("program_digest") and cert.payload["program_digest"]!=digest(a.program):raise Residual("AUDIT_ARTIFACT_PROGRAM_CERTIFICATE_MISMATCH")
        return {"status":"PASS","occurrences":len(self._occ),"languages":len(self.languages),"artifacts":len(self.artifacts),"standings":len(self.standings),"fabric_digest":self.fabric_digest()}
    def snapshot(self):
        a=self.audit();return {"schema":SCHEMA,"version":VERSION,"fabric_digest":a["fabric_digest"],"occurrences":len(self._occ),"resource_used":self.resource_used,"resource_limit":self.resource_limit,"languages":{k:{"status":v.status,"parent":v.parent_language_id,"generated":list(v.generated_primitives)} for k,v in self.languages.items()},"artifacts":{k:{"kind":v.artifact_kind,"language":v.language_id,"standing":v.standing} for k,v in self.artifacts.items()},"audit":"PASS"}
PNR.add_operation=PNR.extend;PNR.compile_transition=PNR.compile_optimized_transition;PNR.run_transition=PNR.run_optimized_transition;PNR.reduce_machine=PNR.optimize_finite_machine;PNR.match_systems=PNR.synthesize_transfer;PNR.find_rewrite=PNR.synthesize_rewrite;PNR.search=PNR.synthesize
__all__=["PNR","PNRError","Residual","ProposalLanguage","GeneratedArtifact","ProducedValue","ClaimStanding","StandingKind","Experiment","canonical","digest","VERSION","SCHEMA"]
