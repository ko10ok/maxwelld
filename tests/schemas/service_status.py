from d42 import schema

ServiceStatusSchema = schema.dict({
    'name': schema.str,
    'state': schema.str,
    'health': schema.str,
    'status': schema.str,
})
