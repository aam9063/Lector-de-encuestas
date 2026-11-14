"""Abbreviations must not split a sentence.

Found against the live model: "Demoscopia Ficticia S.L., cuya sede..." was cut at "S." and
again at "L.", so the digest sent the model a headline ending in "Ficticia S." and a lede
starting with "L. , cuya sede...". The model read that as not a poll and the sheet went
grey.

Spanish press copy is full of abbreviations: company suffixes, countries, honorifics and
"etc.". Splitting inside them corrupts every state built from the text.
"""

import pytest

from ficha_tecnica.extractor.candidates import split_sentences

TEXT = (
    "Demoscopia Ficticia S.L., con sede en la calle Imaginaria 12, realizó el estudio. "
    "El informe lo firma la Dra. Ejemplo para la Fundación Imaginaria, etc. "
    "Los datos de EE.UU. y de la S.A. matriz se revisaron después."
)


def pieces(text: str) -> list[str]:
    return [text[span.start : span.end] for span in split_sentences(text)]


def test_a_company_suffix_does_not_end_a_sentence() -> None:
    sentences = pieces(TEXT)

    assert sentences[0].startswith("Demoscopia Ficticia S.L.,")
    assert not any(sentence.startswith("L.") for sentence in sentences)


@pytest.mark.parametrize(
    "abbreviation",
    ["S.L.", "S.A.", "EE.UU.", "etc.", "Dra.", "Sr.", "Dr.", "núm.", "pág.", "aprox."],
)
def test_common_abbreviations_stay_inside_their_sentence(abbreviation: str) -> None:
    text = f"El informe de la entidad {abbreviation} sigue vigente y se publicó ayer."

    sentences = pieces(text)

    assert len(sentences) == 1, sentences
    assert abbreviation in sentences[0]


def test_the_real_terminator_still_splits() -> None:
    sentences = pieces("Primera frase. Segunda frase. Tercera frase.")

    assert sentences == ["Primera frase.", "Segunda frase.", "Tercera frase."]


def test_question_and_exclamation_marks_still_split() -> None:
    sentences = pieces("¿Votaria usted? ¡Claro que si!")

    assert len(sentences) == 2


def test_spans_still_slice_the_original_text() -> None:
    """The masking used to protect abbreviations must not move any index."""
    for span in split_sentences(TEXT):
        assert TEXT[span.start : span.end].strip()


def test_evidence_spans_survive_the_abbreviation_masking() -> None:
    from ficha_tecnica.extractor.candidates import candidates_for

    spans = candidates_for(TEXT, "a_entity_address")

    assert spans
    for span in spans:
        assert TEXT[span.start : span.end].strip()
