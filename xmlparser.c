#include <stdio.h>
#include <stdint.h>
#include <libxml/xmlreader.h>
#include "xmlparser.h"

int
parse_xml(xmlTextReaderPtr rd, const xml_schema * schema)
{
	const element_t *elt;
	xmlReaderTypes ev_type;
	const uint8_t *trans;
	int i;
	int status;
	int fake_close = 0;
	parser_ctx ctx = {
		rd: rd,
		state: schema->entry
	};

read:
	if (ctx.state == 0)
		goto error;

	if (fake_close) {
		fake_close = 0;
		ev_type = XML_READER_TYPE_END_ELEMENT;
	} else {
		if ((status = xmlTextReaderRead(ctx.rd)) != 1)
			goto error;
		ev_type = xmlTextReaderNodeType(ctx.rd);
	}

	trans = schema->targets.list + schema->targets.offset[ctx.state];

	switch (ev_type) {
	case XML_READER_TYPE_ELEMENT:
		fake_close = xmlTextReaderIsEmptyElement(ctx.rd);
		trans += 1; // skip over the END_ELEMENT transition
		for (i = 0; i < schema->token_names.count[ctx.state]; i++) {
			elt = schema->elements + schema->token_names.list[ schema->token_names.offset[ctx.state] + i ];
			if (elt->localname[0] == '*') {
			// a wildcard, check namespace only
				printf("\tChecking against wildcard\n");
				xmlTextReaderNext(ctx.rd);
				break;
			} else if (elt->localname[0] == '!') {
			// a substitution group, check if this is a proper substitute
				printf("\tChecking against substitution group %s\n", elt->localname + 1);
			} else {
			// normal element name
				if (xmlStrcmp(BAD_CAST elt->localname, xmlTextReaderConstLocalName(ctx.rd)) == 0)
					// take this transition
					break;
			}
		}
		if (i >= schema->token_names.count[ctx.state]) {
			printf("No match for %s found in %d possibilities\n", BAD_CAST xmlTextReaderConstLocalName(ctx.rd), schema->token_names.count[ctx.state]);
			int n;
			for (n = 0; n < schema->token_names.count[ctx.state]; n++)
				printf("  possible value: %s\n", schema->elements[ schema->token_names.list[ schema->token_names.offset[ctx.state] + n]].localname);
		} else
			printf("'%s' accepted\n", BAD_CAST xmlTextReaderConstLocalName(ctx.rd));
		trans += i;
		break;

	case XML_READER_TYPE_END_ELEMENT:
		/* simply take the transition */
		if (*trans == 0)
			printf("END_ELEMENT not allowed here\n");
		else
			printf("'/%s' accepted\n", BAD_CAST xmlTextReaderConstLocalName(ctx.rd));
		break;

	case XML_READER_TYPE_TEXT:
	case XML_READER_TYPE_CDATA:
		/* pass text data to current handler */
		puts((char*)xmlTextReaderConstValue(ctx.rd));

	default:
		/* skip over */
		goto read;
	}

	ctx.state = *trans;
	schema->dispatch(trans - schema->targets.list, &ctx);
	goto read;

error:
	return !(status == 0 && ctx.state >= schema->first_final);
}

extern xml_schema example_schema;

int
main(int argc, char **argv)
{
	int status;
	xmlTextReaderPtr reader;
	if (argc != 2)
		return(1);

	LIBXML_TEST_VERSION

	reader = xmlReaderForFile(argv[1], NULL, 0);
	if (reader == NULL) {
		fprintf(stderr, "Unable to open %s\n", argv[1]);
		return (1);
	}
	status = parse_xml(reader, &example_schema);

	xmlCleanupParser();
	xmlMemoryDump();

	if (status != 0) printf("Document not valid\n");
	return(status);
}
