#include <stdio.h>
#include <libxml/xmlreader.h>
#include "xmlparser.h"

int
parse_xml(xmlTextReaderPtr rd, const xml_schema * schema)
{
	xmlReaderTypes ev_type;
	int ret;
	state_t state = schema->start;
	char fake_close = 0;
	uint8_t *token;
	int len;
	state_t *trans;

read:
	if (state == 0)
		goto error;

	if (fake_close) {
		fake_close = 0;
		ev_type = XML_READER_TYPE_END_ELEMENT;
	} else {
		if ((ret = xmlTextReaderRead(rd)) != 1)
			goto error;
		ev_type = xmlTextReaderNodeType(rd);
	}

	len = 1;
	trans = schema->target_list + schema->target_offset[state];
	switch (ev_type) {
	case XML_READER_TYPE_ELEMENT:
		fake_close = xmlTextReaderIsEmptyElement(rd);
		++ trans; // skip CLOSE transition
		token = schema->token_list + schema->token_offset[state];
		len   = schema->token_length[state];
		printf("OPEN '%s' ", xmlTextReaderConstLocalName(rd));
		while (len > 0) {
			switch (schema->tokens[*token].type) {
			case 0:
				if (xmlStrcmp(BAD_CAST (schema->tokens[*token].localname),
			        xmlTextReaderConstLocalName(rd)) == 0)
			        goto match;
			    break;
			case 1:
				printf("Checking subgraph\n");
				if (xmlStrcmp(BAD_CAST (schema->tokens[*token].localname),
			        xmlTextReaderConstLocalName(rd)) == 0)
			    {
			    	xmlTextReaderNext(rd);
			    	goto match;
			    }
				break;
			case 2:
				break;
			default: {}
			}
			++token, --len, ++trans;
		}
	match:
		break;

	case XML_READER_TYPE_END_ELEMENT:
		printf("CLOSE '%s'", xmlTextReaderConstLocalName(rd));
		break;

	case XML_READER_TYPE_TEXT:
	case XML_READER_TYPE_CDATA:
		printf("TEXT '%s'\n", xmlTextReaderConstValue(rd));
	default: goto read;
	}

	printf(" -> %d%s\n", *trans, (len == 0)? " (default)": "");
	state = *trans;
	goto read;

error:
	/* return 0 if end of document encountered and no more
	 * data expected
	 */
	return !(ret == 0 && state >= schema->first_final);
}

extern xml_schema test_schema;

int
main(int argc, char **argv)
{
	xmlTextReaderPtr reader;
	if (argc != 2)
		return(1);

	LIBXML_TEST_VERSION

	reader = xmlReaderForFile(argv[1], NULL, 0);
	if (reader == NULL) {
		fprintf(stderr, "Unable to open %s\n", argv[1]);
		return (1);
	}
	parse_xml(reader, &test_schema);

	xmlCleanupParser();
	xmlMemoryDump();

	return(0);
}
