#include "SimplePasses.td"
void populateSimpleFoldPatterns(RewritePatternSet &patterns) {
  patterns.add<FoldSimplePattern>(patterns.getContext());
  patterns.add<SecondSimplePattern>(patterns.getContext());
}
