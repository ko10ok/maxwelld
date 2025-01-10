from d42 import optional
from d42 import schema

ContainerSchema = schema.dict({
    'Labels': schema.dict({
        optional('com.docker.maxwelld.release_id'): schema.str,
        'com.docker.compose.service': schema.str,
        'com.docker.compose.project.config_files': schema.str,
        'com.docker.compose.project': schema.str,
        'com.docker.compose.project.working_dir': schema.str,
        ...: ...,
    }),
    'State': schema.str('running') | schema.str,
    ...: ...,
})
