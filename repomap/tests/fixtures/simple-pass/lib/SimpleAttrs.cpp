#include "SimplePasses.td"

// OpBuilder creator: op build method constructs + attaches the attribute
void SimpleOp::build(::mlir::OpBuilder &odsBuilder, ::mlir::OperationState &state) {
  state.addAttribute(Simple_MagicAttr::name,
                     Simple_MagicAttr::get(odsBuilder.getContext()));
}

// verifier container: reads the attribute, never creates it
::mlir::LogicalResult SimpleCheckOp::verify() {
  if (!(*this)->getAttr(Simple_MagicAttr::name))
    return failure();
  return success();
}

// RewritePattern creator: constructs and attaches
struct MagicAnnotatePattern
    : public OpRewritePattern<Simple_FoldOp> {
  using OpRewritePattern<Simple_FoldOp>::OpRewritePattern;
  LogicalResult matchAndRewrite(Simple_FoldOp op,
                                PatternRewriter &rewriter) const override {
    auto magic = Simple_MagicAttr::get(rewriter.getContext());
    op->setAttr(Simple_MagicAttr::name, magic);
    return success();
  }
};

// ConversionPattern creator: attaches during conversion
struct MagicConvertPattern
    : public OpConversionPattern<Simple_FoldOp> {
  using OpConversionPattern<Simple_FoldOp>::OpConversionPattern;
  LogicalResult matchAndRewrite(
      Simple_FoldOp op, OpAdaptor adaptor,
      ConversionPatternRewriter &rewriter) const override {
    rewriter.replaceOp(op, adaptor.getOperands());
    rewriter.modifyOpIfExists([&](Operation *root) {
      root->setAttr(Simple_MagicAttr::name, UnitAttr::get(rewriter.getContext()));
    });
    return success();
  }
};

// PipelineBuilder creator: attaches while building the pipeline
void buildMagicPipeline(OpPassManager &pm, ModuleOp module) {
  pm.addPass(createSimpleFoldPass());
  module->setAttr(Simple_MagicAttr::name, UnitAttr::get(module.getContext()));
}

// pass creator for the second attribute (name-collision pair)
struct SimpleAttrPass : public PassWrapper<OperationPass<ModuleOp>> {
  void runOnOperation() override {
    getOperation()->setAttr(Simple_MagicV2Attr::name,
                            UnitAttr::get(&getContext()));
  }
};
