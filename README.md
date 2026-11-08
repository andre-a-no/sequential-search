# sequential-search

Математическое ядро **последовательного принятия статистических решений при
обходе графа**. Наследует постановку задачи
[`sequential-analysis`](https://pypi.org/project/sequential-analysis/), но
переносит её с плоского потока наблюдений на граф: каждый обход — это
поток экспериментов, а каждое ребро — статистическое решение.

Классический бинарный тест (SPRT и т.п.) — вырожденный случай графа
`root → leaf` с одним ребром.

## Conceptual framework: the Sequentialist ecosystem

The ecosystem studies sequential decisions: observations arrive, evidence
changes, and a policy chooses whether to continue, act, wait or stop. It separates
three questions within the mathematical and cybernetic methods layer:

| Library | Central question | Responsibility |
|---|---|---|
| [sequential-analysis](https://github.com/andre-a-no/sequential-analysis) | What can we infer from the observations available so far? | Statistical tests, estimation, filtering, prediction and procedure-specific uncertainty guarantees. |
| [sequential-search](https://github.com/andre-a-no/sequential-search) | Which step should we explore next to reach an answer or a goal? | Search and reasoning over alternatives, experiments and rules, with explicit evidence, provenance and resource costs. |
| [sequential-games](https://github.com/andre-a-no/sequential-games) | How do participants pursue their own goals while their actions change a shared environment? | Interaction models for cooperation, competition and partially aligned interests, including asynchronous actions, local information and deliberate waiting. |

These are complementary responsibilities. A participant's policy can use search
to plan and statistical analysis to interpret observations; other participants
continue to act according to their own objectives. This describes how the
methods can be composed. Each package's implementation status is stated
separately below.

The naming convention expresses a further separation into three layers:

| Layer | Packages | Responsibility |
|---|---|---|
| Mathematical and cybernetic methods | `sequential-*`: analysis, search, games | Models, algorithms, explicit state and the assumptions under which a result holds. |
| Reusable engineering platform | `sequentialist-*`, including [core](https://github.com/andre-a-no/sequentialist-core) and [visuals](https://github.com/andre-a-no/sequentialist-visuals) | Durable application execution, storage, recovery, audit and presentation, according to each package's implemented scope. |
| Domain applications | `sequentialist-*`, including [ab](https://github.com/andre-a-no/sequentialist-ab), [quality](https://github.com/andre-a-no/sequentialist-quality), [monitor](https://github.com/andre-a-no/sequentialist-monitor), [clinical](https://github.com/andre-a-no/sequentialist-clinical) and [agentic](https://github.com/andre-a-no/sequentialist-agentic) | Subject-specific goals, workflows, adapters and user-facing decisions built from the methods and engineering components they need. |

Both the engineering platform and applications use the `sequentialist-*`
prefix. The platform is an open family of reusable packages; `core` currently
provides durable tasks built around `sequential-analysis` runs. This organization
does not imply that every combination already has an integration.

Across the ecosystem, state, information available to a decision, randomness,
costs and stopping reasons should be explicit. Evidence, resource expenditure
and real-world effects have separate meanings. Statistical validity, derivability
under supplied rules, properties of an interaction model and reliable execution
each require their own justification; a guarantee in one layer does not
automatically establish a guarantee in another.

### Repository status

This `main` branch contains experiment/edge/graph contracts and the statistical
procedure adapter. Graph checkpoint serialization and finite rule-based reasoning
are developed in
[`feat/checkpoint-reasoning-and-discovery`](https://github.com/andre-a-no/sequential-search/tree/feat/checkpoint-reasoning-and-discovery).
General experiment traversal and whole-graph error control remain planned.

## Онтология (см. `docs/ADR-001-graph-nodes-as-experiments.md`)

| Сущность | Что это | Чем НЕ является |
|---|---|---|
| **Node** | эксперимент: `step() -> Observation`, `state() -> EvidenceState`, `cost` | данные, гипотеза, скор |
| **Edge** | stopping rule: накопленные улики → решение `accept / reject / pending` | булев предикат (это лишь вырожденный случай) |
| **Traversal** | политика обхода + глобальный бюджет ошибок (α-риск и ресурс) | цикл `for node in graph` |

## Design scenarios discussed in the ADRs

These are architectural targets and historical discussions. Their inclusion here
does not establish an implemented API or a statistical guarantee.

1. Каскад фильтров (pipeline, group-sequential).
2. Адаптивное дерево условий (adaptive sampling).
3. Поток гипотез с online-FDR (LORD/LTSI, graph-based FDR).
4. Карта состояний HMM / change-point (CUSUM, BOCPD как траектории обхода).
5. **Иерархическое углубление coarse-to-fine**: томография в глубь
   (усреднил группу слайсов → SPRT-решение спускаться ли к тонким срезам),
   пирамиды изображений, любой поиск по дереву разрешения с
   **разной стоимостью наблюдения на уровнях**.
6. **Статистические политики агентов**: вместо эвристик «N шагов и скор» —
   anytime-valid критерий на каждом продолжении действия
   (perpetual traversal).
7. **Дерево выводов (statistical branch-and-bound)**: решение задачи от «дано»
   к ответу; узел — промежуточное состояние, ребро — «продолжать ли ветку».
   «Я делаю слишком сложно, надо было делать что-то другое» = CUSUM-детектор
   смены режима приростов прогресса + нарушение inequality стоимости ожидания
   до успеха относительно сиблингов. См. `docs/ADR-002-traversal-as-conjecture-lifecycle.md`.
8. **Tracking a moving object**: the object moves through its own graph while
   the observer chooses where to observe and pays movement costs. Tracking an
   evolving environment is a search design scenario. Participants with their own
   objectives and coupled actions belong to `sequential-games`; search can be
   used within a participant's policy. The earlier exclusion of a games package
   in `docs/ADR-004-environment-as-adversary.md` records a historical scope
   decision. This tracking scenario remains unimplemented: dependencies through
   the environment, comparison of observation locations and perpetual traversal
   with switching costs are still open work.
9. **Кооперативный поиск общего состояния (sequential matching)**: передатчик и
   приёмник независимо крутят ручки в поисках лучшего канала, полезность общая.
   Кооперативность не требует game theory, но требует **общего e-бюджета** для
   обеих сторон. «Учитывая обстоятельства, нужно встать» — исход `WITHDRAW`,
   отличный от `REJECT`: остановка по исчерпанию ценности продолжения, а не по
   опровержению гипотезы, с возвратом неизрасходованного α. ⚠️ Не выполнимо до
   закрытия дыры B. См. `docs/ADR-005-cooperative-matching-and-withdrawal.md`.
10. **Возобновление после «встать»**: у WITHDRAW есть обратный переход `RESUME`,
    иначе политика будет бояться закрывать ветку и недоиспользует бюджет.
    Требование к контракту: RESUME обязан восстанавливать накопленные улики, а
    не начинать поиск заново (иначе α-резерв тратится дважды). Известная
    стратегия партнёра vs неизвестная — разные постановки: первая даёт точную
    гарантию (conditional power), вторая только anytime-valid верхнюю; обе
    выражаются параметрами узла, adversarial-режим вынесен **за скоуп ядра**.
    См. `docs/ADR-006-resumable-search-and-known-partner.md`.

Application workflows belong in `sequentialist-*` packages. The reserved
[`sequentialist-search`](https://github.com/andre-a-no/sequentialist-search) name
is one proposed engineering wrapper, not the mathematical search library;
[`sequentialist-agentic`](https://github.com/andre-a-no/sequentialist-agentic)
is an existing application repository.

## Target package structure

This tree includes planned modules. The status section below distinguishes the
implemented contracts from the remaining algorithms.

```
src/sequential_search/
├── core/            # онтология графа
│   ├── node.py      # Node protocol, Observation, EvidenceState, canonical_key
│   ├── edge.py      # Edge, StoppingDecision
│   ├── graph.py     # SearchGraph: DAG с merging узлов, динамическое раскрытие
│   └── traversal.py # Traversal: finite / perpetual / resumable, чекпоинты
├── stats/           # математика (тонкие обёртки над sequential-analysis)
│   ├── procedure.py # Procedure adapter (SPRT, mSPRT, group-sequential…)
│   ├── evidence.py  # e-values, likelihood ratios, накопление улик
│   ├── error_budget.py  # offline/online контроль FWER/FDR, alpha-spending
│   └── stopping.py  # StoppingRule, anytime-valid границы
├── policy/          # выбор следующего узла
│   ├── base.py
│   ├── exhaustive.py    # полный DFS/BFS — базовый рабочий случай
│   ├── bandit.py        # распределение бюджета (info per cost, VOI lower bound)
│   └── budget.py        # resource-aware: стоимость узлов ∈ бюджет
├── interpreters/    # эталонные mappings «граф ↔ задача» (минимальные)
│   ├── hypotheses.py
│   ├── sampling.py
│   ├── pipeline.py
│   ├── hierarchy.py     # томография/пирамиды: coarse-to-fine
│   ├── inference.py     # дерево выводов: proof search / стат. branch-and-bound
│   ├── tracking.py      # кейс 8: слежение; ✗ не выполним на текущем ядре (ADR-004)
│   └── matching.py      # кейс 9: кооперативный поиск канала; ✗ до закрытия дыр B/D (ADR-005)
└── io/              # сериализация, чекпоинты (формат совместим с sequential-analysis)
```

## Target kernel invariants

These are design requirements. The implemented contracts and single-edge tests
do not establish whole-graph statistical error control.

1. **Global guarantee**: family-wise error ≤ α по всему обходу, даже если
   политика адаптирует порядок проверок (e-value calibration на рёбрах).
2. **Degenerate anchor**: одно-реберный граф ≡ standalone SPRT из
   `sequential-analysis` (тест фиксируется до реализации обхода).
3. **Checkpointability**: состояние всего обхода сериализуемо и
   воспроизводимо (RNG-семантика наследуется).
4. **Cost-awareness**: `Node.cost` участвует в политике; гарантию α не
   нарушает ни одна стратегия выбора следующего узла.
5. **No double counting**: граф — DAG; повторный вход в канонически тот же
   узел не создаёт нового эксперимента и не удваивает накопленные улики
   (иначе множественность проверок скрывается и инвариант 1 ломается).
6. **Separation of evidence and cost** (E4): правило остановки не способно
   породить `WITHDRAW`/`RESUME` — они выводятся из стоимости продолжения на
   уровне traversal, а не из силы улик. Иначе «уставший тест» неотличим от
   «опровергнутого».
7. **Budget conservativity** (B1/B2): α резервируется под ребро и списывается
   только при ACCEPT/REJECT; возврат не превышает резерв. Без этого `WITHDRAW`
   печатал бы α и инвариант 1 терял смысл.

## Статус

Проект на стадии проектирования. Принятые решения документируются как ADR
в `docs/`.

**Реализовано**: слой 1 (контракты `core/node.py`, `core/edge.py`, `core/graph.py`,
`policy/base.py`) + адаптер `stats/procedure.py` + degenerate anchor (20 tests,
зелёные; 8 из них работают без установленного upstream — extra `[core]` автономен).

**Спецификация degenerate anchor** зафиксирована кодом
`tests/test_degenerate_anchor.py`; отдельный markdown-файл под неё не создавался
(в более ранней сводке он был заявлен по ошибке) — считайте источником истины тест.

**Порядок следующих шагов** (изменён ADR-006):
`io/checkpoint.py` → `core/traversal.py` → `stats/error_budget.py` →
`interpreters/hierarchy.py`. Чекпоинт идёт раньше обхода потому, что `RESUME`
требует сохранения накопленных улик, а без него WITHDRAW невозможно сделать
обратимым, не потеряв гарантию.

**Блокирующий открытый вопрос**: формат envelope чекпоинта и его совместимость с
`sequential-analysis` (`checkpoint()/restore()`). До его решения traversal не
пишется.

## Установка (когда будет опубликовано)

```bash
pip install sequential-search-core        # только контракты, без upstream
pip install sequential-search-core[full]  # + адаптеры процедур поверх sequential-analysis
```

Имя `sequential-search` на PyPI может быть занято — резервуем `-core`
(решение ADR-003, пункт 3), проверяется перед первым релизом.

## Лицензия
AGPL-3.0 (совместимо с двойным лицензированием upstream).
