#include "xmlparser.h"

static void dispatch(int trans, parser_ctx *ctx);

/*
 * This is the schema source file template. Insert the
 * output of xsdcc.py right after this comment.
 */


static void dispatch(int trans, parser_ctx *ctx)
{
	const uint8_t *a = action_list + action_offsets[trans];
	printf("  Running %d actions for transition %d\n", *a, trans);
	uint8_t i;
	for(i= *(a++); i > 0; i--, a++) {
		printf("    Running action %s\n", action_names[*a]);
		switch (*a) {
			default:
				break;
		}
	}
}
