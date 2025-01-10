from d42 import schema

EnvNameSchema = schema.str.regex(r'^[a-z0-9]{1,10}$')
