"""ENC-16: the synthetic corpus and its construction-derived gold labels.

The corpus is generated deterministically from templates, never with a model. The
assertions here pin what the harness and the metrics depend on: 40 unique bases in
four styles, gold derived from the mutation (never hand-written), M14 identical to
its base, and a dev/test split cut by base article, never by case.
"""

from decimal import Decimal

import pytest

from ficha_tecnica.evaluation.dataset import (
    BLOCK_FOR_ITEM,
    EVALUATION_SEED,
    MUTATION_IDS,
    MUTATIONS_PER_BASE,
    EvalCase,
    blocks_of,
    build_dataset,
    split_of_base,
)
from ficha_tecnica.extractor.candidates import all_candidates
from ficha_tecnica.extractor.entities import find_entities
from ficha_tecnica.extractor.metrics import extract_confidence, extract_margin, extract_sample_size
from ficha_tecnica.policy import theoretical_margin
from ficha_tecnica.sanitizer import find_leaks, mask_vote_estimates

BASE_COUNT = 40
MUTATED_CASE_COUNT = 240
DEV_BASES = 24
TEST_BASES = 16

#: Blocks whose disappearance M15 is about: the technical sheet becomes a link.
M15_ABSENT = (
    "a_sample_size",
    "a_margin",
    "a_confidence",
    "a_universe",
    "a_sampling_system",
    "a_selection_procedure",
    "a_mode",
    "a_fieldwork_dates",
    "a_question_text",
    "a_nonresponse",
    "a_weighting",
)

#: The nine deletions of the spec, mapped to the formal item each one removes.
DELETIONS = {
    "M1": ("a_sample_size",),
    "M2": ("a_margin",),
    "M3": ("a_fieldwork_dates",),
    "M4": ("a_entity",),
    "M5": ("a_client",),
    "M6": ("a_universe",),
    "M7": ("a_sampling_system",),
    "M8": ("a_question_text",),
    "M9": ("a_nonresponse",),
}


@pytest.fixture
def ds():
    return build_dataset()


def base_of(case: EvalCase, ds) -> EvalCase:
    return ds.bases_by_id[case.base_id]


def test_the_corpus_is_deterministic():
    first = build_dataset()
    second = build_dataset()

    assert [case.text for case in first.all_cases] == [case.text for case in second.all_cases]
    assert [case.case_id for case in first.all_cases] == [case.case_id for case in second.all_cases]
    assert [case.gold for case in first.all_cases] == [case.gold for case in second.all_cases]


def test_the_seed_is_fixed_and_documented():
    # The generator must not read global random state: the seed is a module constant.
    assert isinstance(EVALUATION_SEED, int)


def test_forty_bases_in_four_styles(ds):
    assert len(ds.bases) == BASE_COUNT
    styles = sorted({case.style for case in ds.bases})
    assert len(styles) == 4
    for style in styles:
        assert sum(1 for case in ds.bases if case.style == style) == BASE_COUNT // 4
    texts = [case.text for case in ds.bases]
    assert len(set(texts)) == BASE_COUNT, "every base must be a distinct article"
    assert len({case.base_id for case in ds.bases}) == BASE_COUNT


def test_every_text_carries_the_simulation_marker_and_fictitious_actors(ds):
    for case in ds.all_cases:
        assert case.text.startswith("SIMULACIÓN"), case.case_id

    # No REAL formation may appear in the corpus. The fictitious ones are expected to be
    # found: they are registered in the curated lists precisely so the evaluation exercises
    # the same code path as a real story.
    simulation_names = {
        entry.name for entry in _curated_entities("parties.yaml", "simulation_parties")
    }
    for case in ds.all_cases:
        found = {span.name for span in find_entities(case.text) if span.kind == "party"}
        assert found <= simulation_names, (case.case_id, sorted(found - simulation_names))


def test_every_base_states_every_checklist_item_and_the_code_finds_it(ds):
    ids = tuple(item["id"] for item in _checklist_items())
    for case in ds.bases:
        for item_id in ids:
            assert case.gold.items[item_id] == "present", (case.case_id, item_id)
            # The corpus is only useful when the code layer can locate the evidence.
            assert all_candidates(case.text)[item_id], (case.case_id, item_id)


def test_the_code_layer_reads_the_arithmetic_the_base_declares(ds):
    for case in ds.bases[:10]:
        scenario = ds.scenario_of(case)
        assert extract_sample_size(case.text) == scenario.sample_size
        assert extract_margin(case.text) == scenario.margin
        assert extract_confidence(case.text) == scenario.confidence
        # The declared margin sits just above the theoretical minimum, so M4 is
        # silent on every base and only M10 can make it fire.
        assert scenario.margin > theoretical_margin(scenario.sample_size)


def test_two_hundred_forty_mutated_cases_covering_all_mutations(ds):
    mutated = [case for case in ds.all_cases if case.mutation != "base"]
    assert len(mutated) == MUTATED_CASE_COUNT
    assert len({case.case_id for case in ds.all_cases}) == len(ds.all_cases)
    assert {case.mutation for case in mutated} == set(MUTATION_IDS)
    for case in mutated:
        assert len(case.base_mutations) == MUTATIONS_PER_BASE
        assert case.text.startswith("SIMULACIÓN")
        assert case.text != base_of(case, ds).text


def test_deletion_gold_is_derived_case_by_case(ds):
    for case in ds.all_cases:
        if case.mutation not in DELETIONS:
            continue
        base = base_of(case, ds)
        expected = dict(base.gold.items)
        for item_id in DELETIONS[case.mutation]:
            expected[item_id] = "absent"
        assert case.gold.items == expected, case.case_id
        # The deletions are honest: the sentence that stated the item is gone. (The cue
        # extractor is broad -- "de 3,8" reads like a date to it -- so what must vanish
        # is the statement itself, not every regex hit.)
        removed_blocks = {
            block
            for item_id, block in BLOCK_FOR_ITEM.items()
            if item_id in DELETIONS[case.mutation]
        }
        for name, base_sentence in blocks_of(base, ds):
            if name in removed_blocks:
                assert base_sentence not in case.text, (case.case_id, name)


def test_m14_gold_is_identical_to_its_base(ds):
    m14 = [case for case in ds.all_cases if case.mutation == "M14"]
    assert m14, "the false-accusation gauge must exist in the corpus"
    for case in m14:
        base = base_of(case, ds)
        assert case.gold.items == base.gold.items
        assert case.gold.expected_flags == base.gold.expected_flags
        # ...and it really is a paraphrase, not a copy.
        assert case.text != base.text


def test_m15_replaces_the_sheet_with_a_link(ds):
    for case in ds.all_cases:
        if case.mutation != "M15":
            continue
        expected = dict(base_of(case, ds).gold.items)
        for item_id in M15_ABSENT:
            expected[item_id] = "absent"
        assert case.gold.items == expected, case.case_id
        assert case.gold.items["a_external_sheet"] == "present"


def test_m10_declares_half_the_theoretical_margin(ds):
    checked = 0
    for case in ds.all_cases:
        if case.mutation != "M10":
            continue
        scenario = ds.scenario_of(base_of(case, ds))
        expected = (scenario.margin_theoretical / 2).quantize(Decimal("0.01"))
        assert extract_margin(case.text) == expected
        assert extract_sample_size(case.text) == scenario.sample_size
        assert "M4" in case.gold.expected_flags
        checked += 1
    assert checked == 16


def test_flag_mutations_declare_what_should_fire(ds):
    expected_by_mutation = {"M10": "M4", "M11": "M11", "M12": "M12", "M13": "M13"}
    for case in ds.all_cases:
        flag = expected_by_mutation.get(case.mutation)
        if flag is None:
            continue
        # The item labels do not move: only the declared expectation does.
        assert case.gold.items == base_of(case, ds).gold.items, case.case_id
        assert case.gold.expected_flags == frozenset({flag}), case.case_id
    # Base articles must expect no flag at all.
    for case in ds.bases:
        assert case.gold.expected_flags == frozenset(), case.case_id


def test_the_split_is_cut_by_base_article_never_by_case(ds):
    assert len([case for case in ds.bases if case.split == "dev"]) == DEV_BASES
    assert len([case for case in ds.bases if case.split == "test"]) == TEST_BASES
    for case in ds.all_cases:
        assert case.split == split_of_base(case.base_id), case.case_id


def test_mutation_rotation_hits_every_mutation_evenly(ds):
    mutated = [case for case in ds.all_cases if case.mutation != "base"]
    for mutation in MUTATION_IDS:
        count = sum(1 for case in mutated if case.mutation == mutation)
        assert count == MUTATED_CASE_COUNT // len(MUTATION_IDS), mutation


def test_the_corpus_exercises_the_sanitizer_instead_of_bypassing_it(ds):
    """The corpus must contain vote estimates, or the sanitizer is never tested.

    This used to assert that no case contained a detectable estimate, which made the
    "zero leaks" metric vacuously true: the detector found nothing because the corpus used
    formations the curated list did not know. The corpus is INPUT; the rule is about what
    the system emits, so the assertion moves to the sanitized text and is pinned by
    requiring that masking actually happens.
    """
    masked_somewhere = 0
    for case in ds.all_cases:
        masked = mask_vote_estimates(case.text)
        if masked != case.text:
            masked_somewhere += 1
        assert find_leaks(masked) == [], case.case_id

    assert masked_somewhere > 0, "no case exercised the sanitizer"


def _checklist_items():
    from ficha_tecnica.schema.checklist import load_checklist

    return [item.model_dump() for item in load_checklist().items]


def _curated_entities(filename: str, key: str) -> tuple:
    """One section of a curated list, read straight from config/."""
    from pathlib import Path

    import yaml

    from ficha_tecnica.extractor.entities import EntityEntry

    config = Path(__file__).resolve().parents[2] / "config" / filename
    with config.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return tuple(
        EntityEntry(name=entry["name"], variants=tuple(entry["variants"]))
        for entry in data.get(key, [])
    )
