from d42 import schema

from schemas.labels import LabelsSchema

ServiceStatusSchema = schema.dict({
    'name': schema.str,
    'state': schema.str,
    'exit_code': schema.int,
    'health': schema.str,
    'status': schema.str,
    'labels': LabelsSchema,
})
