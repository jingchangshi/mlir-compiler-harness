# Goal: Phase 19 — Python Pipeline Semantic Provenance

你负责继续维护 `mlir-compiler-harness`。

当前仓库已经完成：

* Phase 0-11 Compiler Knowledge Graph
* Phase 12 Intent / Constraint Extraction
* Phase 13 Compiler Review Intelligence
* Phase 14 Finding Lifecycle
* Phase 15 Attribute Creator Provenance
* Phase 16 Semantic Finding Impact Analysis
* Phase 17 Compiler Review Memory
* Phase 18 Real Repository Evolution Validation

Phase 18 已验证：

真实 AscendNPU-IR 和 triton-ascend workflow 可用。

当前最大架构 gap：

Python composed pipeline 不是一等 pipeline entity。

目标：

建立 Python pipeline semantic provenance。

---

# Step 0 — Architecture review

阅读：

```text
README.md

docs/architecture/

overview.md
schema.md
query-api.md
roadmap.md
status.md

ADR-015.md
ADR-022.md
ADR-023.md


docs/workflows/

repomap/
```

确认：

保持：

Graph:
deterministic facts only

Review:
reasoning

Finding:
persistent knowledge

禁止：

* runtime tracing
* LLM inference
* reasoning 写入 graph

---

# Step 1 — Analyze current limitation

新增：

```text
docs/validation/phase19/python-pipeline-gap.md
```

使用：

triton-ascend:

* make_ttgir
* triton-to-linalg

分析：

当前：

Python:

function

↓

binding

↓

C++ builder

缺少：

Python level ordered stages。

---

# Step 2 — Design Python Pipeline entity

设计：

Pipeline 可以来源：

```text
C++ builder

or

Python composition
```

新增 provenance:

```
Pipeline

 |
 composed_by

PythonFunction

 |
 contains_ordered

PassStage
```

要求：

deterministic。

不确定：

diagnostic。

---

# Step 3 — Implement Python pipeline extractor

支持第一阶段：

Python AST。

识别：

## Pattern A

PassManager:

```python
pm.add_pass(...)
```

记录：

stage order。

---

## Pattern B

pipeline helper:

```python
pipeline = [
 pass_a,
 pass_b
]
```

记录：

ordered composition。

---

## Pattern C

binding call:

```python
make_ttgir(...)
```

关联：

Python composition

↓

C++ pipeline

---

# Step 4 — Query

增加：

```bash
mlir-repomap pipeline-stages <pipeline>
```

输出：

例如：

```
Pipeline:

make_ttgir


Python owner:

compiler.py:xxx


Stages:

1.
 passA

2.
 passB


Evidence:

file:line
```

---

# Step 5 — Workflow integration

更新：

pipeline-audit:

增加：

Python composition lens。

输出：

```
Python stage order

↓

C++ pipeline stages

↓

review risk
```

---

# Step 6 — Validation

真实验证：

triton-ascend:

make_ttgir

要求：

能够回答：

1.

Python 入口在哪里？

2.

Pass 顺序是什么？

3.

对应 C++ builder 是什么？

---

# Step 7 — Regression

确保：

AscendNPU-IR:

已有 pipeline:

不受影响。

---

# Step 8 — Testing

新增：

覆盖：

1.

Python AST extraction

2.

ordered stages

3.

binding association

4.

ambiguous case

5.

missing evidence

保持：

所有已有测试通过。

---

# Step 9 — Documentation

新增：

```text
docs/validation/phase19/
```

更新：

```text
status.md

roadmap.md
```

新增：

ADR-024

主题：

Python pipeline provenance model

明确拒绝：

* runtime interpreter
* semantic execution
* cross repo validation

---

# Step 10 — Final delivery

运行测试。

确认：

```bash
git status clean
```

commit:

```
Phase 19: add Python pipeline semantic provenance
```

push:

```
git push origin main
```

最终报告：

1.

Architecture change

2.

Python pipeline model

3.

Query examples

4.

triton-ascend validation

5.

Workflow impact

6.

Tests

7.

ADR changes

8.

Remaining limitations

9.

Next roadmap recommendation

```

---

Phase 19 完成后，我认为整个系统会达到一个非常稳定的架构终点：

```

C++ compiler facts
+
Python compiler orchestration
+
Review memory
+
Evolution analysis

```

之后才值得重新评估是否需要 watchlist、MCP 等上层能力。现在继续向“平台化”扩展还早，先补齐 Python pipeline 这个最后一个一等公民缺口更合理。
```
