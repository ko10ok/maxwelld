from d42 import schema

ServiceStatusSchema = schema.dict({
    'name': schema.str,
    'state': schema.str,
    'exit_code': schema.int,
    'health': schema.str,
    'status': schema.str,
})
