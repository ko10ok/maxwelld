from d42 import schema

from schemas.labels import LabelsSchema

MountsSchema = schema.dict({
    'Type': schema.str('bind'),
    'Source': schema.str,
    'Destination': schema.str,
    'Mode': schema.str,
    'RW': schema.bool,
    'Propagation': schema.str,
})

ContainerSchema = schema.dict({
    'Labels': LabelsSchema,
    'State': schema.str('running') | schema.str,
    'Mounts': schema.list(MountsSchema),
    ...: ...,
})
