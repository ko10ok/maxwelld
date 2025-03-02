from d42 import schema

from maxwelld.helpers.labels import Label

LabelsSchema = schema.dict({
    'com.docker.compose.service': schema.str,
    'com.docker.compose.project.config_files': schema.str,
    'com.docker.compose.project': schema.str,
    'com.docker.compose.project.working_dir': schema.str,

    Label.RELEASE_ID: schema.str,
    Label.ENV_ID: schema.str,
    Label.REQUEST_ENV_NAME: schema.str,
    Label.CLIENT_ENV_NAME: schema.str,
    # 'com.maxwelld.env_path': schema.str,

    Label.COMPOSE_FILES: schema.str,
    Label.COMPOSE_FILES_INSTANCE: schema.str,
    # 'com.maxwelld.env_config_template': schema.str,
    # 'com.maxwelld.env_service_map': schema.str,
    ...: ...,
})
