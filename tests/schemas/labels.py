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

    Label.SERVICE_TEMPLATE_NAME: schema.str,

    Label.COMPOSE_FILES: schema.str,
    Label.COMPOSE_FILES_INSTANCE: schema.str,

    Label.ENV_CONFIG_TEMPLATE: schema.str,
    Label.ENV_CONFIG: schema.str,
    ...: ...,
})
