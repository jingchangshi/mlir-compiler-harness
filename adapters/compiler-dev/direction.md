# CompilerDev Harness 演进方向（非实现）

下一步建议在 **dsh creative mode** 中，根据真实 compiler 任务反馈逐步演进
CompilerDev Harness；本仓库在 Phase 20 不实现该 runtime，也不改动 DeepSeek Harness 或
任何外部仓库。

方向是让 Harness 以任务类型选择 `workflow-contract.md` 的预设查询序列，保存原始 JSON
和最少量非敏感 session observation，并用真实 Ascend compiler 任务检验是否减少无目标的
源码搜索。优先验证 verifier 定位、finding impact 与 Python pipeline audit 三类任务；若
反馈稳定地显示同一缺口，再提出一个确定性 query 或 workflow 变更，并以真实证据评审。

不应把 creative-mode 的推理、摘要或执行轨迹写入 compiler graph，也不应由 runtime 自动
改变 finding 生命周期。外部 Harness 的实现与部署决策仍由该项目单独拥有。
