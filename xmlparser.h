#ifndef _XML_PARSER_H_INCLUDED
#define _XML_PARSER_H_INCLUDED

#include <stdint.h>
#include <libxml/xmlreader.h>

typedef struct {
	xmlTextReaderPtr rd;
	unsigned int state;
} parser_ctx;

typedef struct {
    uint8_t namespace_id;
    const char * localname;
} element_t;

typedef struct xml_schema xml_schema;
struct xml_schema {
    const char ** namespaces;
    const element_t * elements;
    const struct {
        const uint8_t * list;
        const uint8_t * offset;
        const uint8_t * count;
    } token_names;
    const struct {
        const uint8_t * list;
        const uint8_t * offset;
    } targets;
    int first_final;
    int entry;
    void (*dispatch)(int, parser_ctx*);
};

#endif /* _XML_PARSER_H_INCLUDED */
