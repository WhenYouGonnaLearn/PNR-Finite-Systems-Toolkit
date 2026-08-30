from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pnr12 import Experiment, PNR, ProducedValue, Residual, StandingKind, digest


def runtime(path=None, budget=1e9, max_risk=1.0, allow_irreversible=False):
    p = PNR(path or tempfile.mkdtemp())
    p.set_contracts(max_risk=max_risk, allow_irreversible=allow_irreversible, budget=budget)
    return p


class PNR12Tests(unittest.TestCase):
    def residual(self, kind, fn):
        with self.assertRaises(Residual) as cm:
            fn()
        self.assertEqual(cm.exception.kind, kind)
        return cm.exception

    @staticmethod
    def step_training():
        return [{"in": [0], "out": 1}]

    @staticmethod
    def step_heldout():
        return [{"in": [1], "out": 0}]

    def generated_step(self, p, *, assumptions=()):
        return p.generate_finite_extension(
            "PNR12_BASE", "step", [[0, 1]], [0, 1],
            self.step_training(), self.step_heldout(), assumptions=assumptions,
        )

    def identity_sensor(self, p, *, label=7):
        aid = p.propose_sensor([{"op": "get", "key": "x"}], "x")
        p.calibrate_sensor(aid, [{"raw": {"x": label}, "label": label}])
        return aid

    def assess_single(self, p, claim_id, evidence_id, dim="reading"):
        p.require(claim_id, [dim])
        return p.assess_claim(claim_id, [evidence_id])

    def test_01_frozen_basis_is_deliberately_inadequate(self):
        p = runtime()
        base = p.languages["PNR12_BASE"]
        self.assertTrue(all(len(spec["domains"]) == 1 for spec in base.primitives.values()))
        self.residual("PRIMITIVE_NOT_IN_LANGUAGE", lambda: p.generate_sensor("PNR12_BASE", "missing", ["a", "b"], []))

    def test_02_post_source_hash_language_genesis_restart_retract_replace_restart(self):
        source = Path(__file__).with_name("pnr12.py").read_bytes()
        source_hash = hashlib.sha256(source).hexdigest()
        nonce = "pf_" + source_hash[:16]
        self.assertNotIn(nonce.encode(), source)

        bits = bin(int(source_hash[:2], 16))[2:].zfill(8)
        rows = []
        for i in range(8):
            inp = [(i >> 2) & 1 == 1, (i >> 1) & 1 == 1, i & 1 == 1]
            rows.append({"in": inp, "out": bits[i] == "1"})

        td = tempfile.mkdtemp()
        p = runtime(td)
        g1 = p.generate_boolean_extension("PNR12_BASE", nonce, 3, rows[:-1], rows[-1:])
        lid1 = g1["language_id"]
        aid1 = p.generate_sensor(
            lid1, nonce, ["a", "b", "c"],
            [{"raw": {"a": r["in"][0], "b": r["in"][1], "c": r["in"][2]}, "label": r["out"]} for r in rows],
        )
        self.assertEqual(p.languages[lid1].status, "QUALIFIED")
        self.assertEqual(p.artifacts[aid1].standing, "CALIBRATED_EMPIRICAL")

        p2 = PNR(td)
        self.assertEqual(p2.languages[lid1].status, "QUALIFIED")
        self.assertEqual(p2.artifacts[aid1].standing, "CALIBRATED_EMPIRICAL")

        replacement = [dict(r) for r in rows]
        replacement[-1] = {"in": list(rows[-1]["in"]), "out": not rows[-1]["out"]}
        p2.counterexample("regime_shift", language_ids=[lid1], detail={"artifact_id": aid1})
        self.assertEqual(p2.languages[lid1].status, "RETRACTED")
        self.assertEqual(p2.artifacts[aid1].standing, "RETRACTED_BY_COUNTEREXAMPLE")
        self.residual("ARTIFACT_NOT_EXECUTABLE", lambda: p2.run_sensor(aid1, {"a": False, "b": False, "c": False}))

        g2 = p2.generate_boolean_extension("PNR12_BASE", nonce + "_r", 3, replacement[:-1], replacement[-1:])
        lid2 = g2["language_id"]
        aid2 = p2.generate_sensor(
            lid2, nonce + "_r", ["a", "b", "c"],
            [{"raw": {"a": r["in"][0], "b": r["in"][1], "c": r["in"][2]}, "label": r["out"]} for r in replacement],
        )
        self.assertNotEqual(lid1, lid2)

        p3 = PNR(td)
        self.assertEqual(p3.languages[lid1].status, "RETRACTED")
        self.assertEqual(p3.languages[lid2].status, "QUALIFIED")
        self.assertEqual(p3.artifacts[aid2].standing, "CALIBRATED_EMPIRICAL")

    def test_03_direct_language_commit_is_private(self):
        p = runtime()
        bad = {
            "kind": "finite_table",
            "domains": [[False, True], [False, True]],
            "codomain": [False, True],
            "table": [{"in": [False, False], "out": False}],
        }
        self.residual("DIRECT_LANGUAGE_COMMIT_NOT_PUBLIC", lambda: p.extend_language("PNR12_BASE", "bad", bad))
        self.residual("BRIDGE_TABLE_NOT_TOTAL", lambda: p.bridge.check_primitive(bad))

    def test_04_reserved_occurrence_ingress_is_private(self):
        p = runtime()
        self.residual("RESERVED_OCCURRENCE_INGRESS", lambda: p.append("EvidenceOccurrence", {"value": 1}, ()))

    def test_05_resource_law_preempts_language_search(self):
        p = PNR(tempfile.mkdtemp())
        p.set_budget(0.0001)
        self.residual(
            "RESOURCE_EXHAUSTED",
            lambda: p.generate_boolean_extension(
                "PNR12_BASE", "xor", 2,
                [{"in": [False, False], "out": False}],
                [{"in": [False, True], "out": True}, {"in": [True, False], "out": True}, {"in": [True, True], "out": False}],
            ),
        )

    def test_06_independence_is_not_sufficiency(self):
        p = runtime()
        p.add_obligation("c", "exact", ["x", "y"])
        a = p.add_evidence(1, ["x"], ["a"])
        b = p.add_evidence(1, ["x"], ["b"])
        st = p.assess_claim("c", [a, b])
        self.assertEqual(st.dependency_status, "INDEPENDENT")
        self.assertEqual(st.kind, StandingKind.TYPED_RESIDUAL)

    def test_07_correlated_evidence_is_not_independent(self):
        p = runtime()
        p.add_obligation("c", "exact", ["x"])
        a = p.add_evidence(1, ["x"], ["same"])
        b = p.add_evidence(1, ["x"], ["same"])
        st = p.assess_claim("c", [a, b])
        self.assertEqual(st.dependency_status, "CORRELATED")
        self.assertEqual(st.kind, StandingKind.TYPED_RESIDUAL)

    def test_08_independent_conflict_preserves_fibre(self):
        p = runtime()
        p.add_obligation("c", "exact", ["x"])
        a = p.add_evidence(1, ["x"], ["a"], assertions={"x": 1})
        b = p.add_evidence(2, ["x"], ["b"], assertions={"x": 2})
        self.assertEqual(p.assess_claim("c", [a, b]).kind, StandingKind.UNRESOLVED_EQUIVALENCE_CLASS)

    def test_09_counterexample_retracts_assumption_dependents_after_restart(self):
        td = tempfile.mkdtemp()
        p = runtime(td)
        p.add_assumption("A", "premise")
        p.add_obligation("c", "exact", ["x"], admissible_assumptions=["A"])
        e = p.add_evidence(1, ["x"], ["ref"])
        self.assertEqual(p.assess_claim("c", [e], assumptions=["A"]).kind, StandingKind.EXACT_UNDER_ASSUMPTIONS)
        cid = p.propose_constitution({"probe": 1}, assumptions=["A"], payload={"relevant_claims": ["c"]})
        p.counterexample("boom", ["A"], {"constitution_id": cid})
        q = PNR(td)
        self.assertEqual(q.standings["c"].kind, StandingKind.RETRACTED_BY_COUNTEREXAMPLE)
        self.assertFalse(q.constitutions[cid]["active"])

    def test_10_experiment_selection_is_endogenous(self):
        p = runtime(max_risk=0.5)
        p.add_obligation("target", "exact", ["behavior"])
        hidden = 173
        for n in range(256):
            p.propose_constitution({f"b{i}": (n >> i) & 1 for i in range(8)}, payload={"relevant_claims": ["target"], "n": n})
        probes = [Experiment(f"b{i}", cost=1 + i * 0.01, risk=0.01) for i in range(8)]
        used = 0
        while len(p.active_constitutions()) > 1:
            e = p.schedule_next("target", probes, protected_value=10)["experiment"]
            p.perform_experiment(e, (hidden >> int(e.experiment_id[1:])) & 1)
            used += 1
        self.assertEqual(used, 8)
        self.assertEqual(p.active_constitutions()[0].payload["n"], hidden)

    def test_11_transfer_map_is_synthesized_not_supplied(self):
        p = runtime()
        ss, ts = ["a", "b", "c"], ["u", "v", "w"]
        low = {"a": {"n": "b"}, "b": {"n": "c"}, "c": {"n": "a"}}
        high = {"u": {"x": "v"}, "v": {"x": "w"}, "w": {"x": "u"}}
        so, to = {"a": 0, "b": 1, "c": 2}, {"u": 1, "v": 2, "w": 0}
        r = p.synthesize_transfer(ss, ["n"], low, high, ts, ["x"], so, to)
        tau = p.externalize(r["tau"], reason="inspect synthesized transfer")
        omega = p.externalize(r["omega"], reason="inspect synthesized transfer")
        self.assertEqual(set(tau), set(ss))
        self.assertEqual(omega, {"n": "x"})
        self.assertTrue(all(so[s] == to[tau[s]] for s in ss))

    def test_12_symbolic_rewrite_requires_generated_semantics(self):
        p = runtime()
        src = {"op": "add", "args": [{"var": "x"}, {"var": "x"}]}
        train = [{"env": {"x": 2}, "expected": 4}, {"env": {"x": 3}, "expected": 9}]
        held = [{"env": {"x": 5}, "expected": 25}, {"env": {"x": -2}, "expected": 4}]
        self.residual("NO_LAWFUL_MORPHISM_IN_SEARCH_APERTURE", lambda: p.synthesize_rewrite(src, train, held))
        domain = [-2, 2, 3, 5]
        g = p.generate_finite_extension(
            "PNR12_BASE", "sq", [domain], [4, 9, 25],
            [{"in": [-2], "out": 4}, {"in": [2], "out": 4}, {"in": [3], "out": 9}],
            [{"in": [5], "out": 25}],
        )
        r = p.synthesize_rewrite(src, train, held, g["language_id"])
        replacement = p.externalize(r["replacement"], reason="inspect synthesized rewrite")
        self.assertEqual(replacement, {"call": "sq", "args": [{"var": "x"}]})

    def test_13_generated_algorithm_handles_1e100(self):
        p = runtime(budget=1e9)
        g = self.generated_step(p)
        a = p.compile_generated_algorithm(g["language_id"], "step", 10**100)
        result = p.externalize(p.run_generated_algorithm(a["artifact_id"], 0, 10**100), reason="inspect algorithm result")
        self.assertEqual(result, (10**100) % 2)
        self.assertLess(a["levels"], 400)

    def test_14_language_transport_requalifies_target(self):
        p = runtime()
        g = self.generated_step(p)
        lid = p.transport_language(g["language_id"], {"task": "other"}, {"step": [{"in": [0], "out": 1}]})
        self.assertEqual(p.languages[lid].status, "QUALIFIED")
        self.residual(
            "LANGUAGE_TRANSPORT_REQUALIFICATION_FAIL",
            lambda: p.transport_language(g["language_id"], {"task": "bad"}, {"step": [{"in": [0], "out": 0}]}),
        )

    def test_15_generated_proof_program_stays_under_fixed_kernel(self):
        p = runtime()
        g = self.generated_step(p)
        program = {
            "kind": "ProofProgram",
            "clauses": [{"op": "FORALL_DOMAIN", "var": "x", "body": {"op": "ASSERT_EQ", "left": {"apply": "step", "args": ["$x"]}, "right": {"apply": "step", "args": ["$x"]}}}],
        }
        r = p.synthesize_proof_program(g["language_id"], [program], {"domains": {"x": [0, 1]}})
        self.assertEqual(p.artifacts[r["artifact_id"]].standing, "EXACT_UNDER_ASSUMPTIONS")

    def test_16_behavioral_quotient_and_exact_executor(self):
        p = runtime(budget=1e9)
        states = list(range(64))
        observations = {s: s % 8 for s in states}
        transitions = {s: {"n": (s + 8) % 64} for s in states}
        m = p.add_evidence(transitions, ["transition"], ["model"])
        r = p.add_evidence(dict(transitions), ["transition"], ["reference"])
        mo = p.add_evidence(observations, ["observation"], ["model_obs"])
        ro = p.add_evidence(dict(observations), ["observation"], ["ref_obs"])
        out = p.optimize_finite_machine(
            states, observations, transitions,
            reference_observations=observations, reference_transitions=transitions,
            model_evidence_id=m, reference_evidence_id=r,
            model_observation_evidence_id=mo, reference_observation_evidence_id=ro,
            action="n", max_steps=10**6,
        )
        self.assertEqual(out["quotient_states"], 8)
        res = p.externalize(p.run_optimized_transition(out["executor_id"], "q0", 10**6), reason="inspect optimized transition")
        self.assertIn(res, {f"q{i}" for i in range(8)})

    def test_17_caller_owned_semantics_are_detached(self):
        p = runtime()
        spec = {"kind": "finite_table", "domains": [[0, 1]], "codomain": [0, 1], "table": [{"in": [0], "out": 1}, {"in": [1], "out": 0}]}
        p.bridge.check_primitive(spec)
        original = digest(spec)
        spec["table"][0]["out"] = 0
        self.assertNotEqual(digest(spec), original)

    def test_18_out_of_band_language_and_artifact_mutation_fail_closed(self):
        p = runtime()
        g = self.generated_step(p)
        with self.assertRaises(TypeError):
            p.languages[g["language_id"]].primitives["step"]["table"][0]["out"] = 0

        p = runtime()
        g = self.generated_step(p)
        a = p.compile_generated_algorithm(g["language_id"], "step", 10)["artifact_id"]
        with self.assertRaises(TypeError):
            p.artifacts[a].program["compiled"]["max_steps"] = 999

    def test_19_resource_cost_and_contract_cannot_be_laundered(self):
        p = PNR(tempfile.mkdtemp())
        p.set_budget(1)
        self.residual("RESOURCE_COST_INVALID", lambda: p.charge(-1, "refund"))
        p.charge(0.5, "real")
        self.residual("RESOURCE_BUDGET_CANNOT_INCREASE", lambda: p.set_budget(2))
        p.resource_used = -100
        self.residual("RESOURCE_STATE_MUTATED_OUT_OF_BAND", lambda: p.charge(0.1, "bypass"))

    def test_20_authority_contract_cannot_be_loosened_or_mutated(self):
        p = runtime(max_risk=0.2, allow_irreversible=False)
        self.residual("AUTHORITY_CONTRACT_CANNOT_LOOSEN", lambda: p.set_contracts(max_risk=0.3, allow_irreversible=False, budget=1e9))
        p.authority["max_risk"] = 99
        self.residual("AUTHORITY_STATE_MUTATED_OUT_OF_BAND", lambda: p.perform_experiment(Experiment("x", risk=1), 1))

    def test_21_contradictory_language_evidence_is_typed(self):
        p = runtime()
        self.residual(
            "LANGUAGE_EVIDENCE_CONFLICT",
            lambda: p.generate_finite_extension("PNR12_BASE", "f", [[0, 1]], [0, 1], [{"in": [0], "out": 0}, {"in": [0], "out": 1}], [{"in": [1], "out": 0}]),
        )

    def test_22_language_evidence_outside_declared_carrier_is_typed(self):
        p = runtime()
        self.residual("LANGUAGE_EVIDENCE_INPUT_OUTSIDE_DOMAIN", lambda: p.generate_finite_extension("PNR12_BASE", "f", [[0, 1]], [0, 1], [{"in": [2], "out": 0}], []))
        self.residual("LANGUAGE_EVIDENCE_OUTPUT_OUTSIDE_CODOMAIN", lambda: p.generate_finite_extension("PNR12_BASE", "g", [[0, 1]], [0, 1], [{"in": [0], "out": 2}], []))

    def test_23_sensor_calibration_must_exist_and_runtime_errors_are_typed(self):
        p = runtime()
        g = self.generated_step(p)
        self.residual("CALIBRATION_INSUFFICIENT", lambda: p.generate_sensor(g["language_id"], "step", ["x"], []))
        aid = p.generate_sensor(g["language_id"], "step", ["x"], [{"raw": {"x": 0}, "label": 1}])
        self.residual("SENSOR_INPUT_KEY_MISSING", lambda: p.run_sensor(aid, {}))
        self.residual("SENSOR_INPUT_ARITY_MISMATCH", lambda: p.generate_sensor(g["language_id"], "step", ["x", "y"], [{"raw": {"x": 0, "y": 1}, "label": 1}]))

    def test_24_steps_are_integral_bounded_and_in_domain(self):
        p = runtime()
        g = self.generated_step(p)
        aid = p.compile_generated_algorithm(g["language_id"], "step", 10)["artifact_id"]
        self.residual("STEP_COUNT_INVALID", lambda: p.run_generated_algorithm(aid, 0, 1.5))
        self.residual("STEP_COUNT_INVALID", lambda: p.run_generated_algorithm(aid, 0, -1))
        self.residual("COMPILED_EXECUTOR_OUTSIDE_SCOPE", lambda: p.run_generated_algorithm(aid, 0, 11))
        self.residual("COMPILED_EXECUTOR_START_OUTSIDE_DOMAIN", lambda: p.run_generated_algorithm(aid, 9, 1))

    def test_25_retracted_language_and_artifact_identities_do_not_resurrect(self):
        p = runtime()
        g = self.generated_step(p)
        lid = g["language_id"]
        p.counterexample("bad_language", language_ids=[lid])
        self.residual("LANGUAGE_REALIZATION_ALREADY_EXISTS", lambda: self.generated_step(p))

        p = runtime()
        g = self.generated_step(p)
        aid = p.compile_generated_algorithm(g["language_id"], "step", 10)["artifact_id"]
        p.counterexample("bad_artifact", artifact_ids=[aid])
        self.residual("ARTIFACT_REALIZATION_ALREADY_EXISTS", lambda: p.compile_generated_algorithm(g["language_id"], "step", 10))

    def test_26_assumption_counterexample_retracts_languages_artifacts_and_claims(self):
        td = tempfile.mkdtemp(); p = runtime(td)
        p.add_assumption("A", "premise")
        p.add_obligation("c", "exact", ["x"], admissible_assumptions=["A"])
        e = p.add_evidence(1, ["x"], ["root"])
        p.assess_claim("c", [e], assumptions=["A"])
        lid = self.generated_step(p, assumptions=["A"])["language_id"]
        aid = p.generate_sensor(lid, "step", ["x"], [{"raw": {"x": 0}, "label": 1}], assumptions=["A"])
        p.counterexample("badA", falsified_assumptions=["A"])
        self.assertEqual(p.languages[lid].status, "RETRACTED")
        self.assertEqual(p.artifacts[aid].standing, "RETRACTED_BY_COUNTEREXAMPLE")
        self.assertEqual(p.standings["c"].kind, StandingKind.RETRACTED_BY_COUNTEREXAMPLE)
        self.residual("ASSUMPTION_RETRACTED_BY_COUNTEREXAMPLE", lambda: self.generated_step(p, assumptions=["A"]))
        q = PNR(td)
        self.assertEqual(q.languages[lid].status, "RETRACTED")
        self.assertEqual(q.artifacts[aid].standing, "RETRACTED_BY_COUNTEREXAMPLE")

    def test_27_causal_parent_roots_are_inherited_automatically(self):
        p = runtime()
        a = p.add_evidence(1, ["x"], ["A"])
        b = p.add_evidence(1, ["x"], ["pretend-independent"], parents=[a])
        p.add_obligation("c", "exact", ["x"])
        st = p.assess_claim("c", [a, b])
        self.assertEqual(st.dependency_status, "CORRELATED")

    def test_28_unrooted_evidence_never_counts_as_independent(self):
        p = runtime(); p.add_obligation("c", "exact", ["x"])
        a = p.add_evidence(1, ["x"], [])
        st = p.assess_claim("c", [a])
        self.assertEqual(st.dependency_status, "UNROOTED")
        self.assertEqual(st.kind, StandingKind.TYPED_RESIDUAL)

    def test_29_empty_proof_program_cannot_earn_standing(self):
        p = runtime()
        before = len(p.artifacts)
        err = self.residual("NO_LAWFUL_MORPHISM_IN_SEARCH_APERTURE", lambda: p.synthesize_proof_program("PNR12_BASE", [{"kind": "ProofProgram", "clauses": []}], {}))
        self.assertIn("PROOF_PROGRAM_EMPTY", err.detail["rejected"])
        self.assertEqual(len(p.artifacts), before)

    def test_30_finite_language_work_is_bounded_by_rows_not_imaginary_candidates(self):
        p = runtime()
        rows = [{"in": [bool((i >> b) & 1) for b in range(5)], "out": bool(i & 1)} for i in range(32)]
        g = p.generate_boolean_extension("PNR12_BASE", "five_bit", 5, rows[:-1], rows[-1:])
        self.assertEqual(g["tested"], 32)
        self.residual("LANGUAGE_SEARCH_APERTURE_EXCEEDED", lambda: p.generate_boolean_extension("PNR12_BASE", "too_large", 17, [], []))

    def test_31_optimizer_cannot_use_unrelated_evidence_as_independent_receipts(self):
        p = runtime()
        transitions = {0: 1, 1: 0}
        m = p.add_evidence({0: 0, 1: 1}, ["transition"], ["m"])
        r = p.add_evidence(transitions, ["transition"], ["r"])
        self.residual("OPTIMIZER_EVIDENCE_VALUE_MISMATCH", lambda: p.compile_optimized_transition(transitions, 10, reference_transition=transitions, model_evidence_id=m, reference_evidence_id=r))

    def test_32_two_live_writers_fail_closed_instead_of_corrupting_log(self):
        td = tempfile.mkdtemp(); a = PNR(td); b = PNR(td)
        a.add_evidence(1, ["x"], ["a"])
        self.residual("CONCURRENT_STATE_MODIFICATION", lambda: b.add_evidence(2, ["x"], ["b"]))
        PNR(td)

    def test_33_truncated_occurrence_log_is_a_typed_failure(self):
        td = tempfile.mkdtemp(); p = runtime(td); p.add_evidence(1, ["x"], ["a"])
        path = Path(td) / "occurrences.jsonl"
        data = path.read_text(); path.write_text(data[:-7])
        self.residual("OCCURRENCE_LOG_PARSE_ERROR", lambda: PNR(td))

    def test_34_duplicate_assumption_and_obligation_ids_are_rejected(self):
        p = runtime(); p.add_assumption("A", "one")
        self.residual("ASSUMPTION_ID_ALREADY_BOUND", lambda: p.add_assumption("A", "two"))
        p.add_obligation("c", "exact", ["x"])
        self.residual("CLAIM_OBLIGATION_ALREADY_BOUND", lambda: p.add_obligation("c", "exact", ["y"]))

    def test_35_counterexample_references_must_exist_before_commit(self):
        p = runtime(); before = len(p.occurrences)
        self.residual("UNKNOWN_LANGUAGE", lambda: p.counterexample("bad", language_ids=["missing"]))
        self.assertEqual(len(p.occurrences), before)

    def test_36_experiment_ids_must_be_unique_and_objects_typed(self):
        p = runtime(); p.propose_constitution({"e": 0}); p.propose_constitution({"e": 1})
        self.residual("EXPERIMENT_ID_DUPLICATE", lambda: p.select_discriminating_experiment([Experiment("e"), Experiment("e")]))
        self.residual("EXPERIMENT_OBJECT_REQUIRED", lambda: p.select_discriminating_experiment([object()]))

    def test_37_frozen_base_qualification_depends_on_bridge_certificate_occurrence(self):
        p = runtime()
        q = [o for o in p.occurrences if o.kind == "ProposalLanguageQualifiedOccurrence" and o.payload["language_id"] == "PNR12_BASE"][0]
        self.assertEqual(len(q.parents), 1)
        self.assertEqual(p.by_id[q.parents[0]].kind, "BridgeCertificateOccurrence")

    def test_38_authority_irreversible_flags_are_strict_booleans(self):
        p = PNR(tempfile.mkdtemp())
        self.residual("AUTHORITY_IRREVERSIBLE_FLAG_INVALID", lambda: p.set_contracts(allow_irreversible="false", budget=10))
        with self.assertRaises(ValueError):
            Experiment("bad", irreversible=1)

    def test_39_counterexample_identity_cannot_be_rebound_even_after_restart(self):
        d = tempfile.mkdtemp(); p = runtime(d)
        p.counterexample("cx_unique")
        self.residual("COUNTEREXAMPLE_ID_ALREADY_BOUND", lambda: p.counterexample("cx_unique"))
        q = PNR(d)
        self.residual("COUNTEREXAMPLE_ID_ALREADY_BOUND", lambda: q.counterexample("cx_unique"))

    def test_40_reasoning_and_occurrence_views_are_read_only(self):
        p = runtime(); eid = p.add_evidence({"v": 1}, ["v"], ["root"])
        with self.assertRaises(TypeError):
            p.evidence[eid]["lineage_roots"][0] = "forged"
        o = p.occurrences[0]
        with self.assertRaises(TypeError):
            o.payload["forged"] = True

    def test_41_generated_output_is_opaque_until_externalized(self):
        p = runtime(); aid = self.identity_sensor(p, label=4)
        out = p.run_sensor(aid, {"x": 4})
        self.assertIsInstance(out, ProducedValue)
        with self.assertRaises(TypeError):
            bool(out)
        with self.assertRaises(TypeError):
            _ = (out == 4)
        raw = p.externalize(out, reason="inspect value")
        self.assertEqual(raw, 4)

    def test_42_observing_produced_value_preserves_provenance_automatically(self):
        p = runtime(); aid = self.identity_sensor(p, label=7)
        out = p.run_sensor(aid, {"x": 7})
        e = p.observe(out, ["reading"], ["lab"])
        self.assertIn(aid, p.evidence[e]["producer_artifacts"])
        st = self.assess_single(p, "c42", e)
        self.assertEqual(st.kind, StandingKind.CALIBRATED_EMPIRICAL)
        p.refute("bad42", artifact_ids=[aid])
        self.assertEqual(p.standings["c42"].kind, StandingKind.RETRACTED_BY_COUNTEREXAMPLE)

    def test_43_transform_preserves_producer_closure_and_restart(self):
        td = tempfile.mkdtemp(); p = runtime(td); aid = self.identity_sensor(p, label=7)
        e = p.observe(p.run_sensor(aid, {"x": 7}), ["reading"], ["lab"])
        t = p.add_transform(e, "identity", 7, 7, False)
        self.assertIn(aid, p.evidence[t]["producer_artifacts"])
        st = self.assess_single(p, "c43", t)
        self.assertEqual(st.kind, StandingKind.CALIBRATED_EMPIRICAL)
        p.refute("sensor_bad", artifact_ids=[aid])
        q = PNR(td)
        self.assertEqual(q.standings["c43"].kind, StandingKind.RETRACTED_BY_COUNTEREXAMPLE)
        self.assertIn(aid, q.evidence[t]["producer_artifacts"])

    def test_44_same_sensor_readings_do_not_count_as_independent(self):
        p = runtime(); aid = self.identity_sensor(p, label=7)
        a = p.observe(p.run_sensor(aid, {"x": 7}), ["reading"], ["lab-a"])
        b = p.observe(p.run_sensor(aid, {"x": 7}), ["reading"], ["lab-b"])
        st = self.assess_single(p, "c44", a)
        self.assertEqual(st.kind, StandingKind.CALIBRATED_EMPIRICAL)
        p.require("c44_pair", ["reading"])
        pair = p.assess_claim("c44_pair", [a, b])
        self.assertEqual(pair.dependency_status, "CORRELATED")
        self.assertEqual(pair.kind, StandingKind.TYPED_RESIDUAL)

    def test_45_externalized_values_cross_an_explicit_boundary(self):
        p = runtime(); aid = self.identity_sensor(p, label=7)
        raw = p.externalize(p.run_sensor(aid, {"x": 7}), reason="notebook export")
        e = p.observe(raw, ["reading"], ["hand-typed"])
        st = self.assess_single(p, "c45", e)
        self.assertEqual(st.kind, StandingKind.EXACT_UNDER_ASSUMPTIONS)
        p.refute("sensor_bad", artifact_ids=[aid])
        self.assertEqual(p.standings["c45"].kind, StandingKind.EXACT_UNDER_ASSUMPTIONS)

    def test_46_unrelated_claim_survives_artifact_retraction(self):
        p = runtime(); aid = self.identity_sensor(p, label=7)
        dependent = p.observe(p.run_sensor(aid, {"x": 7}), ["reading"], ["lab-a"])
        independent = p.add_evidence(9, ["reading"], ["lab-b"])
        self.assertEqual(self.assess_single(p, "dep", dependent).kind, StandingKind.CALIBRATED_EMPIRICAL)
        self.assertEqual(self.assess_single(p, "ind", independent).kind, StandingKind.EXACT_UNDER_ASSUMPTIONS)
        p.refute("sensor_bad", artifact_ids=[aid])
        self.assertEqual(p.standings["dep"].kind, StandingKind.RETRACTED_BY_COUNTEREXAMPLE)
        self.assertEqual(p.standings["ind"].kind, StandingKind.EXACT_UNDER_ASSUMPTIONS)

    def test_47_retracted_or_unqualified_artifact_cannot_produce_new_evidence(self):
        p = runtime(); proposed = p.propose_sensor([{"op": "identity"}], "x")
        self.residual("EVIDENCE_PRODUCER_NOT_EXECUTABLE", lambda: p.observe(True, ["reading"], ["lab"], produced_by=proposed))
        p.calibrate_sensor(proposed, [{"raw": True, "label": True}])
        p.refute("bad", artifact_ids=[proposed])
        self.residual("EVIDENCE_PRODUCER_NOT_EXECUTABLE", lambda: p.observe(True, ["reading"], ["lab"], produced_by=proposed))

    def test_48_counterexample_determinant_input_must_be_external(self):
        p = runtime(); aid = self.identity_sensor(p, label=4)
        out = p.run_sensor(aid, {"x": 4})
        self.residual("COUNTEREXAMPLE_DETERMINANT_INPUT_MUST_BE_EXTERNAL", lambda: p.counterexample("cx48", detail={"seen": out}))

    def test_49_generic_surface_is_small_and_self_describing(self):
        import inspect
        names = ["observe", "require", "extend", "synthesize", "refute", "snapshot"]
        self.assertEqual([n for n in names if callable(getattr(PNR, n, None))], names)
        for n in names[:-1]:
            self.assertTrue((inspect.getdoc(getattr(PNR, n)) or "").strip())
        self.assertIn("candidates", inspect.signature(PNR.synthesize).parameters)
        self.assertIn("qualify", inspect.signature(PNR.synthesize).parameters)

    def test_50_audit_sweeps_live_state_and_snapshot_refuses_corruption(self):
        p = runtime(); aid = self.identity_sensor(p, label=4)
        e = p.observe(p.run_sensor(aid, {"x": 4}), ["reading"], ["lab"])
        self.assess_single(p, "c50", e)
        self.assertEqual(p.audit()["status"], "PASS")
        p.resource_used = -1
        self.residual("RESOURCE_STATE_MUTATED_OUT_OF_BAND", lambda: p.snapshot())

class PNR12RollbackProtectionTests(unittest.TestCase):
    def residual(self, kind, fn):
        with self.assertRaises(Residual) as cm:
            fn()
        self.assertEqual(cm.exception.kind, kind)
        return cm.exception

    @staticmethod
    def make_retracted(path):
        p = runtime(path)
        g = p.generate_boolean_extension(
            "PNR12_BASE", "xor_rollback", 2,
            [{"in": [False, False], "out": False}, {"in": [False, True], "out": True}, {"in": [True, False], "out": True}],
            [{"in": [True, True], "out": False}],
        )
        lid = g["language_id"]
        aid = p.generate_sensor(lid, "xor_rollback", ["a", "b"], [
            {"raw": {"a": False, "b": False}, "label": False},
            {"raw": {"a": False, "b": True}, "label": True},
            {"raw": {"a": True, "b": False}, "label": True},
            {"raw": {"a": True, "b": True}, "label": False},
        ])
        pre = p.anchor()
        p.counterexample("rollback_counterexample", language_ids=[lid])
        post = p.anchor()
        return p, lid, aid, pre, post

    def test_51_valid_prefix_truncation_is_caught_by_local_high_water(self):
        td = tempfile.mkdtemp()
        p, lid, aid, pre, post = self.make_retracted(td)
        log = Path(td) / "occurrences.jsonl"
        lines = log.read_text().splitlines(True)
        log.write_text("".join(lines[:pre["seq"]]))
        self.residual("FABRIC_ROLLBACK_DETECTED", lambda: PNR(td))

    def test_52_stale_watermark_behind_valid_log_is_repaired_forward(self):
        td = tempfile.mkdtemp()
        p = runtime(td)
        mark = Path(td) / ".pnr12-high-water.json"
        stale = mark.read_bytes()
        p.add_evidence(1, ["x"], ["later"])
        final = p.anchor()
        mark.write_bytes(stale)
        q = PNR(td)
        self.assertEqual(q.anchor(), final)
        recorded = json.loads(mark.read_text())
        self.assertEqual(recorded["seq"], final["seq"])
        self.assertEqual(recorded["head_digest"], final["head_digest"])

    def test_53_external_anchor_catches_whole_directory_rollback(self):
        import shutil
        live = tempfile.mkdtemp(); backup = tempfile.mkdtemp()
        p = runtime(live)
        g = p.generate_boolean_extension(
            "PNR12_BASE", "xor_ext_anchor", 2,
            [{"in": [False, False], "out": False}, {"in": [False, True], "out": True}, {"in": [True, False], "out": True}],
            [{"in": [True, True], "out": False}],
        )
        lid = g["language_id"]
        aid = p.generate_sensor(lid, "xor_ext_anchor", ["a", "b"], [{"raw": {"a": False, "b": False}, "label": False}])
        # Snapshot the entire directory before the retraction, including its local watermark.
        for child in Path(live).iterdir():
            if child.is_file() and child.name != ".pnr12.lock":
                shutil.copy2(child, Path(backup) / child.name)
        p.counterexample("external_anchor_counterexample", language_ids=[lid])
        anchor = p.anchor()
        # The old snapshot is internally self-consistent, so local rollback detection alone cannot reject it.
        old = PNR(backup)
        self.assertEqual(old.languages[lid].status, "QUALIFIED")
        self.residual("FABRIC_EXTERNAL_ROLLBACK_DETECTED", lambda: PNR(backup, expect_anchor=anchor))

    def test_54_external_anchor_accepts_monotone_descendants(self):
        td = tempfile.mkdtemp(); p = runtime(td)
        anchor = p.anchor()
        p.add_evidence(1, ["x"], ["later"])
        q = PNR(td, expect_anchor=anchor)
        self.assertGreater(q.anchor()["seq"], anchor["seq"])

    def test_55_external_anchor_rejects_divergent_history(self):
        import shutil
        a = tempfile.mkdtemp(); b = tempfile.mkdtemp()
        pa = runtime(a); pa.add_evidence(1, ["x"], ["branch-a"]); anchor = pa.anchor()
        pb = runtime(b); pb.add_evidence(2, ["x"], ["branch-b"])
        # Same or greater length is not enough; the anchored prefix must be the same history.
        self.residual("FABRIC_EXTERNAL_DIVERGENCE_DETECTED", lambda: PNR(b, expect_anchor=anchor))

    def test_56_exact_expect_digest_is_strict_current_identity(self):
        td = tempfile.mkdtemp(); p = runtime(td)
        d = p.fabric_digest()
        PNR(td, expect_digest=d)
        p.add_evidence(1, ["x"], ["later"])
        self.residual("FABRIC_EXTERNAL_ANCHOR_MISMATCH", lambda: PNR(td, expect_digest=d))

    def test_57_corrupt_high_water_is_typed_failure(self):
        td = tempfile.mkdtemp(); p = runtime(td)
        mark = Path(td) / ".pnr12-high-water.json"
        raw = json.loads(mark.read_text()); raw["head_digest"] = "0" * 64
        mark.write_text(json.dumps(raw))
        self.residual("FABRIC_HIGH_WATER_INVALID", lambda: PNR(td))

class PNR12RollbackAuditEdgeTests(unittest.TestCase):
    def residual(self, kind, fn):
        with self.assertRaises(Residual) as cm:
            fn()
        self.assertEqual(cm.exception.kind, kind)
        return cm.exception

    def test_58_audit_detects_live_disk_truncation_even_before_reopen(self):
        td = tempfile.mkdtemp(); p = runtime(td)
        p.add_evidence(1, ["x"], ["tail"])
        log = Path(td) / "occurrences.jsonl"
        lines = log.read_text().splitlines(True)
        log.write_text("".join(lines[:-1]))
        self.residual("OCCURRENCE_DISK_STATE_DIVERGED", lambda: p.audit())

    def test_59_watermark_io_failure_does_not_turn_committed_append_into_false_failure(self):
        td = tempfile.mkdtemp(); p = runtime(td)
        original = p._write_local_watermark
        def fail_mark():
            raise OSError("simulated watermark fsync failure")
        p._write_local_watermark = fail_mark
        eid = p.add_evidence(1, ["x"], ["committed"])
        self.assertIn(eid, p.evidence)
        self.assertTrue(p._watermark_degraded)
        p._write_local_watermark = original
        # Reopen treats the old watermark as a valid ancestor and repairs it forward.
        q = PNR(td)
        self.assertIn(eid, q.evidence)
        self.assertEqual(q.audit()["status"], "PASS")


class PNR12RollbackWatermarkDeterminantTests(unittest.TestCase):
    def residual(self, kind, fn):
        with self.assertRaises(Residual) as cm:
            fn()
        self.assertEqual(cm.exception.kind, kind)

    def test_60_retraction_advances_watermark_without_anchor_side_effect(self):
        td = tempfile.mkdtemp(); p = runtime(td)
        g = p.generate_boolean_extension(
            "PNR12_BASE", "xor_watermark", 2,
            [{"in": [False, False], "out": False}, {"in": [False, True], "out": True}, {"in": [True, False], "out": True}],
            [{"in": [True, True], "out": False}],
        )
        lid = g["language_id"]
        aid = p.generate_sensor(lid, "xor_watermark", ["a", "b"], [{"raw": {"a": False, "b": False}, "label": False}])
        out = p.counterexample("watermark_det", language_ids=[lid])
        cseq = p.by_id[out["counterexample_occurrence_id"]].seq
        # No p.anchor() call here: the append path itself must have advanced the local HWM.
        log = Path(td) / "occurrences.jsonl"
        lines = log.read_text().splitlines(True)
        log.write_text("".join(lines[:cseq - 1]))
        self.residual("FABRIC_ROLLBACK_DETECTED", lambda: PNR(td))

if __name__ == "__main__":
    unittest.main(verbosity=2)
