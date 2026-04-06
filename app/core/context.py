from contextvars import ContextVar

# Contexto por request/proceso
ctx_trace_id = ContextVar("trace_id", default=None)
ctx_process_type = ContextVar("process_type", default=None)  # "agenda"|"bot"|"sms"|"tracking"|"mail"|...
ctx_process_id = ContextVar("process_id", default=None)
ctx_tenant = ContextVar("tenant", default=None)
ctx_user = ContextVar("user", default=None)

def bind_context(logger):
    return logger.bind(
        trace_id=ctx_trace_id.get(),
        process_type=ctx_process_type.get(),
        process_id=ctx_process_id.get(),
        tenant=ctx_tenant.get(),
        user=ctx_user.get(),
    )
