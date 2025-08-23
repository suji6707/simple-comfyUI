-- Initial database setup script
-- This will be run when PostgreSQL container starts for the first time

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
-- These will be created by Alembic migrations, but having them here ensures they exist