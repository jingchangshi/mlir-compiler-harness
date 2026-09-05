def SimpleDialect : Dialect<"simple"> {
  let summary = "Simple test dialect";
}
def Simple_FoldOp : Op<SimpleDialect, "fold"> {
  let summary = "folds things";
}
def SimpleFoldPass : Pass<"simple-fold", "func::FuncOp"> {
  let summary = "folds simple ops";
}
