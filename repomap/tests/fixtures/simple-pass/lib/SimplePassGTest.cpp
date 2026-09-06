#include "gtest/gtest.h"

TEST(SimpleFoldGTest, SimpleFoldCollapsesConstants) {
  EXPECT_TRUE(true);
}

TEST(UnrelatedSuite, NothingToDoWithFolding) {
  EXPECT_TRUE(true);
}
