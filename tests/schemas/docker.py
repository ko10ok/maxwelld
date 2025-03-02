from d42 import schema

from schemas.labels import LabelsSchema

ContainerSchema = schema.dict({
    'Labels': LabelsSchema,
    'State': schema.str('running') | schema.str,
    ...: ...,
})
