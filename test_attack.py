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

 def test_review_compile_stores_one_step_map(self):
  p=PNR(tempfile.mkdtemp());g=p.generate_finite_extension("PNR12_BASE","step",[[0,1,2]],[0,1,2],[{"in":[0],"out":1},{"in":[1],"out":2}],[{"in":[2],"out":0}]);a=p.compile_generated_algorithm(g["language_id"],"step",10**100);self.assertEqual((a["levels"],a["table_entries"]),(1,3));self.assertEqual(p.externalize(p.run_generated_algorithm(a["artifact_id"],0,10**100),reason="check"),1)
 def test_review_transfer_search_has_preflight_bound(self):
  p=PNR(tempfile.mkdtemp());states=list(range(9));low={i:{"a":i} for i in states};self.r("MORPHISM_SEARCH_APERTURE_EXCEEDED",lambda:p.synthesize_transfer(states,["a"],low,low,states,["a"]))
 def test_review_five_bit_table_is_not_charged_as_2_to_32_search(self):
  p=PNR(tempfile.mkdtemp());p.set_budget(1);rows=[{"in":[bool((i>>b)&1) for b in range(5)],"out":bool(i&1)} for i in range(32)];g=p.generate_boolean_extension("PNR12_BASE","f5",5,rows[:-1],rows[-1:]);self.assertEqual(g["tested"],32);self.assertLess(p.resource_used,.01)
 def test_review_transform_records_declared_change(self):
  p=PNR(tempfile.mkdtemp());e=p.add_evidence(7,["x"],["r"]);t=p.add_transform(e,"round",7,8,True,{"why":"test"});self.assertEqual(p.evidence[t]["assertions"]["_transform"],{"kind":"round","input":7,"lossy":True,"detail":{"why":"test"}});self.r("TRANSFORM_INPUT_MISMATCH",lambda:p.add_transform(e,"x",6,7,False))
 def test_review_reduce_rejects_python_equality_collision(self):
  p=PNR(tempfile.mkdtemp());self.r("PYTHON_KEY_SEMANTIC_COLLISION",lambda:p.reduce_machine([0,False],{0:"x"},{0:{"a":0}},action="a",max_steps=1))
 def test_review_rewrite_uses_check_rows_after_selection(self):
  p=PNR(tempfile.mkdtemp());self.r("REWRITE_HELDOUT_FAIL",lambda:p.find_rewrite({"var":"x"},[{"env":{"x":1},"expected":1}],[{"env":{"x":2},"expected":3}]))
 def test_review_rewrite_candidate_errors_do_not_escape(self):
  p=PNR(tempfile.mkdtemp());self.r("NO_LAWFUL_MORPHISM_IN_SEARCH_APERTURE",lambda:p.find_rewrite({"op":"add","args":[{"var":"x"},{"var":"x"}]},[{"env":{"x":{}},"expected":1}],[]))
 def test_review_sensor_signature_has_no_discarded_metadata(self):
  import inspect
  sig=inspect.signature(PNR.propose_sensor);self.assertNotIn("claim_id",sig.parameters);self.assertNotIn("sensor_lineage_roots",sig.parameters);self.assertFalse(any(x.kind==x.VAR_KEYWORD for x in sig.parameters.values()))
 def test_review_scheduler_uses_claim_and_value(self):
  from pnr12 import Experiment
  p=PNR(tempfile.mkdtemp());p.add_obligation("c1","x",[]);p.add_obligation("c2","x",[])
  p.propose_constitution({"a":0,"b":0},payload={"relevant_claims":["c1"]});p.propose_constitution({"a":1,"b":0},payload={"relevant_claims":["c1"]});p.propose_constitution({"a":0,"b":0},payload={"relevant_claims":["c2"]});p.propose_constitution({"a":0,"b":1},payload={"relevant_claims":["c2"]})
  es=[Experiment("a",cost=.1),Experiment("b",cost=.1)];self.assertEqual(p.schedule_next("c1",es)["experiment"].experiment_id,"a");self.assertEqual(p.schedule_next("c2",es)["experiment"].experiment_id,"b")
  q=PNR(tempfile.mkdtemp());q.add_obligation("c","x",[])
  for i,(a,b) in enumerate([(0,0),(0,0),(1,0),(1,1)]):q.propose_constitution({"a":a,"b":b},payload={"relevant_claims":["c"],"i":i})
  es=[Experiment("a",cost=10),Experiment("b",cost=.1)];self.assertEqual(q.schedule_next("c",es,protected_value=1)["experiment"].experiment_id,"b");self.assertEqual(q.schedule_next("c",es,protected_value=10)["experiment"].experiment_id,"a")

if __name__=='__main__':unittest.main(verbosity=2)
