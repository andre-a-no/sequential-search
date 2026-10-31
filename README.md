# sequential-search

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

## Интерпретации, которые покрывает ядро

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

Прикладные интерпретации живут **не здесь**, а в слое
`sequentialist-search` (отдельный репозиторий-обвязка).

## Структура пакета

```
src/sequential_search/
├── core/            # онтология графа
│   ├── node.py      # Node protocol, Observation, EvidenceState
│   ├── edge.py      # Edge, StoppingDecision
│   ├── graph.py     # SearchGraph (tree/DAG), динамическое раскрытие узлов
│   └── traversal.py # Traversal: finite и perpetual режимы, чекпоинты
├── stats/           # математика (тонкие обёртки над sequential-analysis)
│   ├── procedure.py # Procedure adapter (SPRT, mSPRT, group-sequential…)
│   ├── evidence.py  # e-values, likelihood ratios, накопление улик
│   ├── error_budget.py  # offline/online контроль FWER/FDR, alpha-spending
│   └── stopping.py  # StoppingRule, anytime-valid границы
├── policy/          # выбор следующего узла
│   ├── base.py
│   ├── exhaustive.py    # полный DFS/BFS — базовый рабочий случай
│   ├── bandit.py        # распределение бюджета (info per cost)
│   └── budget.py        # resource-aware: стоимость узлов ∈ бюджет
├── interpreters/    # эталонные mappings «граф ↔ задача» (минимальные)
│   ├── hypotheses.py
│   ├── sampling.py
│   ├── pipeline.py
│   └── hierarchy.py     # томография/пирамиды: coarse-to-fine
└── io/              # сериализация, чекпоинты (формат совместим с sequential-analysis)
```

## Инварианты ядра

1. **Global guarantee**: family-wise error ≤ α по всему обходу, даже если
   политика адаптирует порядок проверок (e-value calibration на рёбрах).
2. **Degenerate anchor**: одно-реберный граф ≡ standalone SPRT из
   `sequential-analysis` (тест фиксируется до реализации обхода).
3. **Checkpointability**: состояние всего обхода сериализуемо и
   воспроизводимо (RNG-семантика наследуется).
4. **Cost-awareness**: `Node.cost` участвует в политике; гарантию α не
   нарушает ни одна стратегия выбора следующего узла.

## Статус

Проект на стадии проектирования. Принятые решения документируются как ADR
в `docs/`.

## Установка (когда будет опубликовано)

```bash
pip install sequential-search
```

Зависимость: `sequential-analysis` (ядро процедур и чекпоинтинга).

## Лицензия
AGPL-3.0 (совместимо с двойным лицензированием upstream).
