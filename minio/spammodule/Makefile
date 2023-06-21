CC     = gcc
CFLAGS = -I -Wall -I/usr/include/python3.8
DEPS   = spammodule.h # $(python3.8-config --includes)
OBJ    = spammodule.o

%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

module: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS)

clean:
	rm -f module spammodule.o