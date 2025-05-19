import string

from d42 import schema

start_letter = string.ascii_letters + string.digits + '_'
end_letter = string.ascii_letters + string.digits + '_-'

ServiceNameSchema = schema.str.regex(rf'[{start_letter}]+[{end_letter}]+')
