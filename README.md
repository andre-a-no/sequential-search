# sequential-search

Start with the [plain-language overview](docs/overview.md) for use cases,
current versus planned capabilities and guarantees. [llms.txt](llms.txt) is a
curated source index; [AGENTS.md](AGENTS.md) contains development guidance.

Математическое ядро **последовательного принятия статистических решений при
обходе графа**. Наследует постановку задачи
[`sequential-analysis`](https://pypi.org/project/sequential-analysis/), но
переносит её с плоского потока наблюдений на граф: каждый обход — это
поток экспериментов, а каждое ребро — статистическое решение.

Классический бинарный тест (SPRT и т.п.) — вырожденный случай графа
`root → leaf` с одним ребром.

## Онтология (см. `docs/ADR-001-graph-nodes-as-experiments.md`)

| Сущность | Что это | Чем НЕ является |
|---|---|---|
| **Node** | эксперимент: `step() -> Observation`, `state() -> EvidenceState`, `cost` | данные, гипотеза, скор |
| **Edge** | stopping rule: накопленные улики → решение `accept / reject / pending` | булев предикат (это лишь вырожденный случай) |
| **Traversal** | политика обхода + глобальный бюджет ошибок (α-риск и ресурс) | цикл `for node in graph` |

## Design scenarios discussed in the ADRs

The following scenarios are architectural targets and historical discussions,
not a list of implemented capabilities. In particular, earlier ADRs excluded a
separate games package; the current ecosystem now distinguishes
[sequential-games](https://github.com/andre-a-no/sequential-games) for mathematical
interaction models with independent objectives and coupled asynchronous actions.
The earlier exclusion below records that earlier scope decision.

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
8. **Слежение за перемещающимся объектом** (объект сам путешествует по своему
   графу; мы решаем, смещаться ли нам, и платим за перемещение). Оппонент с
   собственной стратегией — вырожденный случай адаптивной среды, отдельная
   библиотека для игр **не создаётся**. ⚠️ Этот кейс пока **не выполним на
   текущем ядре**: вскрывает три дыры (зависимость наблюдений через среду,
   сравнение двух точек съёма, perpetual + switching cost). См.
   `docs/ADR-004-environment-as-adversary.md`.
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

Application interpretations belong in `sequentialist-*` packages. Earlier ADRs
used `sequentialist-search` as a proposed wrapper name; that does not establish
that such a package or repository is available. `sequentialist-agentic` is an
existing application integration; domain packages can use search directly.

## Target package structure

This tree includes planned modules. Inspect the actual `src/` files and the
status section below for implemented APIs; a filename here is not an import
availability claim.

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

These are design requirements. Local contracts and tests establish only their
documented scope; whole-graph error control remains unimplemented.

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
`policy/base.py`), адаптер `stats/procedure.py`, degenerate anchor и версионируемый
формат контрольной точки `io/checkpoint.py`. Он сохраняет граф, улики, frontier,
состояния рёбер, резервы бюджетов и состояние политики/RNG. `ProcedureNode`
восстанавливает свой upstream Run и последний результат без сброса улик.
Контракты и сериализация не требуют установленного upstream; адаптер требует
`[full]`. Контракт формата и пример кодеков —
[ADR-007](docs/ADR-007-checkpoint-envelope.md).

**Finite reasoning reference (P0):** `sequential_search.reasoning` adds pure
forward, backward and checked bidirectional search over a declared finite set of
positive implication rules. It supports AND premises, OR alternatives, checked
proof provenance and explicit missing-premise results. Search limits remain
distinct from exhaustion; search-work cost remains distinct from proof cost.
This is an additive mathematical reference, not a replacement for experiment
nodes or a general theorem prover. Contract, example and limits:
[ADR-008](docs/ADR-008-reasoning-search.md).

**Спецификация degenerate anchor** зафиксирована кодом
`tests/test_degenerate_anchor.py`; отдельный markdown-файл под неё не создавался
(в более ранней сводке он был заявлен по ошибке) — считайте источником истины тест.

**Порядок следующих шагов** (изменён ADR-006):
`core/traversal.py` → `stats/error_budget.py` → `interpreters/hierarchy.py`.
Формат envelope и вложение upstream-чекпоинта определены в ADR-007. Сериализация
сохраняет WITHDRAW и накопленные улики; переход RESUME предстоит реализовать
в обходе. Корректность повторного возврата и резервирования α пока не доказана:
сохранение чисел бюджета само по себе не устанавливает global guarantee.

## Установка (когда будет опубликовано)

```bash
pip install sequential-search-core        # только контракты, без upstream
pip install sequential-search-core[full]  # + адаптеры процедур поверх sequential-analysis
```

Имя `sequential-search` на PyPI может быть занято — резервуем `-core`
(решение ADR-003, пункт 3), проверяется перед первым релизом.

## Лицензия
AGPL-3.0 (совместимо с двойным лицензированием upstream).
