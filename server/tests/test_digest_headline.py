"""The headline of a digest must be a headline, not a one-word label.

Found against the live model: a story starting with "SIMULACIÓN." classified as
``not_a_poll`` with p = 0.68-0.81 and the sheet came back grey, hiding every item. The
label was being used as the digest headline, and "SIMULACIÓN" reads as "this is not a real
survey".

This matters beyond the demo: every synthetic article in the evaluation corpus is required
to start with that marker, so the bug would have poisoned the whole evaluation with a
plausible-looking "no findings".
"""

from ficha_tecnica.extractor.digest import build_digest_a, build_digest_b, build_state

BODY = (
    "El Partido Popular ganaria las elecciones segun una encuesta de Demoscopia Ficticia S.L. "
    "El estudio se hizo con 1.200 entrevistas entre el 3 y el 9 de noviembre."
)


def test_a_one_word_opening_label_is_not_the_headline() -> None:
    digest = build_digest_a("SIMULACIÓN. " + BODY)

    assert digest["headline"] != "SIMULACIÓN."
    assert "encuesta de Demoscopia" in digest["headline"]


def test_the_label_is_kept_as_context_and_not_thrown_away() -> None:
    """The reader's eye should still be able to tell this is a simulation."""
    digest = build_digest_a("SIMULACIÓN. " + BODY)

    whole = build_state(digest)
    assert "SIMULACIÓN" in whole


def test_a_short_dateline_does_not_become_the_headline_on_its_own() -> None:
    digest = build_digest_b("Madrid, 12 de octubre. " + BODY)

    assert digest["headline"] != "Madrid, 12 de octubre."
    assert "El Partido Popular" in digest["headline"]


def test_a_normal_story_keeps_its_first_sentence_as_headline() -> None:
    digest = build_digest_a(BODY)

    assert digest["headline"].startswith("El Partido Popular")


def test_a_text_made_only_of_short_sentences_still_produces_a_headline() -> None:
    digest = build_digest_a("Sondeo. Urgente. El PP sube. El PSOE baja.")

    assert digest["headline"]


def test_the_lede_never_repeats_the_headline() -> None:
    digest = build_digest_a("SIMULACIÓN. " + BODY)

    assert digest["headline"] not in digest["lede"]


def test_figure_sentences_still_start_after_the_headline() -> None:
    digest = build_digest_b("SIMULACIÓN. " + BODY)

    assert all(digest["headline"] != sentence for sentence in digest["figure_sentences"])
