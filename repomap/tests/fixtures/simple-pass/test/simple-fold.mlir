// RUN: bishengir-opt %s --simple-fold | FileCheck %s
// CHECK-LABEL: func.func
func.func @test(%a : i32) -> i32 { return %a : i32 }
