"""The synthetic evaluation corpus (section 11.1) with gold labels by construction.

Why templates instead of a generative model: the design doc foresaw generating the 40
base articles with a NaN model, but a model would cost API money, add nondeterminism,
and make the corpus impossible to review line by line. A template generator is free,
byte-reproducible for a fixed seed, and the corpus can be diffed in review like any
other file. The trade-off is wording variety, which the real hand-labelled news set
(section 11.1, item 4) is there to cover.

Construction rules the whole corpus obeys:

- every article starts with the SIMULACIÓN marker and only uses fictitious actors
  ("Demoscopia Ficticia S.L.", "Partido Cohete"); no real name ever appears;
- every base states every checklist item, so the base gold is "present" for all of them;
- the gold is derived, never written: each mutation declares which blocks it changes
  and the case receives the recomputed gold;
- M14 is a paraphrase by construction: same blocks, same figures, reworded sentences;
  its gold must be identical to its base's gold, and a test asserts it;
- the dev/test split is cut by base article, never by case, so mutations of the same
  text never cross the boundary.

Fact sentences read without written accents: the code layer folds accents when it
locates evidence, so either form is found, and the accentless forms also cover the
social-network style where accents are routinely dropped.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from random import Random

from ficha_tecnica.evaluation.metrics import GoldLabel
from ficha_tecnica.policy import theoretical_margin

#: Fixed seed for every variation. Same seed, same corpus, every time.
EVALUATION_SEED = 2026

SCENARIO_COUNT = 10
STYLE_COUNT = 4
BASE_COUNT = SCENARIO_COUNT * STYLE_COUNT
STYLES = ("agencia", "diario_local", "television", "red_social")
MUTATIONS_PER_BASE = 6
DEV_SHARE = 0.6

MutationId = str  # "M1".."M15", or "base" for the unmutated article

#: The mutation ids of the spec, in the order of the section 11.1 table.
MUTATION_IDS: tuple[MutationId, ...] = tuple(f"M{i}" for i in range(1, 16))

#: Block name of every checklist item, i.e. the sentence that states it.
BLOCK_FOR_ITEM: Mapping[str, str] = {
    "a_entity": "entity",
    "a_entity_address": "address",
    "a_client": "client",
    "a_sample_size": "sample",
    "a_margin": "margin",
    "a_confidence": "confidence",
    "a_universe": "universe",
    "a_sampling_system": "sampling",
    "a_selection_procedure": "selection",
    "a_mode": "mode",
    "a_fieldwork_dates": "dates",
    "a_question_text": "question",
    "a_nonresponse": "nonresponse",
    "a_weighting": "weighting",
    "a_external_sheet": "external",
}

FICTITIOUS_POLLSTERS: tuple[tuple[str, str], ...] = (
    ("Demoscopia Ficticia S.L.", "Calle Inventada 12, Madrid"),
    ("Sondeos Imaginarios S.A.", "Avenida Supuesta 3, Barcelona"),
    ("Instituto Quimerico S.L.U.", "Paseo Ensonacion 8, Valencia"),
    ("Barometro Inventado S.A.U.", "Calle Fabula 45, Sevilla"),
    ("Panel Onirico S.L.", "Calle Utopia 7, Bilbao"),
    ("Encuestas Noveladas S.A.", "Calle Quimera 21, Zaragoza"),
    ("Estudios Fabula S.L.U.", "Avenida Apocrifa 1, Malaga"),
    ("Medicion Ilusoria S.A.U.", "Calle Virtual 33, Murcia"),
    ("Termometro Sonado S.L.", "Paseo Irreal 5, Valladolid"),
    ("Investigacion Nube S.A.", "Calle Ambiguo 19, A Coruna"),
)

FICTITIOUS_CLIENTS: tuple[str, ...] = (
    "El Diario de Aqui",
    "La Gaceta Inventada",
    "Onda Ejemplo",
    "Television Simulada",
    "El Periodico Novelado",
    "Canal Ficcion Noticias",
    "La Voz Apocrifa",
    "Diario Supuesto",
    "Emisora Ficticia",
    "El Faro Inventado",
)

FICTITIOUS_PARTIES: tuple[str, ...] = (
    "Partido Cohete",
    "Partido Brujula",
    "Partido Farol",
    "Partido Timon",
    "Partido Vela",
    "Partido Ancla",
    "Partido Brisa",
    "Partido Cauce",
    "Partido Faro",
    "Partido Marea",
)

_SAMPLE_SIZES: tuple[int, ...] = (800, 1000, 1200, 1500)
_MODE_PHRASES: tuple[str, ...] = ("por telefono", "de manera presencial", "por internet")
_SAMPLING_PHRASES: tuple[str, ...] = (
    "estratificado por comunidad y tamano de habitat",
    "por cuotas de sexo y edad",
    "aleatorio simple a partir de censo",
    "por afijacion proporcional",
)
_MONTHS: tuple[str, ...] = ("noviembre", "octubre", "junio", "septiembre", "mayo", "marzo")


@dataclass(frozen=True)
class Scenario:
    """The facts one template instance states, before any style or mutation touches it."""

    index: int
    sample_size: int
    margin: Decimal
    margin_theoretical: Decimal
    confidence: Decimal
    party_a: str
    party_b: str
    pct_a: Decimal
    pct_b: Decimal
    pollster: str
    address: str
    client: str
    mode_phrase: str
    sampling_phrase: str
    dates_phrase: str
    question_sentence: str

    @property
    def half_theoretical_margin(self) -> Decimal:
        return (self.margin_theoretical / 2).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class Gold:
    """The labels a case must receive, derived from its mutation, plus rule expectations."""

    items: Mapping[str, GoldLabel]
    expected_flags: frozenset[str] = frozenset()

    def with_absent(self, item_ids: tuple[str, ...]) -> Gold:
        items = dict(self.items)
        for item_id in item_ids:
            items[item_id] = "absent"
        return Gold(items=items, expected_flags=self.expected_flags)

    def with_flags(self, flags: tuple[str, ...]) -> Gold:
        merged = frozenset((*self.expected_flags, *flags))
        return Gold(items=dict(self.items), expected_flags=merged)


@dataclass(frozen=True)
class EvalCase:
    """One text to analyse: a base article or one of its mutations."""

    case_id: str
    base_id: str
    mutation: MutationId
    style: str
    split: str
    text: str
    gold: Gold
    base_mutations: tuple[MutationId, ...] = ()


@dataclass(frozen=True)
class Dataset:
    bases: tuple[EvalCase, ...]
    mutation_cases: tuple[EvalCase, ...]
    scenarios: Mapping[int, Scenario]

    @property
    def all_cases(self) -> tuple[EvalCase, ...]:
        """Bases interleaved with their mutations, so a small ``--limit`` covers both."""
        by_base: dict[str, list[EvalCase]] = {}
        for case in self.mutation_cases:
            by_base.setdefault(case.base_id, []).append(case)
        ordered: list[EvalCase] = []
        for base in self.bases:
            ordered.append(base)
            ordered.extend(by_base.get(base.base_id, []))
        return tuple(ordered)

    @property
    def bases_by_id(self) -> dict[str, EvalCase]:
        return {case.base_id: case for case in self.bases}

    def scenario_of(self, case: EvalCase) -> Scenario:
        return self.scenarios[_scenario_index(case)]


def _scenario_index(case: EvalCase) -> int:
    return int(case.base_id.removeprefix("base")) // STYLE_COUNT


def _fmt(number: Decimal) -> str:
    """Spanish formatting: decimal comma."""
    return f"{number:f}".replace(".", ",")


def _fmt_thousands(number: int) -> str:
    return f"{number:,}".replace(",", ".")


def _scenario(index: int, rng: Random) -> Scenario:
    pollster, address = FICTITIOUS_POLLSTERS[index % len(FICTITIOUS_POLLSTERS)]
    sample_size = _SAMPLE_SIZES[index % len(_SAMPLE_SIZES)]
    confidence = Decimal("95.5") if index == 7 else Decimal("95")
    margin_theoretical = theoretical_margin(sample_size, confidence=confidence)
    margin = margin_theoretical + Decimal("0.3")
    lead = margin - Decimal("0.2")
    day = 3 + (index * 2) % 20
    pct_a = Decimal(36 - (index % 4))
    return Scenario(
        index=index,
        sample_size=sample_size,
        margin=margin,
        margin_theoretical=margin_theoretical,
        confidence=confidence,
        party_a=FICTITIOUS_PARTIES[index % len(FICTITIOUS_PARTIES)],
        party_b=FICTITIOUS_PARTIES[(index + 5) % len(FICTITIOUS_PARTIES)],
        pct_a=pct_a,
        pct_b=pct_a - lead,
        pollster=pollster,
        address=address,
        client=FICTITIOUS_CLIENTS[index % len(FICTITIOUS_CLIENTS)],
        mode_phrase=_MODE_PHRASES[rng.randrange(len(_MODE_PHRASES))],
        sampling_phrase=_SAMPLING_PHRASES[rng.randrange(len(_SAMPLING_PHRASES))],
        dates_phrase=f"entre el {day} y el {day + 6} de {_MONTHS[index % len(_MONTHS)]}",
        question_sentence=(
            "La pregunta aplicada fue «¿A que formacion daria su voto si se celebraran "
            "elecciones manana?»"
        ),
    )


def _headline(scenario: Scenario, style: str) -> str:
    a, b = scenario.party_a, scenario.party_b
    if style == "agencia":
        return f"Sondeo ficticio: {a} adelanta a {b} en intencion de voto"
    if style == "diario_local":
        return f"{a} se mantiene por delante de {b} de acuerdo con la encuesta simulada"
    if style == "television":
        return f"Avance: la encuesta simulada situa a {a} por delante de {b}"
    return f"Hilo: la encuesta simulada da la delantera a {a} frente a {b}"


def _closing(style: str) -> str:
    if style == "agencia":
        return "La empresa subraya que todos los datos de esta nota son simulados."
    if style == "diario_local":
        return "El periodico recuerda que todo el contenido de la pieza es simulado."
    if style == "television":
        return "El informativo ha recordado que se trata de una simulacion con fines didacticos."
    return "Fin del hilo: todo inventado, no lo compartas como real."


_BLOCK_ORDER: tuple[str, ...] = (
    "marker",
    "headline",
    "entity",
    "client",
    "address",
    "results",
    "sample",
    "margin",
    "confidence",
    "universe",
    "sampling",
    "selection",
    "mode",
    "dates",
    "question",
    "nonresponse",
    "weighting",
    "external",
    "closing",
)


def _blocks(scenario: Scenario, style: str) -> list[tuple[str, str]]:
    """The ordered (block, sentence) skeleton of one base article.

    The fact sentences deliberately use wording the code layer can locate (the
    candidate cues), so the corpus measures systems on solvable cases; the paraphrase
    and deletion mutations then measure how much of that survives rewording.
    """
    sentences = {
        "marker": "SIMULACIÓN.",
        "headline": _headline(scenario, style),
        "entity": f"La encuesta fue elaborada por {scenario.pollster}.",
        "client": f"El estudio fue contratado por {scenario.client}.",
        "address": f"La sede de la empresa esta en {scenario.address}.",
        "results": (
            f"{scenario.party_a} obtendria un {_fmt(scenario.pct_a)} % de los votos y "
            f"{scenario.party_b} un {_fmt(scenario.pct_b)} %."
        ),
        "sample": f"El trabajo se baso en {_fmt_thousands(scenario.sample_size)} entrevistas.",
        "margin": f"El margen de error es de {_fmt(scenario.margin)} puntos.",
        "confidence": f"El nivel de confianza es del {_fmt(scenario.confidence)} %.",
        "universe": "El universo son mayores de 18 anos residentes en Espana.",
        "sampling": f"El muestreo fue {scenario.sampling_phrase}.",
        "selection": "Los participantes fueron captados por marcacion aleatoria.",
        "mode": f"La recogida de datos se hizo {scenario.mode_phrase}.",
        "dates": f"Los trabajos de campo se desarrollaron {scenario.dates_phrase}.",
        "question": scenario.question_sentence,
        "nonresponse": "La tasa de respuesta fue del 97 %.",
        "weighting": "Los resultados fueron ponderados por sexo, edad y nivel de estudios.",
        "external": "La ficha tecnica completa esta publicada en la web de la encuestadora.",
        "closing": _closing(style),
    }
    return [(name, sentences[name]) for name in _BLOCK_ORDER]


def _render(blocks: list[tuple[str, str]], style: str) -> str:
    separator = "\n" if style == "red_social" else " "
    return separator.join(sentence for _, sentence in blocks)


def base_gold() -> Gold:
    """A complete base states every checklist item: all present, no flag expected."""
    return Gold(items={item_id: "present" for item_id in BLOCK_FOR_ITEM})


#: The simple block rewrites take the old sentence and the scenario and return the new one.
Rewrite = Callable[[str, Scenario], str]


def _m10_margin(_sentence: str, scenario: Scenario) -> str:
    return f"El margen de error es de {_fmt(scenario.half_theoretical_margin)} puntos."


def _m11_headline(_sentence: str, scenario: Scenario) -> str:
    return (
        f"¡{scenario.party_a} ya gana las elecciones: "
        f"{_fmt(scenario.pct_a - scenario.pct_b)} puntos de ventaja sobre {scenario.party_b}!"
    )


def _m12_results(_sentence: str, scenario: Scenario) -> str:
    return (
        f"La proyeccion apunta a un {_fmt(scenario.pct_a)} % de los votos para "
        f"{scenario.party_a} frente al {_fmt(scenario.pct_b)} % de {scenario.party_b} "
        "el dia de las elecciones."
    )


def _m13_reader_vote(blocks: list[tuple[str, str]], scenario: Scenario) -> list[tuple[str, str]]:
    replacements = {
        "entity": f"La votacion abierta de lectores fue promovida por {scenario.client}.",
        "sample": (
            f"Participaron de forma voluntaria {_fmt_thousands(scenario.sample_size)} lectores."
        ),
    }
    return [(name, replacements.get(name, sentence)) for name, sentence in blocks]


def _m14_paraphrase(blocks: list[tuple[str, str]], _scenario: Scenario) -> list[tuple[str, str]]:
    text = _render(blocks, "agencia")
    for old, new in PARAPHRASES:
        text = text.replace(old, new)
    return [("paraphrase", text)]


#: M14: sentence-level rewording that keeps every statement. Nothing here may change what
#: the article asserts: the whole point is that the gold must not move.
PARAPHRASES: tuple[tuple[str, str], ...] = (
    ("fue elaborada por", "corre a cargo de"),
    ("La sede de la empresa esta en", "La empresa tiene su domicilio social en"),
    ("El margen de error es de", "El margen de error se situa en"),
    ("El nivel de confianza es del", "El nivel de confianza estadistico es del"),
    ("El universo son", "La poblacion objetivo son"),
    ("El muestreo fue", "El muestreo se hizo"),
    ("fueron captados por marcacion aleatoria", "se contacta a traves de marcacion aleatoria"),
    ("La recogida de datos se hizo", "La recogida de datos se realizo"),
    ("se desarrollaron", "se llevaron a cabo"),
    ("La pregunta aplicada fue", "El cuestionario preguntaba"),
    ("no respondio", "no contesto"),
    ("La tasa de respuesta fue del 97 %.", "Respondieron 97 de cada 100 contactados."),
    ("fueron ponderados", "se aplico ponderacion"),
    ("El trabajo se baso en", "La muestra fue de"),
    ("obtendria un", "conseguiria un"),
    ("de los votos", "de los sufragios"),
    ("esta publicada en", "esta disponible en"),
)


def _m15_link(blocks: list[tuple[str, str]], _scenario: Scenario) -> list[tuple[str, str]]:
    sheet_blocks = frozenset(
        {
            "sample",
            "margin",
            "confidence",
            "universe",
            "sampling",
            "selection",
            "mode",
            "dates",
            "question",
            "nonresponse",
            "weighting",
        }
    )
    return [
        (
            name,
            "Mas datos en la ficha tecnica publicada en la web de la encuestadora."
            if name == "external"
            else sentence,
        )
        for name, sentence in blocks
        if name not in sheet_blocks
    ]


@dataclass(frozen=True)
class MutationSpec:
    """What one mutation changes, plus the rule the change should make fire."""

    id: MutationId
    remove_blocks: tuple[str, ...] = ()
    rewrite_block: str = ""
    rewrite: Rewrite | None = None
    handler: Callable[[list[tuple[str, str]], Scenario], list[tuple[str, str]]] | None = None
    expected_flags: tuple[str, ...] = ()

    def apply(self, blocks: list[tuple[str, str]], scenario: Scenario) -> list[tuple[str, str]]:
        if self.handler is not None:
            return self.handler(list(blocks), scenario)
        result: list[tuple[str, str]] = []
        for name, sentence in blocks:
            if name in self.remove_blocks:
                continue
            if self.rewrite is not None and name == self.rewrite_block:
                sentence = self.rewrite(sentence, scenario)
            result.append((name, sentence))
        return result


MUTATIONS: Mapping[MutationId, MutationSpec] = {
    "M1": MutationSpec("M1", remove_blocks=("sample",)),
    "M2": MutationSpec("M2", remove_blocks=("margin",)),
    "M3": MutationSpec("M3", remove_blocks=("dates",)),
    "M4": MutationSpec("M4", remove_blocks=("entity",)),
    "M5": MutationSpec("M5", remove_blocks=("client",)),
    "M6": MutationSpec("M6", remove_blocks=("universe",)),
    "M7": MutationSpec("M7", remove_blocks=("sampling",)),
    "M8": MutationSpec("M8", remove_blocks=("question",)),
    "M9": MutationSpec("M9", remove_blocks=("nonresponse",)),
    "M10": MutationSpec("M10", rewrite_block="margin", rewrite=_m10_margin, expected_flags=("M4",)),
    "M11": MutationSpec(
        "M11", rewrite_block="headline", rewrite=_m11_headline, expected_flags=("M11",)
    ),
    "M12": MutationSpec(
        "M12", rewrite_block="results", rewrite=_m12_results, expected_flags=("M12",)
    ),
    "M13": MutationSpec("M13", handler=_m13_reader_vote, expected_flags=("M13",)),
    "M14": MutationSpec("M14", handler=_m14_paraphrase),
    "M15": MutationSpec("M15", handler=_m15_link),
}

#: Items whose gold turns absent for M15: the sheet became a link.
_M15_ABSENT_ITEMS: tuple[str, ...] = (
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

_DELETION_MUTATIONS: frozenset[str] = frozenset(MUTATION_IDS[:9])


def gold_for(mutation: MutationId, base_gold: Gold) -> Gold:
    """Derive the gold of a mutation from the gold of its base. Never hand-written."""
    if mutation == "base":
        return base_gold
    spec = MUTATIONS[mutation]
    gold = base_gold
    if mutation in _DELETION_MUTATIONS:
        removed = tuple(
            item_id for item_id, block in BLOCK_FOR_ITEM.items() if block in spec.remove_blocks
        )
        gold = gold.with_absent(removed)
    elif mutation == "M15":
        gold = gold.with_absent(_M15_ABSENT_ITEMS)
    if spec.expected_flags:
        gold = gold.with_flags(spec.expected_flags)
    return gold


def split_of_base(base: int | str) -> str:
    """60/40 dev/test, cut along base articles so mutations never cross the boundary."""
    index = int(base) if isinstance(base, int) else int(str(base).removeprefix("base"))
    return "dev" if index < int(BASE_COUNT * DEV_SHARE) else "test"


def blocks_of(case: EvalCase, dataset: Dataset) -> list[tuple[str, str]]:
    """Rebuild the block skeleton of any case: base blocks with the mutation applied."""
    scenario = dataset.scenario_of(case)
    blocks = _blocks(scenario, case.style)
    if case.mutation == "base":
        return blocks
    return MUTATIONS[case.mutation].apply(list(blocks), scenario)


def build_dataset() -> Dataset:
    """Build the whole corpus. Deterministic for the fixed seed; no model is involved."""
    scenarios: dict[int, Scenario] = {}
    bases: list[EvalCase] = []
    mutation_cases: list[EvalCase] = []

    for scenario_index in range(SCENARIO_COUNT):
        scenario = _scenario(scenario_index, Random(EVALUATION_SEED + scenario_index))
        scenarios[scenario_index] = scenario
        for style in STYLES:
            base_number = scenario_index * STYLE_COUNT + STYLES.index(style)
            base_id = f"base{base_number:02d}"
            split = split_of_base(base_number)
            blocks = _blocks(scenario, style)
            text = _render(blocks, style)
            gold = base_gold()
            bases.append(
                EvalCase(
                    case_id=base_id,
                    base_id=base_id,
                    mutation="base",
                    style=style,
                    split=split,
                    text=text,
                    gold=gold,
                )
            )

            # Round-robin rotation: every base receives six consecutive mutation ids out
            # of the cycle, so the 15 mutations spread evenly across the 40 bases.
            assigned = tuple(
                MUTATION_IDS[(base_number * MUTATIONS_PER_BASE + offset) % len(MUTATION_IDS)]
                for offset in range(MUTATIONS_PER_BASE)
            )
            for mutation in assigned:
                mutated_blocks = MUTATIONS[mutation].apply(list(blocks), scenario)
                mutated_text = (
                    mutated_blocks[0][1] if mutation == "M14" else _render(mutated_blocks, style)
                )
                mutation_cases.append(
                    EvalCase(
                        case_id=f"{base_id}-{mutation.lower()}",
                        base_id=base_id,
                        mutation=mutation,
                        style=style,
                        split=split,
                        text=mutated_text,
                        gold=gold_for(mutation, gold),
                        base_mutations=assigned,
                    )
                )

    return Dataset(bases=tuple(bases), mutation_cases=tuple(mutation_cases), scenarios=scenarios)
