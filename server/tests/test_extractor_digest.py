"""Bounded digests A/B/C and the ``state`` string sent to Clef (ENC-05 T3/T4)."""

import json
from pathlib import Path

from ficha_tecnica.extractor.digest import (
    build_digest_a,
    build_digest_b,
    build_digest_c,
    build_state,
    estimate_tokens,
)

SNAPSHOTS = Path(__file__).parent / "fixtures" / "snapshots"

# A fixed press-style story used by the content tests and the state snapshots.
FIXED_TEXT = (
    "El PP adelantaría al PSOE en intención de voto y gobernaría en minoría, según el "
    "barómetro electoral de Example Consulting publicado este domingo.\n"
    "La encuesta se realizó con 1.200 entrevistas telefónicas entre el 2 y el 6 de mayo, "
    "con un margen de error de ±2,8 puntos y un nivel de confianza del 95 %.\n"
    "El universo del estudio es la población residente en España de 18 años o más.\n"
    "El trabajo de campo lo llevó a cabo el instituto Fieldworks por encargo de la cadena "
    "NE.\n"
    "Los datos están ponderados por sexo, edad y tamaño de hábitat.\n"
    "En estimación de votos, el PP obtendría un 34,2 % de los sufragios, seis puntos por "
    "delante del PSOE, que se queda en un 28,4 %.\n"
    "Sumar entraría en el Congreso con un 11,3 % y Vox bajaría hasta el 9,8 % de los "
    "votos.\n"
    "El sondeo también preguntó por la valoración de los líderes: el presidente obtiene un "
    "4,1 sobre 10.\n"
    "A la pregunta «¿Votaría usted de nuevo al mismo partido que en 2023?», el 46 % de los "
    "encuestados responde que sí.\n"
    "La ficha técnica completa está publicada en la web del instituto demoscópico."
)

_BUDGETS = {"a": 1200, "b": 500, "c": 400}
_BUILDERS = {"a": build_digest_a, "b": build_digest_b, "c": build_digest_c}


def test_estimate_tokens_rounds_up() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2
    assert estimate_tokens("a" * 8) == 2


def test_huge_text_stays_under_every_budget() -> None:
    sentence = "La encuesta constó de 1.200 entrevistas con un margen de error de ±2,8 puntos."
    huge = "Titular de la encuesta. " + f"{sentence} " * 400
    for name, build in _BUILDERS.items():
        digest = build(huge)
        state = build_state(digest)
        assert estimate_tokens(state) <= _BUDGETS[name], f"digest {name} over budget"
        assert digest["meta"]["chars"] == len(huge)
        assert digest["meta"]["digest_tokens"] == estimate_tokens(state)
        assert digest["meta"]["digest_tokens"] <= _BUDGETS[name]


def test_lede_is_cut_at_a_word_boundary() -> None:
    body = "palabras " * 200  # ~1799 chars: far beyond the lede budget, cuts mid-word
    text = f"Titular corto.\n{body}fin.\nTercera frase con un 34,2 %."
    digest = build_digest_a(text)
    lede = digest["lede"]
    giant = text.split("\n")[1]
    assert giant.startswith(lede)  # the lede is a prefix of the second sentence
    assert giant[len(lede)] == " "  # ... and stops at a word boundary
    assert estimate_tokens(lede) <= 120


def test_digest_a_carries_headline_lede_and_technical_sentences() -> None:
    digest = build_digest_a(FIXED_TEXT)
    assert digest["headline"].startswith("El PP adelantaría")
    assert "1.200 entrevistas" in digest["lede"]
    technical = digest["technical_sentences"]
    assert technical, "expected technical sentences"
    assert len(technical) == len(set(technical)), "duplicated technical sentence"
    assert all(sentence not in digest["lede"] for sentence in technical)
    assert all(sentence not in digest["headline"] for sentence in technical)
    assert any("margen de error" in sentence for sentence in digest["lede"].split(". "))
    assert any("universo" in sentence for sentence in digest["lede"].split(". "))
    assert any("34,2 %" in sentence for sentence in technical)
    assert any("ficha técnica" in sentence for sentence in technical)


def test_digest_b_keeps_party_percentages_intact_and_unsanitized() -> None:
    digest = build_digest_b(FIXED_TEXT)
    figures = digest["figure_sentences"]
    assert 0 < len(figures) <= 6
    assert len(figures) == len(set(figures)), "duplicated figure sentence"
    percentage = next(sentence for sentence in figures if "34,2 %" in sentence)
    assert "PP" in percentage and "PSOE" in percentage  # intact, nothing sanitized away
    assert any("%" in sentence for sentence in figures)


def test_digest_c_carries_only_quoted_questions() -> None:
    digest = build_digest_c(FIXED_TEXT)
    assert set(digest) == {"quoted_questions", "meta"}
    quoted = digest["quoted_questions"]
    assert quoted, "expected the quoted question to be picked"
    assert len(quoted) == len(set(quoted))
    assert quoted == ["¿Votaría usted de nuevo al mismo partido que en 2023?"]
    assert all("34,2 %" not in sentence for sentence in quoted)  # plain results are not wording
    assert all("46 %" not in sentence for sentence in quoted)  # the answer around it stays out


def test_state_is_a_compact_json_string() -> None:
    digest = build_digest_a(FIXED_TEXT)
    state = build_state(digest)
    assert isinstance(state, str)
    assert state == json.dumps(json.loads(state), ensure_ascii=False, separators=(",", ":"))
    assert json.loads(state) == digest
    assert "adelantaría" in state  # ensure_ascii=False: no \\uXXXX escapes


def test_snapshot_states_of_the_fixed_text() -> None:
    states = {name: build_state(build(FIXED_TEXT)) for name, build in _BUILDERS.items()}
    for name, state in states.items():
        path = SNAPSHOTS / f"digest_state_{name}.json"
        assert state + "\n" == path.read_text(encoding="utf-8"), f"snapshot {name} drifted"
