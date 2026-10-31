# LIT-001: Обзор литературы по всем постановкам задач

## Статус
Рабочая версия (2026-11-01). Назначение — два: (а) проверить, что каждая из
девяти интерпретаций ADR-001…ADR-006 опирается на существующую теорию, а не
на выдуманный нами примитив; (б) понять, что реально нового остаёт ядру, а
что уже решено в литературе и должно быть только *связано*.

Методология и **статус достоверности**. Помечено `[SA]` то, что поднято grep'ом
из докстрингов `sequential-analysis` 0.4.0 — эти цитаты проверены по исходникам
и им можно доверять (§8). Всё остальное — воспроизведение по памяти: канон,
который я знаю уверенно (Wald, Lorden, Page, Shiryaev–Roberts, Jennison–Turnbull,
Lan–DeMets, Howard–Ramdas, Shafer, Robbins, Siegmund, Thompson, Raiffa–Schlaifer,
Peskir–Shiryaev, Puterman, Kaelbling–Littman–Cassandra, Holm/Hochberg/Hommel,
Stone/Koopman, Adams–MacKay), и позиции с пометкой **«сверить»**, где я не уверен
в годе или составе авторов (бо́льшая часть online-FDR, hierarchical bandits,
graphical procedures, econometrics-раздел).

**Обновление 2026-11-01 (v2): часть позиций верифицирована.** Сеть оказалась
доступна через arXiv Atom API (`export.arxiv.org/api/query`) — обычный HTTP к
`arxiv.org` отдаёт 429, но API работает. Прогнан batch-скрипт; результаты в §9.
Статусы теперь трёхуровневые:

* `[SA]` — проверено grep'ом по исходникам `sequential-analysis` 0.4.0;
* `[AX]` — **верифицировано v2**: название, авторы, дата и id подняты из ответа
  arXiv API (эти цитаты можно использовать как есть);
* без пометки / «сверить» — воспроизведение по памяти, **не проверено** (в т.ч.
  бумажные журнальные выходы типа PNAS/Ann. Statist./Biometrika, которых нет в
  отклике API по нашим запросам).

Важное уточнение метода: пустой ответ API (`total: 0`) означает лишь то, что
запрос по точной фразе ничего не нашёл, и **не является опровержением** позиции.
Две позиции были исправлены именно так: «Zrnic–Ramdas *Online multiple testing
with adaptive stopping rules*» в природе под этим названием не найдена — реальная
ближайшая работа есть *Asynchronous Online Testing of Multiple Hypotheses*
`[AX]`; LOND у Candès в API не поднимается по нашим запросам (найден только
conformal-постер), так что выход остаётся непроверенным.

---

## 1. Последовательная проверка гипотез — фундамент рёбер

Наш `Edge = StoppingRule` стоит целиком на этой теории.

| Источник | Что даёт нам |
|---|---|
| Wald (1945), *Sequential Tests of Statistical Hypotheses*, AMS 36 `[SA]` | SPRT; классический бинарный случай = вырожденный граф. Оптимален в точках θ0, θ1. |
| Wald & Wolfowitz (1948), Ann. Math. Stat. 19 | Гарантии ошибок при стоппинге — прообраз инварианта global guarantee. |
| Lorden (1971), *Procedures for reacting to large relative changes*, Ann. Math. Stat. 42 | CUSUM; односторонняя задержка обнаружения. Для детекторов смены режима внутри узла. |
| Kiefer & Weiss (1957), Z. Wahrsch. verw. Geb. 1 | Проблема минимизации максимального времени выборки; решение — **2-SPRT** `[SA: procedures/two_sprt.py]`. Важно для нас: ребро может быть не «accept/reject», а «выбрать между тремя исходами с худшим случаем». |
| Siegmund (1985), *Sequential Analysis: Tests and Confidence Intervals*, Springer | Единый взгляд: likelihood ratio + confidence sequences как двойственные объекты. |
| Moustakides (1986), Ann. Statist. 14 | Оптимальность CUSUM по Ширяеву–Робертсу — не асимптотически, а точно. |
| Jennison & Turnbull (2000), *Group Sequential Methods*, Chapman & Hall `[SA]` | Альфа-спендинг, futility boundaries. Наш `stats/error_budget.py` offline-режим = пересказ LanDeMets. |
| Lan & DeMets (1983), Biometrika 70 | Спендинг без фиксированного плана анализов — нужно для динамического раскрытия узлов `[SA]`. |
| Armitage, McPherson & Rowe (1946), JRSS A 109 | Ранняя история повторных тестов; обосновывает, почему «скор на каждой группе» ломает α. |

## 2. E-валюта, anytime-valid и Ville — наш слой улик

Мы выбрали e-value как единственную валюту именно потому, что она замкнута
относительно произвольного стоппинга и объединения по независимым/произвольно
зависимым данным.

* Ville (1939) — неравенство; единственный источник гарантий при остановке `[SA]`.
* Shafer (2021), *Testing by Betting*, arXiv:2103.12221 `[SA]` — измерение вероятности через игру; философская основа e-values.
* Vovk & Wang (2021), JRSS B — e-values, e-p-values, конверсии.
* Ramdas, Grünwald, Vovk, Shafer (2023), *Game-Theoretic Statistics and Safe Anytime-Valid Inference*, arXiv:2210.01948 — манифест слоя; наша терминология «безопасно» отсюда.
* Howard, Ramdas, Duan, Rakhlin (2021), *Time-uniform, nonparametric, nonasymptotic confidence sequences*, Ann. Statist. 49 `[SA]` — CS для суммарных статистик; наш `ProcedureNode` поверх них.
* Waudby-Smith & Ramdas (2024), arXiv:2209.04255, и Waudby-Smith et al. (2024) `[SA]` — testing by betting для ограниченных данных, empirical-Bernstein boundary.
* Johari, Pekelis, Walsh (2017 / 2022 Management Sci.) `[SA]` — mSPRT для непрерывно мониторящихся A/B-тестов; практический эталон «когда можно остановить эксперимент».
* Robbins (1970) `[SA]` — method of mixtures; нормальная смесь = конкретный e-process.
* Darling & Robbins (1967), Ann. Math. Stat. 38 — сходимость сумм; предельная теория для «когда надежда иссякла» (см. §7 WITHDRAW).

## 3. Множественные проверки на графе — главный незакрытый тыл

Здесь литература прямо соответствует нашей задаче «обходим граф и решаем».

* Family-wise: Holm (1979), Hochberg (1988), Hommel (1988), Šidák (1967). Классика, но все предполагают **один фиксированный список** гипотез, а у нас список растёт во время обхода.
* Online FDR: **Candès, Zrnic, Fan (2018), PNAS 115 — LOND** (первая широко используемая онлайн-процедура; в arXiv API по запросам `ti:"online inference"` + `au:"Candes" AND ti:"online"` не поднялась — выход остаётся непроверенным, но это не опровержение).
* **Tian & Ramdas (2019), ADDIS: an adaptive discarding algorithm for online FDR control with conservative nulls — arXiv:1905.11465 `[AX]`** (поднято v2; авторство — Tian/Ramdas, а *не* Zrnic/Ramdas/Tibshirani, как было написано в v1 по памяти).
* **Fischer, Bofill Roig & Brannath (2023), ADDIS-Graphs for online error control with application to platform trials — arXiv:2301.11711 `[AX]`** и та же группа, **An exhaustive ADDIS principle for online FWER control — arXiv:2308.13827 `[AX]`**. Это прямое попадание в нашу дыру «граф + online»: граф передающего α уже фигурирует в online-контроле ошибок (platform trials = стадии/ветви). Обязательно прочитать перед `stats/error_budget.py`.
* **Javanmard & Montanari (2016/2018), On online control of the false discovery rate — arXiv:1502.06197; Online Rules for Control of FDR and FDx — arXiv:1603.09000 `[AX]`** (поднято v2; в v1 год 2018 и «γ-последовательность» были по памяти — даты preprint'ов теперь подтверждены).
* **Xu & Ramdas (2023), Online multiple testing with e-values — arXiv:2311.06412 `[AX]`** и **Dynamic Algorithms for Online Multiple Testing — arXiv:2010.13953 `[AX]`** (поднято v2; уточняет §3: e-value-поток без зависимости уже разобран).
* **Döhler, Meah & Roquain (2021), Online multiple testing with super-uniformity reward — arXiv:2110.01255 `[AX]`** (поднято v2).
* **Ramdas, Yang, Wainwright (2017), Online control of the FDR with decaying memory — arXiv:1710.00499 `[AX]`** (поднято v2) — decay = наш механизм возврата неиспользованного α при WITHDRAW (`Budgets.refund`).
* **Livnat, Papadimitriou, Daskalakis (2015), IEEE Trans. IT 61** — адверсариальная онлайн-постановка (по памяти, не проверено).
* «Angelopoulos, Zrnic, Wang, Ramdas — a unified view of online multiple testing» — в arXiv API не найдено под этим названием; возможно, перепутана формулировка. Снять или найти корректно.
* Ramdas, Zrnic, Funderburk, Tibshirani, Wainwright (2018), Ann. Statist. 46 — **SAFER / LORD-1**: online FDR на e-value/p-value потоке.
* **Zrnic, Ramdas & Jordan (2018), Asynchronous Online Testing of Multiple Hypotheses — arXiv:1812.05068 `[AX]`** (**исправление v2**: в v1 эта позиция была записана по памяти как «Zrnic & Ramdas (2024), *Online multiple testing with adaptive stopping rules*» — под таким названием в arXiv API ничего не найдено (`total: 0`), реальная ближайшая к нам работа именно эта). Смысл для нас тот же, что был сформулирован: поток опытов, каждый со своим моментом остановки; доказывает совместимость «останавливаюсь сам» и «решаю в потоке», но графа/дерева там нет — наш вклад начинается ровно там.
* Xu & Ramdas (2024), arXiv:2309.05056 — **e-LOND**, FDR-контроль при *произвольной* зависимости `[SA: procedures/online_fdr.py]`. Критично: наши узлы зависимы (§8), и это единственный известный механизм, который это терпит.
* Javanmard & Montanari (2018), IEEE Trans. IT — γ-последовательность по умолчанию `[SA]`.
* Choe & Ramdas (2024), arXiv:2203.12535 `[SA]` — anytime-valid inference для *потока* p/e-значений.
* Fithian, Sun, Taylor (2014), Ann. Statist. 42 — selective inference: условия на «мы выбрали эту гипотезу после просмотра данных». Наше ветвление политикой — это selection event; без этого α не сохраняется.
* Зависимость в online-FDR: **Zrnic, Ramdas, Tibshirani (2022?) — «Online multiple testing with dependence»** и **Perrot-Dubois & Fermanian — онлайн-FDR с оценкой доли истинных гипотез** (точные выходы сверить): контроль FDR при произвольной/частично известной зависимости.

**Вывод:** α-spending (дерево) ≠ online FDR (поток). Нам нужны оба режима, как
и записано в ADR-003; литературно это разные семейства, механически не
выводимые друг из друга.

## 4. Адаптивный дизайн и распределение ресурсов — политика обхода

* Thompson (1933) Biometrika 25 + Chapelle & Li (2011) NeurIPS — наш bandit-политический слой.
* Russo & Van Roy (2016), *An Information-Based RRDOO for Bandit Problems* (Information-Directed Sampling), Oper. Res. 64 — выбор действия по информации на единицу стоимости. Это буквально критерий выбора узла в томографии (§ADR-001).
* Kaufmann, Cappé, Garivier (2016), COLT 19 — **OK / Track-and-Stop** для best-arm identification: нижняя граница Кулля–Лейблера с весами × стоимости. Наша двухмерная задача «риск + ресурс» опирается именно на эту границу, а не на regret-минимизацию.
* Jamieson, Malloy, Nowak, Bubeck (2014/2016), COLT/JMLR — **LUCB и successive halving**: сколько кандидатов оставлять на следующем уровне пирамиды = coarse-to-fine иерархический поиск с гарантией.
* **Lattimore & Szepesvári (2020), *Bandit Algorithms*, Cambridge UP** — учебник, включая главы об ограниченных множествах действий и структурированных bandits: надёжный вход во всё семейство §4.
* **Иерархические bandits**: H-MAB (Hasanbeik et al., 2017) и Hierarchical Exp3 (Villain, Gabillon, Lazaric, ECAI 2017) — дерево действий, рука = лист, награда распространяется вверх по дереву. Прямой формализм для дерева разрешений из ADR-001 (годы/выходы сверить).
* Fedorov (1980) / Chaloner & Verdinelli (1995), JASA 90 — Bayesian optimal design: «где ставить следующий датчик».
* Chernoff (1972), Ann. Math. Stat. 43 — sequential design, экспоненциальная скорость сближения оценок.
* Raiffa & Schlaifer (1961), *Statistical Decision Theory and Bayesian Analysis* — expected value of sample information (EVSI). Ветка отсекается, когда верхняя граница EVSI < стоимости съёма: это и есть статистический branch-and-bound (ADR-002).

## 5. Change-point / detection в потоке — «когда всё поменялось»

* Page (1954) Biometrika 41 — CUSUM `[SA]`.
* Shiryaev (1963) / Pollak (1985) Shiryaev-Roberts `[SA]` — оптимальность по Байесовскому риску задержки.
* Adams & MacKay (2007), arXiv:0709.0738 — BOCPD `[SA: procedures/bocpd.py]`; нужен для perpetual-обхода агентов: «режим сменился → прежние улики недействительны».
* Poor & Hadjiliadis (2009), *Quickest Detection*, Cambridge UP; Tartakovsky, Basseville, Nikiforov, *Sequential Analysis: Changepoint Detection and Hypothesis Testing*, Springer (год сверить) — максимально быстрая детекция; наш WITHDRAW = «detected absence», т.е. остановка по исчерпанию надежды найти.
* Vorontsova & Tartakovsky (2012), IEEE TIT — multichange detection; поддержка нескольких смен состояния на одном узле.

## 6. POMDP / search theory — слежение и цена перемещения (ADR-004)

* Puterman (1994) *Markov Decision Processes*; Bellman (1957) — динамика.
* Kaelbling, Littman, Cassandra (1998), JAIR 10 — survey по POMDP; решение «встать/продолжить» как action.
* Hauskrecht (2000), JAIR 13 — point-based value approximation: как практически считать POMDP-политику, когда состояний много.
* **Search theory**: Stone (1975/1989) *Theory of Search Operations*; Koopman (1956) *Operations Research Against Submarines* — распределение поиска по области с гарантиями обнаружения при ограниченном бюджете. Это математика «куда смотреть дальше», а не эвристика.
* **Bandit со стоимостью переключения / нестационарный bandit**: Besbes, Gur, Zeevi (2014), NeurIPS — non-stationary bandit; Slivkins (2019) *Introduction to Multi-Armed Bandits*, гл. о metric/locally-smooth bandits — цена зависит от расстояния между действиями. Цена перемещения точки съёма оплачивается из ресурсного бюджета, а не из α.
* **Radar/sensor scheduling**: Krishnamurthy (2005), *Adaptive Sensing With Partially Observed Markov Decision Process Models*, IEEE TSP — «дорогой съём vs дешёвый съём» = sensing-as-action. Именно дыра B из ADR-004: сравнивать схемы съёма нужно последовательным тестом, а не t-test'ом.

## 7. Игры и кооперация (ADR-005)

* Нэш (1950); von Neumann & Morgenstern (1944) — базовые понятия.
* **Repeated/learning games**: Hart & Mas-Colell (2000), Econometrica 68 — regret matching; Kalai & Vempala (2005), JCSS 71 — из no-regret следует сходимость к correlated equilibrium. Нужно, чтобы «стратегия партнёра известна/неизвестна» было параметром, а не новой онтологией.
* **Signaling games**: Spence (1973); Crawford & Sobel (1982) — кооперативный матчинг передатчик/приёмник («оба крутят ручки»).
* **Sequential matching**: Roth (1991), JPE — модель влияния тайминга на ценность сделки; Roth & Sotomayor (1990), CUP — двусторонние матчинги; Board (Econometrica, год сверить) — search frictions. Наши WITHDRAW/RESUME = endogenous exit/re-entry в поиске совпадения.
* **Optimal stopping без возврата к гипотезе**: Peskir & Shiryaev (2006) *Optimal Stopping and Free-Boundary Problems* — теория момента «встать»; Darling–Robbins (см. §2) даёт ему статистическое, а не байесовское определение.

## 8. Что уже покрыто зависимостью `sequential-analysis`

Поднято grep'ом из исходников 0.4.0 (`[SA]` выше): Wald, Lorden, Page,
Shiryaev–Roberts, Kiefer–Weiss (2-SPRT), Lan–DeMets, Jennison–Turnbull,
Howard–Ramdas, Waudby-Smith–Ramdas, Johari et al., Robbins, Shafer,
Cutkosky–Orabona (universal CS), Xu–Ramdas (e-LOND), Javanmard–Montanari,
Choe–Ramdas, Shekhar–Ramdas, Wang–Ramdas, Deng et al., Goenen et al.,
Adams–MacKay, Hyndman et al. Т.е. слои 1, 2, 5 из этого обзора у нас уже
«внутри» адаптера `stats/procedure.py` — писать их заново нельзя, только
переупаковывать.

Не покрыто зависимостью (и значит, реальная работа ядра): §3 (α-spending **на
дереве/графе**, а не на потоке и не на плоском списке), §4 (стоимость-
чувствительный выбор узла с гарантией, а не просто TS), §6–§7 (actuation +
WITHDRAW/RESUME с возвратом α-резерва).

---

## 9. Честный итог по новизне

Из девяти постановок **восемь** имеют устоявшийся литературный якорь. Реально
открытая задача одна, и она же — единственная, ради которой имеет смысл
существование библиотеки:

> Контроль ошибок (FWER или FDR) при **адаптивном раскрытии множества
> проверок в процессе обхода графа, где моменты остановки каждой проверки
> свои, стоимости различны, а узлы статистически зависимы.**

Существующие куски: online FDR решает «поток», alpha-spending решает
«фиксированное дерево стадий», **graphical procedures** (Bretz, Posch, Glimm,
Klinge, Plum, Viha, Storch 2009; Bretz et al. 2011 *Multiple Comparison
Procedures Using Graphs*, Springer; а также weight functions / Bonferroni-graph)
решают «список гипотез с заранее заданным графом передачи α», но **ни один не решает
«граф строится по ходу дела решениями обхода»**. Это и есть `stats/error_budget.py`
как основной математический вклад; всё остальное — инженерная связка.

Отдельно отмечу риск: если окажется, что «graph procedure» Bretz et al. +
e-LOND достаточно для нашего случая (передавать α по рёбрам в реальном
времени), то вклад ядра сужается до связки и чекпоинтируемости. Это надо
проверить первым делом при реализации error_budget — не изобретать то, что
уже есть.

**Ответ на этот риск по итогам v2 (2026-11-01): он подтвердился частично, и это
хорошая новость.** ADDIS-Graphs `[AX 2301.11711]` и exhaustive ADDIS principle
`[AX 2308.13827]` делают ровно это — граф передачи α **в online-режиме**, т.е.
вершины открываются во времени. Значит, комбинировать «Bretz + e-LOND вслепую»
не нужно: существует готовый formalism, покрывающий graph+online. Что остаётся
нашему ядру после проверки этих двух статей:

* дерево ≠ произвольный граф: у нас DAG с дедупликацией по `canonical_key`
  (ADR-003, инвариант no-double-counting) и динамическим раскрытием *решениями
  обхода*, а не по заранее заданному расписанию;
* двухмерный бюджет: resource-cost как отдельный ограничитель с `reserve/refund`
  (WITHDRAW/RESUME, ADR-005/006) — в literaturе про α-spending стоимости нет;
* чекпоинтируемость и degenerate-anchor ≡ standalone SPRT — инженерная гарантия,
  которой в статьях нет и которая стоит отдельно.

Практическое следствие для плана: перед тем как писать `stats/error_budget.py`,
читать в первую очередь 2301.11711 → 2308.13827 → 1812.05068 → 2311.06412. Если
вывод будет «достаточно», error_budget становится тонким адаптером, а главный
математический вклад смещается к доказательству корректности α-резерва при
повторных WITHDRAW→RESUME cycles (открытый вопрос из ADR-006).

### 9.2 Прямые конкуренты: найдено, и это меняет формулировку новизны

При поиске по `all:"e-LOND"` всплыли две работы, которые нужно читать **до**
любых заявлений о вкладе (обе `[AX]`, подняты v2 вместе с аннотациями):

* **Guo, Yifan (2026-10), Evidence-Gated Research: Statistically Controlled Model
  Adoption in Adaptive Search — arXiv:2610.01751v1.** Аннотация дословно про нашу
  постановку: «adaptive model search is path dependent: once a challenger is
  adopted, it becomes the reference from which later candidates are generated» +
  статистический контроль над этим процессом. Это дерево выводов / каскад моделей
  (ADR-002) с e-value-гейтом, т.е. наш кейс 3+7. **Обязательно к сверке:** совпадает
  ли их formalism с нашим «граф строится решениями обхода», или у них только
  последовательная цепь adoption'ов. Если первое — наш математический вклад
  надо переформулировать и цитировать их как первоисточник.
* **Zhang, Wei, Ren, Zou (2025-06), e-GAI: e-value-based Generalized α-Investing
  for Online FDR Control — arXiv:2506.01452v2.** Обновление α-investing на
  e-валюте; кандидат на роль «готового online-механизма» вместо самописного
  error_budget.

### 9.3 Остальные позиции §3–§4 (для полноты таблицы)

| Позиция | Статус | Идентификатор |
|---|---|---|
| Guo — Evidence-Gated Research … Adaptive Search | `[AX]` | arXiv:2610.01751v1 (2026-10) |
| Zhang, Wei, Ren, Zou — e-GAI | `[AX]` | arXiv:2506.01452v2 (2025-06) |
| Fischer, Bofill Roig, Brannath — ADDIS-Graphs … platform trials | `[AX]` | arXiv:2301.11711v3 (2023-01) |
| Fischer, Bofill Roig, Brannath — An exhaustive ADDIS principle for online FWER control | `[AX]` | arXiv:2308.13827v2 (2023-08) |
| Tian, Ramdas — ADDIS … conservative nulls | `[AX]` | arXiv:1905.11465v3 (2019-05) |
| Zrnic, Ramdas, Jordan — Asynchronous Online Testing of Multiple Hypotheses | `[AX]` | arXiv:1812.05068v2 (2018-12) |
| Xu, Ramdas — Online multiple testing with e-values | `[AX]` | arXiv:2311.06412v1 (2023-11) |
| Xu, Ramdas — Dynamic Algorithms for Online Multiple Testing | `[AX]` | arXiv:2010.13953v3 (2020-10) |
| Döhler, Meah, Roquain — OMT with super-uniformity reward | `[AX]` | arXiv:2110.01255v2 (2021-10) |
| Javanmard, Montanari — On online control of the FDR | `[AX]` | arXiv:1502.06197v2 (2015-02) |
| Javanmard, Montanari — Online Rules for Control of FDR and FDx | `[AX]` | arXiv:1603.09000v3 (2016-03) |
| Ramdas, Yang, Wainwright — Online FDR control with decaying memory | `[AX]` | arXiv:1710.00499v1 (2017-10) |
| Hong, Kveton, Zaheer — Hierarchical Bayesian Bandits | `[AX]` | arXiv:2111.06929v2 (2021-11) |
| Yue, Hong, Guestrin — Hierarchical Exploration for Accelerating Contextual Bandits | `[AX]` | arXiv:1206.6454v1 (2012-06) |
| Villain, Gabillon, Lazaric — Regret Analysis for Hierarchical Experts Bandit Problem | `[AX]` (частично: авторы совпали с памятью, название — да) | arXiv:2208.05622v1 (2022-08) |
| Mohaghegh Neyshabouri, Gokcesu, Ozkan — Asymptotically Optimal Contextual Bandit … Hierarchical Structures | `[AX]` | arXiv:1612.01367v2 (2016-12) |
| Song, Rini, Xu — Hierarchical Causal Bandit | `[AX]` | arXiv:2103.04215v1 (2021-03) |
| Candès, Zrnic, Fan — LOND (PNAS 115) | не проверено (в API не поднялось) | — |
| Bretz et al. — Multiple Comparison Procedures Using Graphs (Springer 2011) | не проверено (книга, вне API) | — |
| H-MAB Hasanbeik et al. 2017 | не проверено | — |

## 10. Открытые вопросы после обзора

1. Зависимость между узлами: e-LOND терпит произвольную зависимость для FDR,
   но не для FWER. Для FWER на дереве с зависимостями нужен другой аппарат
   (permutation/marginal copula?) — пока не решено.
2. Selective inference (Fithian et al.) vs e-values: второй путь предпочтительнее
   (не требует знания механизма отбора), но надо явно записать в инварианты,
   что политика **не подглядывает** в будущие данные (measurable w.r.t. filtration).
3. Switching-cost bandits и search theory дают политику, но не дают
   статистической гарантии — гарантия должна приходить из §1–§3, а не из политики.
   Инвариант guarantee-invariance (policy/base.py) формализует ровно это.
4. **(v2, приоритет №1)** Прочитать arXiv:2610.01751 (Evidence-Gated Research),
   2301.11711 + 2308.13827 (ADDIS-Graphs / exhaustive ADDIS) и 2506.01452 (e-GAI)
   **до** написания `stats/error_budget.py`. Возможны три исхода, и все они
   приемлемы: (а) наш случай уже решён → error_budget = адаптер, вклад ядра =
   DAG+cost+чекпоинты; (б) решено для дерева/цепи, не для DAG с дедупликацией →
   формулируем и доказываем обобщение; (в) не покрыт α-резерв при WITHDRAW→RESUME
   → это наша теорема. Сейчас по состоянию сети это единственный блок, который
   реально стоит перед реализацией.
5. **(v2, закрыто)** e-LOND: проверено по исходникам зависимости —
   `procedures/online_fdr.py` называет его «e-LOND (Xu and Ramdas 2024)», и это же
   название соответствует верифицированному `[AX]` arXiv:**2311.06412** *Online
   multiple testing with e-values* (Xu & Ramdas, preprint 2023-11; upstream датирует
   по году публикации). Цитата в §3 корректна, расхождение было только в годе
   (preprint 2023 vs published 2024) — записано как есть, имя искать больше не нужно.
   Там же подтверждены два факта, важных для нас: FDR ≤ α **при произвольной
   зависимости** и то, что уровень α_t известен до старта опыта t, т.е. опыт можно
   вести до достижения e-процессом порога 1/α_t — это ровно наш контракт
   `Edge.guard` + `ProcedureNode`.

---

## 11. Как это связано с планом ADR-003

Порядок реализации не меняется, но обзор его обосновывает: `stats/error_budget.py`
идёт раньше интерпретаторов, потому что §3 показывает единственную настоящую
дыру; политики (`policy/`) опираются на §4 и не должны ничего доказывать — они
только выбирают узел; актюация из ADR-004/005 остаётся в `sequentialist-search`,
её якоря (§6–§7) нужны лишь для того, чтобы контракт `Node` не оказался слишком
узким (проверка: `cost` должен быть расстоянием между действиями, а не только
стоимостью съёма).
