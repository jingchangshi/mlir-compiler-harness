// same-name builder in another file: must NOT merge (QG-1 / ADR-012)
void buildSimplePipeline(OpPassManager &pm) {
  pm.addPass(createSimpleFoldPass());
}
