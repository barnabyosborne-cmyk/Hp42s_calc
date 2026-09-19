#include <stdio.h>
#include <fenv.h>
#include "bid_conf.h"
#include "bid_functions.h"

void bid_selftest(void) {
    BID_UINT128 a, b, c;
    char buf[64];
    bid128_from_string(&a, "1");
    bid128_from_string(&b, "7");
    bid128_div(&c, &a, &b);
    bid128_to_string(buf, &c);
    printf("1/7 = %s\n", buf);
}
