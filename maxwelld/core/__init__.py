"""
Core if maxwelld service.

It stores all in flight environments, prerequisites for env, "up" and "down" sequences.

Base run sequence:
    - if requested environment (d-c files + service env params + name/purpose) exist
      -> return env_id
    - if requested environment doesnt ready
      -> config d-c files with service env params
      -> run environment
      -> run migrations for each service
      -> return env_id

All Maxwelld service commands made by sequence of such atomic docker-compose commands:
> docker-compose up -d %services%
> docker-compose down -d %services%
> docker-compose status
> docker-compose exec %service% %cmd%

Used docker-compose commands described in compose_interface
"""
