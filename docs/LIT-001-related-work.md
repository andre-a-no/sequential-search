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

Ограничение проверки: из этого окружения сеть доступна только на уровне
TCP-коннекта к arxiv.org (HTTP не поднимается), поэтому выходы, воспроизведённые
по памяти, верифицировать не удалось. Требование: перед публикацией
README/paper прогнать список через нормальный поиск и снять все пометки.
Пока пометки стоят, файл годится как карта направлений, но не как citations.

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
* Online FDR: **Candès, Zrnic, Fan (2018), PNAS 115 — LOND** (первая широко используемая онлайн-процедура); **Zrnic, Ramdas, Tibshirani (2019?) — ADDIS** и **Angelopoulos, Zrnic, Wang, Ramdas — a unified view of online multiple testing**; **Livnat, Papadimitriou, Daskalakis (2015), IEEE Trans. IT 61** — адверсариальная онлайн-постановка. Точные годы/составы этих трёх позиций сверить перед публикацией библиографии — я их привожу по памяти.
* Ramdas, Zrnic, Funderburk, Tibshirani, Wainwright (2018), Ann. Statist. 46 — **SAFER / LORD-1**: online FDR на e-value/p-value потоке.
* **Zrnic & Ramdas (2024), Online multiple testing with adaptive stopping rules** (arXiv; точный выход сверить) — поток опытов, каждый со своим моментом остановки; буквально наш кейс «поток гипотез» + «разные стоимости». Это ближайшая к нам работа: она доказывает, что «останавливаюсь сам» и «решаю в потоке» совместимы, но графа/дерева там нет.
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

---

## 11. Как это связано с планом ADR-003

Порядок реализации не меняется, но обзор его обосновывает: `stats/error_budget.py`
идёт раньше интерпретаторов, потому что §3 показывает единственную настоящую
дыру; политики (`policy/`) опираются на §4 и не должны ничего доказывать — они
только выбирают узел; актюация из ADR-004/005 остаётся в `sequentialist-search`,
её якоря (§6–§7) нужны лишь для того, чтобы контракт `Node` не оказался слишком
узким (проверка: `cost` должен быть расстоянием между действиями, а не только
стоимостью съёма).
