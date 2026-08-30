import json, tempfile, unittest
from pathlib import Path
from pnr12 import PNR, Residual, canonical, digest

class Attack(unittest.TestCase):
 def r(self,k,f):
  with self.assertRaises(Residual) as c:f()
  self.assertEqual(c.exception.kind,k)
 def test_frozenset_roundtrip_and_dict_key(self):
  d=tempfile.mkdtemp();p=PNR(d);e=p.add_evidence({frozenset({1,2}):"ok"},["x"],["r"]);q=PNR(d);self.assertEqual(q.evidence[e]["value"][frozenset({1,2})],"ok");self.assertEqual(q.audit()["status"],"PASS")
 def test_python_key_collision_rejected_before_exact_transfer(self):
  p=PNR(tempfile.mkdtemp());self.r("PYTHON_KEY_SEMANTIC_COLLISION",lambda:p.synthesize_transfer([False,0],["a"],{False:{"a":False},0:{"a":0}},{"u":{"x":"u"},"v":{"x":"v"}},["u","v"],["x"]))
 def test_views_and_occurrences_are_immutable(self):
  p=PNR(tempfile.mkdtemp());e=p.add_evidence({"x":1},["x"],["r"])
  with self.assertRaises(TypeError):p.evidence[e]["value"]["x"]=2
  with self.assertRaises(TypeError):p.evidence["fake"]={}
  with self.assertRaises(TypeError):p.occurrences[0].payload["x"]=1
 def test_float_budget_boundary(self):
  p=PNR(tempfile.mkdtemp());p.set_budget(.3);p.charge(.1,"a");p.charge(.2,"b");self.assertAlmostEqual(p.resource_used,.3);self.assertEqual(p.audit()["status"],"PASS")
 def test_unknown_dependency_rejected(self):
  p=PNR(tempfile.mkdtemp());self.r("UNKNOWN_ARTIFACT_DEPENDENCY",lambda:p.synthesize(kind="x",candidates=[1],build=lambda x:{"x":x},qualify=lambda x:True,depends_on=["missing"]))
 def test_foreign_sensor_context_is_typed(self):
  p=PNR(tempfile.mkdtemp());a=p.propose_sensor([{"op":"identity"}],"x");p.calibrate_sensor(a,[{"raw":1,"label":1}]);self.r("SENSOR_RUNTIME_ERROR",lambda:p.run_sensor(a,1,context=object()))
 def test_single_record_generated_language_commit(self):
  p=PNR(tempfile.mkdtemp());n=len(p.occurrences);g=p.generate_finite_extension("PNR12_BASE","flip",[[0,1]],[0,1],[{"in":[0],"out":1}],[{"in":[1],"out":0}]);tail=p.occurrences[n:];self.assertEqual(sum(o.kind=="LanguageCommitted" for o in tail),1);self.assertEqual(p.languages[g["language_id"]].status,"QUALIFIED")
 def test_single_record_artifact_commit(self):
  p=PNR(tempfile.mkdtemp());g=p.generate_finite_extension("PNR12_BASE","flip",[[0,1]],[0,1],[{"in":[0],"out":1}],[{"in":[1],"out":0}]);n=len(p.occurrences);a=p.compile_generated_algorithm(g["language_id"],"flip",100);tail=p.occurrences[n:];self.assertEqual(sum(o.kind=="ArtifactCommitted" for o in tail),1);self.assertEqual(p.artifacts[a["artifact_id"]].standing,"EXACT_UNDER_ASSUMPTIONS")
 def test_disk_payload_tamper_killed(self):
  d=tempfile.mkdtemp();p=PNR(d);p.add_evidence(1,["x"],["r"]);path=Path(d)/"occurrences.jsonl";rows=path.read_text().splitlines();r=json.loads(rows[-1]);r["payload"][1][-1][1][1]="2";rows[-1]=json.dumps(r,separators=(",",":"));path.write_text("\n".join(rows)+"\n");self.r("OCCURRENCE_HASH_INVALID",lambda:PNR(d))
 def test_false_externalized_provenance_does_not_retract(self):
  p=PNR(tempfile.mkdtemp());a=p.propose_sensor([{"op":"identity"}],"x");p.calibrate_sensor(a,[{"raw":7,"label":7}]);raw=p.externalize(p.run_sensor(a,7),reason="boundary");e=p.observe(raw,["x"],["manual"]);p.require("c",["x"]);self.assertEqual(p.assess_claim("c",[e]).kind.value,"EXACT_UNDER_ASSUMPTIONS");p.refute("bad",artifact_ids=[a]);self.assertEqual(p.standings["c"].kind.value,"EXACT_UNDER_ASSUMPTIONS")

if __name__=='__main__':unittest.main(verbosity=2)
