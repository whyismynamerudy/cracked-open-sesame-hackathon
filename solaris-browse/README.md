_______.  ______    __          ___      .______       __       _______.
/       | /  __  \  |  |        /   \     |   _  \     |  |     /       |
|   (----`|  |  |  | |  |       /  ^  \    |  |_)  |    |  |    |   (----`
\   \    |  |  |  | |  |      /  /_\  \   |      /     |  |     \   \    
.----)   |   |  `--'  | |  `----./  _____  \  |  |\  \----.|  | .----)   |   
|_______/     \______/  |_______/__/     \__\ | _| `._____||__| |_______/    
```

# Solaris Browse

## Database Setup

1. Install dependencies:
```bash
cd solaris-browse
poetry install
```

2. Start PostgreSQL:
```bash
docker compose up -d
```

3. Run migrations:
```bash
poetry run migrate
```

## Database Schema

### Agents Table
- id (UUID, primary key)
- session_id (UUID)
- intent (text)

### Agent Loops Table
- agent_id (UUID, foreign key to agents.id)
- iteration (integer)
- plan_result (text)
- execution_result (text)

## Connection String
```
postgresql://postgres:postgres@localhost:5432/app_db
