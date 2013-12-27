#ifndef _XML_PARSER_H_INCLUDED
#define _XML_PARSER_H_INCLUDED

#include <stdint.h>
#include <libxml/xmlreader.h>

typedef uint16_t state_t;
typedef uint8_t index_t;
typedef struct xml_schema xml_schema;

typedef struct {
	xmlTextReaderPtr rd;
} parser_ctx;

typedef struct {
	char type;
	char ns;
	char *localname;
} token_t;

struct xml_schema {
	token_t *tokens;
	uint8_t *token_list;
	index_t *token_offset;
	index_t *token_length;

    state_t *target_list;
    index_t *target_offset;

    state_t start;
    state_t first_final;

    void (*dispatch)(int, parser_ctx*);
};

#endif /* _XML_PARSER_H_INCLUDED */
