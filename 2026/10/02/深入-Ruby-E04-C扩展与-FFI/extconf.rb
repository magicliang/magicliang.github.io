require 'mkmf'
$CFLAGS << ' -std=c11 -Wall -Wextra -Wno-unused-parameter'
abort 'POSIX poll required' unless have_header('poll.h')
create_makefile('native_box')
