#include "xmlparser.h"
/*
typedef uint16_t state_t;
typedef uint8_t index_t;
typedef struct xml_schema xml_schema;

struct xml_schema {
	char ** tokens;
	uint8_t *token_list;
	index_t *token_offset;
	index_t *token_length;


    state_t *target_list;
    index_t *target_offset;

    state_t start;
    state_t first_final;
};

*/

static const token_t _tokens[] = {
	{0, 0, "LineSymbolizer"},
	{0, 0, "BaseSymbolizer"},
	{0, 0, "Description"},
	{0, 0, "Geometry"},
	{0, 0, "Name"},
	{0, 0, "PerpendicularOffset"},
	{0, 0, "Stroke"},
	{0, 0, "Abstract"},
	{0, 0, "Title"},
	{0, 0, "OnlineResource"},
	{0, 0, "PropertyName"},
	{0, 0, "GraphicFill"},
	{0, 0, "GraphicStroke"},
	{0, 0, "SvgParameter"},
	{2, 0, "expression"},
	{1, 0, "Graphic"},
	{0, 0, "Gap"},
	{0, 0, "InitialGap"}
};

/*
entry:
	 1 | LineSymbolizer -> 2
	 2 | /LineSymbolizer -> 9, BaseSymbolizer -> 5, Description -> 4, Geometry -> 6, Name -> 3, PerpendicularOffset -> 8, Stroke -> 7
	 3 | /Name -> 10
	 4 | /Description -> 13, Abstract -> 12, Title -> 11
	 5 | OnlineResource -> 14
	 6 | PropertyName -> 15
	 7 | /Stroke -> 19, GraphicFill -> 16, GraphicStroke -> 17, SvgParameter -> 18
	 8 | /PerpendicularOffset -> 20, expression -> 8
	 9 | /GraphicStroke -> 27
	 10 | /LineSymbolizer -> 33, BaseSymbolizer -> 5, Description -> 4, Geometry -> 6, PerpendicularOffset -> 8, Stroke -> 7
	 11 | /Title -> 21
	 12 | /Abstract -> 22
	 13 | /LineSymbolizer -> 33, BaseSymbolizer -> 5, Geometry -> 6, PerpendicularOffset -> 8, Stroke -> 7
	 14 | /OnlineResource -> 23
	 15 | /PropertyName -> 24
	 16 | Graphic -> 25
	 17 | Graphic -> 26
	 18 | /SvgParameter -> 27, expression -> 18
	 19 | /LineSymbolizer -> 33, PerpendicularOffset -> 8
	 20 | /LineSymbolizer -> 33
	 21 | /Description -> 13, Abstract -> 12
	 22 | /Description -> 13
	 23 | /BaseSymbolizer -> 28
	 24 | /Geometry -> 29
	 25 | /GraphicFill -> 27
	 26 | /GraphicStroke -> 27, Gap -> 31, InitialGap -> 30
	 27 | /Stroke -> 19, SvgParameter -> 18
	 28 | /LineSymbolizer -> 33, Geometry -> 6, PerpendicularOffset -> 8, Stroke -> 7
	 29 | /LineSymbolizer -> 33, PerpendicularOffset -> 8, Stroke -> 7
	 30 | /InitialGap -> 32, expression -> 30
	 31 | /Gap -> 33, expression -> 31
	 32 | /GraphicStroke -> 27, Gap -> 31
	[33]| 
*/

static const uint8_t token_list[] = {
	0,
	1, 2, 3, 4, 5, 6,
	//
	7, 8,
	9,
	10,
	11, 12, 13,
	14,
	//
	1, 2, 3, 5, 6,
	//
	//
	1, 3, 5, 6,
	//
	//
	15,
	15,
	14,
	5,
	//
	7,
	//
	//
	//
	//
	16, 17,
	13,
	3, 5, 6,
	5, 6,
	14,
	14,
	16
};

static const index_t token_offset[] = {
	0,
	0,
	1, 7, 7, 9, 10, 11, 14, 15, 15, 20, 20, 20, 24, 24, 24, 25, 26, 27, 28, 28, 29, 30, 30, 30, 30, 30, 32, 33, 36, 38, 39, 40, 41
};

static const index_t token_length[] = {
	0, 1, 6, 0, 2, 1, 1, 3, 1, 0, 5, 0, 0, 4, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 2, 1, 3, 2, 1, 1, 1, 0
};

static const state_t target_list[] = {
	 0, 0,
	 0, 2, 0,
	 9, 5, 4, 6, 3, 8, 7, 0,
	10, 0,
	13, 12, 11, 0,
	 0, 14, 0,
	 0, 15, 0,
	19, 16, 17, 18, 0,
	20, 8, 0,
	27, 0,
	33, 5, 4, 6, 8, 7, 0,
	21, 0,
	22, 0,
	33, 5, 6, 8, 7, 0,
	23, 0,
	24, 0,
	 0, 25, 0,
	 0, 26, 0,
	27, 18, 0,
	33,  8, 0,
	33,  0,
	13, 12, 0,
	13, 0,
	28, 0,
	29, 0,
	27, 0,
	27, 31, 30, 0,
	19, 18, 0,
	33,  6, 8, 7, 0,
	33,  8, 7, 0,
	32, 30, 0,
	33, 31, 0,
	27, 31, 0,
	 0,  0
};

static const index_t target_offset[] = {
	  0,  2,  5, 13, 15, 19, 22, 25, 30, 33,
	 35, 42, 44, 46, 52, 54, 56, 59, 62, 65,
	 68, 70, 73, 75, 77, 79, 81, 85, 88, 93,
	 97,100,103,106
};

xml_schema const test_schema = {
	.start = 1,
	.tokens = _tokens,
	.token_list = token_list,
	.token_offset = token_offset,
	.token_length = token_length,
	.target_list = target_list,
	.target_offset = target_offset
};
