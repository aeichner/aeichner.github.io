LIBXML2_LIBS=`pkg-config --libs libxml-2.0`
LIBXML2_CFLAGS=`pkg-config --cflags libxml-2.0`

LDFLAGS=$(LIBXML2_LIBS)
CFLAGS=-Wall -g -std=gnu99 $(LIBXML2_CFLAGS)

DEPENDS=.depend

.PHONY: clean

SRC=xmlparser.c linesymbolizer.c
OBJS=$(SRC:%.c=%.o)

all: test
test: $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

clean:
	rm -rf $(OBJS) test

dep: $(SRC)
	$(CC) -MM $(SRC) > $(DEPENDS)
