# 新 Compiler Engineer 可用性评估

模拟问题：“解释 HFusion RegBase pipeline 中 MergeVecScope 到后续 lowering 的约束
关系”。本节只使用 `mlir-repomap` 与 `docs/compiler-architecture/`，未 grep 或阅读
编译器源树。

1. `pass MergeVecScope` 给出真实 id、两处 guarded membership、后继
   `convert-to-hivm-op` 和 4 条 exact test。
2. 对返回的 file-qualified pipeline 调用 `pipeline`/`pipeline-builder`，得到
   `HIVMRegbasePipelines.cpp:223`，并区分 level 1 bufferize 前与 level 2 首轮后。
3. `pass-constraints`/`review` 给出 `:1422/:1625` verify guard 与 MVS-001 的
   unguarded single-use VF history。
4. 两份定向 dossier 提供已证据化的 swap outcome：merge 与 copy insertion 交换会
   no-op，随后 convert-to-hivm-op 消费合并 call graph。

故工程师可回答：guard 保护合并结果合法性、不保护 call-count；修改时先重跑四条
test，再审查 call-count 与 dependency closure。4 次查询和 2 份定向文档替代了手工
搜索、全仓阅读和同名 pipeline 猜测；最终语义判断仍由工程师承担。
