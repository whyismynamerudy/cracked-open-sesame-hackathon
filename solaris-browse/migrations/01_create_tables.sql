-- Create UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    intent TEXT
);

-- Create agent_loops table
CREATE TABLE agent_loops (
    agent_id UUID NOT NULL REFERENCES agents(id),
    iteration INTEGER NOT NULL,
    plan_result TEXT,
    execution_result TEXT,
    PRIMARY KEY (agent_id, iteration)
);

-- Create a function to auto-increment iteration per agent_id
CREATE OR REPLACE FUNCTION next_iteration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.iteration IS NULL THEN
        SELECT COALESCE(MAX(iteration) + 1, 1)
        INTO NEW.iteration
        FROM agent_loops
        WHERE agent_id = NEW.agent_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-set iteration
CREATE TRIGGER set_iteration
    BEFORE INSERT ON agent_loops
    FOR EACH ROW
    EXECUTE FUNCTION next_iteration();
