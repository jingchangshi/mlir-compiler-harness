void buildSimplePipeline(OpPassManager &pm, const Config &config) {
  pm.addPass(createInlinePass());
  if (config.getEnableFancy()) {
    pm.addPass(createSimpleFoldPass());
    pm.addPass(createCleanupPass());
  }
  pm.nest<func::FuncOp>().addPass(createSimpleFoldPass());
  buildSubPipeline(pm);
}
void buildSubPipeline(OpPassManager &pm) {
  pm.addPass(createCanonicalizePass());
}
