from d42 import schema

ContainerSchema = schema.dict({
    'Labels': schema.dict({
        'com.docker.compose.service': schema.str,
        'com.docker.compose.project.config_files': schema.str,
        'com.docker.compose.project': schema.str,
        'com.docker.compose.project.working_dir': schema.str,
        ...: ...,
    }),
    'State': schema.str('running') | schema.str,
    ...: ...,
})
