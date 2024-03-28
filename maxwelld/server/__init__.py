"""
This module used for http server for Maxwell Demon container

Client for this server - maxwelld/client

Each command contains params set described in it's handler (for example up_compose: UpRequestParams)
Param set is used by client for serializing into json; and by server for deserializing same param set from json.
Same happens for response params (for example http_get_status: StatusResponseParams).

For incoming request it searches for initialized maxwelld service instance (core/service) and runs 'up', 'status'
or any other commands.
"""
