#include "ruby.h"
#include "ruby/thread.h"
#include <poll.h>
#include <unistd.h>
#include <stdatomic.h>
#include <string.h>
typedef struct { char *bytes; size_t size; VALUE label; } box_t;
static long live_buffers = 0;
static _Atomic int waiting = 0;
static void release_buffer(box_t *box) {
    if (box->bytes) { xfree(box->bytes); box->bytes = NULL; box->size = 0; live_buffers--; }
}
static void box_mark(void *ptr) { rb_gc_mark(((box_t *)ptr)->label); }
static void box_free(void *ptr) { box_t *box = ptr; release_buffer(box); xfree(box); }
static size_t box_size(const void *ptr) { const box_t *box = ptr; return sizeof(*box) + box->size; }
static const rb_data_type_t box_type = {
    .wrap_struct_name = "Workshop::NativeBox",
    .function = { .dmark = box_mark, .dfree = box_free, .dsize = box_size },
    .flags = RUBY_TYPED_FREE_IMMEDIATELY
};
static VALUE box_alloc(VALUE klass) {
    box_t *box;
    VALUE obj = TypedData_Make_Struct(klass, box_t, &box_type, box);
    box->label = Qnil;
    return obj;
}
static VALUE box_init(VALUE self, VALUE size, VALUE label) {
    box_t *box; TypedData_Get_Struct(self, box_t, &box_type, box);
    if (box->bytes || !NIL_P(box->label)) rb_raise(rb_eRuntimeError, "already initialized");
    if (!RB_INTEGER_TYPE_P(size)) rb_raise(rb_eTypeError, "size must be Integer");
    long n = NUM2LONG(size);
    if (n < 1 || n > 1024) rb_raise(rb_eArgError, "size out of range");
    Check_Type(label, T_STRING);
    box->label = rb_str_dup(label);
    rb_obj_freeze(box->label);
    box->bytes = ALLOC_N(char, n);
    box->size = (size_t)n; live_buffers++;
    memset(box->bytes, 'A', box->size);
    return self;
}
static VALUE box_label(VALUE self) {
    box_t *box; TypedData_Get_Struct(self, box_t, &box_type, box); return box->label;
}
static VALUE box_read(VALUE self) {
    box_t *box; TypedData_Get_Struct(self, box_t, &box_type, box);
    if (!box->bytes) rb_raise(rb_eIOError, "closed");
    return rb_str_new(box->bytes, (long)box->size);
}
static VALUE box_close(VALUE self) {
    box_t *box; TypedData_Get_Struct(self, box_t, &box_type, box);
    if (!box->bytes) return Qfalse;
    release_buffer(box); return Qtrue;
}
static VALUE live(VALUE klass) { return LONG2NUM(live_buffers); }
typedef struct { int ready_fd, input_fd, ok; } wait_t;
static void *native_wait(void *ptr) {
    wait_t *state = ptr;
    atomic_store(&waiting, 1);
    char token = 'r';
    if (write(state->ready_fd, &token, 1) != 1) { atomic_store(&waiting, 0); return NULL; }
    struct pollfd input = { .fd = state->input_fd, .events = POLLIN };
    if (poll(&input, 1, 1200) == 1 && (input.revents & POLLIN)) {
        state->ok = read(state->input_fd, &token, 1) == 1 && token == 'x';
    }
    atomic_store(&waiting, 0);
    return NULL;
}
static VALUE wait_for_token(VALUE klass, VALUE ready, VALUE input, VALUE unlock) {
    wait_t state = { .ready_fd = NUM2INT(ready), .input_fd = NUM2INT(input), .ok = 0 };
    if (RTEST(unlock)) rb_thread_call_without_gvl(native_wait, &state, NULL, NULL);
    else native_wait(&state);
    return state.ok ? Qtrue : Qfalse;
}
static VALUE is_waiting(VALUE klass) { return atomic_load(&waiting) ? Qtrue : Qfalse; }
void Init_native_box(void) {
    VALUE klass = rb_define_class("NativeBox", rb_cObject);
    rb_define_alloc_func(klass, box_alloc);
    rb_define_method(klass, "initialize", box_init, 2);
    rb_define_method(klass, "label", box_label, 0);
    rb_define_method(klass, "read", box_read, 0);
    rb_define_method(klass, "close", box_close, 0);
    rb_define_singleton_method(klass, "live_buffers", live, 0);
    rb_define_singleton_method(klass, "wait_for_token", wait_for_token, 3);
    rb_define_singleton_method(klass, "waiting?", is_waiting, 0);
}
