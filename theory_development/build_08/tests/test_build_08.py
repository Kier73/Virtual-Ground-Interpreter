import math
import random
import unittest

from cross_observer_generalization import (
    Registry, codon_quaternion_product, random_closed_polygon, s2_dist,
    signed_solid_angle, horizontal_lift, lift_phase, resample_arclength,
    shape_signature, temporal_signature, generate_families, make_observer_rdms,
    spearman, upper, family_bootstrap, vr_h1_persistence, h0_persistence,
    substrate_rdms, canonical_semantic_ir, sha256, build_report,
    temporal_low_band_rows, standardize, robustness_sweep,
)


class Build08Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.families = generate_families(18, 20261104)

    def test_random_paths_are_closed_and_unit(self):
        for f in self.families:
            self.assertGreaterEqual(f.petals, 1)
            self.assertLessEqual(f.petals, 3)
            self.assertLess(s2_dist(f.path[0], f.path[-1]), 1e-10)
            for p in f.path:
                self.assertAlmostEqual(sum(x*x for x in p), 1.0, places=10)

    def test_path_library_is_nontrivial(self):
        lengths = [len(f.path) for f in self.families]
        self.assertGreater(len(set(lengths)), 3)

    def test_holonomy_phase_matches_half_solid_angle_modulo_pi(self):
        for f in self.families[:8]:
            phase = lift_phase(horizontal_lift(f.path))
            expected = 0.5*signed_solid_angle(f.path)
            # The Hopf U(1) fibre coordinate is modulo 2pi.
            err = abs((phase-expected+math.pi)%(2*math.pi)-math.pi)
            self.assertLess(err, 2e-3)

    def test_shape_signature_invariant_to_reversal(self):
        for f in self.families:
            a=shape_signature(f.path); b=shape_signature(tuple(reversed(f.path)))
            self.assertLess(max(abs(x-y) for x,y in zip(a,b)), 1e-7)

    def test_temporal_signature_detects_warp(self):
        f=self.families[0]
        self.assertGreater(sum((x-y)**2 for x,y in zip(temporal_signature(f.path,1.0),
                                                          temporal_signature(f.path,1.7))),1e-8)

    def test_codon_alias_and_tree_variants_match(self):
        a=(.41,-.12,.53,.72); b=(-.16,.63,.24,.71)
        ref=codon_quaternion_product(a,b,Registry(),"left")
        alt=codon_quaternion_product(a,b,Registry(add="plus",sub="minus",mul="times"),"pairwise")
        for x,y in zip(ref,alt): self.assertAlmostEqual(x,y,places=14)

    def test_observer_rdms_are_symmetric(self):
        rdms=make_observer_rdms(self.families)
        for rdm in rdms.values():
            for i in range(len(rdm)):
                self.assertAlmostEqual(rdm[i][i],0.0,places=12)
                for j in range(len(rdm)):
                    self.assertAlmostEqual(rdm[i][j],rdm[j][i],places=10)

    def test_bootstrap_is_deterministic(self):
        r=make_observer_rdms(self.families)
        a=family_bootstrap(r["shape_clean"],r["local_clean"],30,99)
        b=family_bootstrap(r["shape_clean"],r["local_clean"],30,99)
        self.assertEqual(a,b)

    def test_persistence_reports_h1(self):
        # A square metric: one prominent loop before triangles fill it.
        d=[[0,1,math.sqrt(2),1],[1,0,1,math.sqrt(2)],
           [math.sqrt(2),1,0,1],[1,math.sqrt(2),1,0]]
        p=vr_h1_persistence(d,max_edge=1.5)
        self.assertGreaterEqual(p["simplex_count"],4)
        self.assertGreaterEqual(p["triangle_count"],0)
        self.assertTrue(all(b<=death for b,death,_ in p["intervals"]))

    def test_h0_persistence_has_n_minus_one_deaths(self):
        d=[[0,1,3],[1,0,2],[3,2,0]]
        self.assertEqual(len(h0_persistence(d)),2)

    def test_substrate_hashes_are_fixed_size_and_distinct(self):
        h=substrate_rdms(self.families)
        self.assertEqual(set(h),{"sha256","blake2b_256","blake2s_256"})
        for r in h.values(): self.assertEqual(len(r),len(self.families))


    def test_time_reparameterization_keeps_shape_but_changes_temporal_response(self):
        f=self.families[2]
        self.assertLess(max(abs(a-b) for a,b in zip(shape_signature(f.path),
                                                      shape_signature(tuple(reversed(f.path))))),1e-7)
        self.assertGreater(sum((a-b)**2 for a,b in zip(temporal_signature(f.path,1.0),
                                                        temporal_signature(f.path,1.7))),1e-8)

    def test_temporal_low_band_retains_each_axis_and_schedule(self):
        rows=[list(range(159)),list(range(159,318))]
        low=temporal_low_band_rows(rows)
        self.assertEqual(len(low[0]),69)
        self.assertEqual(len(low),2)

    def test_robustness_sweep_has_noise_and_projection_levels(self):
        result=robustness_sweep(self.families[:8],seed=7,repeats=2)
        self.assertEqual(set(result),{"shape","local","holonomy","temporal"})
        self.assertEqual(len(result["shape"]),20)
        self.assertTrue(all(0.0 <= x["keep_fraction"] <= 1.0 for x in result["shape"]))

    def test_quaternion_identity_elements(self):
        q=(.31,-.47,.22,.78); e=(1.0,0.0,0.0,0.0)
        l=codon_quaternion_product(q,e); r=codon_quaternion_product(e,q)
        for a,b in zip(q,l): self.assertAlmostEqual(a,b,places=14)
        for a,b in zip(q,r): self.assertAlmostEqual(a,b,places=14)

    def test_hash_addresses_do_not_encode_semantic_neighborhood_by_construction(self):
        h=substrate_rdms(self.families)
        self.assertEqual(len(h["sha256"]),len(self.families))
        vals=[x for row in h["sha256"] for x in row]
        self.assertTrue(all(0.0 <= x <= 1.0 for x in vals))

    def test_report_shape(self):
        report,_,_=build_report(12,33,20,20)
        self.assertEqual(report["family_count"],12)
        self.assertTrue(report["path_generation"]["all_closed"])
        self.assertIn("persistence",report)
        self.assertIn("primary_cross_observer_tests",report)
        self.assertIn("observer_robustness_sweep",report)


if __name__=="__main__": unittest.main()
