#include "SimplePasses.td"
namespace {
struct SimpleFoldPass : public PassWrapper<SimpleFoldPass, OperationPass<func::FuncOp>> {
  StringRef getArgument() const override { return "simple-fold"; }
  void runOnOperation() override {
    RewritePatternSet patterns(&getContext());
    patterns.add<FoldSimplePattern>(&getContext());
  }
};
struct FoldSimplePattern : public OpRewritePattern<Simple_FoldOp> {
  LogicalResult matchAndRewrite(Simple_FoldOp op, PatternRewriter &rewriter) const override {
    rewriter.create<Simple_CanonicalOp>(op.getLoc());
    return success();
  }
};
} // namespace
std::unique_ptr<Pass> createSimpleFoldPass() { return std::make_unique<SimpleFoldPass>(); }

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch
// out-of-line runOnOperation now delegates to the populator
void SimpleFoldPass::runOnOperation() {
  RewritePatternSet patterns(&getContext());
  populateSimpleFoldPatterns(patterns);
  applyPatternsGreedily(getOperation(), std::move(patterns));
}

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch

// touch
