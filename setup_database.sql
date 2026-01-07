-- PostgreSQL Database Setup Script for Food Delivery Platform
-- Run this script to create database, user, and grant proper privileges

-- ==============================================================================
-- STEP 1: Create Database (if not exists)
-- ==============================================================================

-- Check if database exists, create if not
SELECT 'CREATE DATABASE fooddelivery'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fooddelivery')\gexec

-- ==============================================================================
-- STEP 2: Create Dedicated Application User
-- ==============================================================================

-- Drop user if exists (for clean setup)
DROP USER IF EXISTS fooddelivery_user;

-- Create application user with password
CREATE USER fooddelivery_user WITH
  LOGIN
  PASSWORD 'Nishat@n1'
  NOSUPERUSER
  INHERIT
  CREATEDB
  NOCREATEROLE
  NOREPLICATION
  CONNECTION LIMIT -1;

-- Add comment
COMMENT ON ROLE fooddelivery_user IS 'Application user for Food Delivery Platform';

-- ==============================================================================
-- STEP 3: Grant Database Access
-- ==============================================================================

-- Grant CONNECT privilege on database
GRANT CONNECT ON DATABASE fooddelivery TO fooddelivery_user;

-- Grant TEMPORARY privilege (allows temp tables)
GRANT TEMPORARY ON DATABASE fooddelivery TO fooddelivery_user;

-- ==============================================================================
-- STEP 4: Connect to fooddelivery database and grant schema privileges
-- ==============================================================================

\c fooddelivery

-- Grant all privileges on public schema
GRANT ALL PRIVILEGES ON SCHEMA public TO fooddelivery_user;

-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO fooddelivery_user;

-- ==============================================================================
-- STEP 5: Grant Table Privileges (existing and future tables)
-- ==============================================================================

-- Grant all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fooddelivery_user;

-- Grant all privileges on all existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fooddelivery_user;

-- Grant all privileges on all existing functions
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO fooddelivery_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO fooddelivery_user;

-- Set default privileges for future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO fooddelivery_user;

-- Set default privileges for future functions
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON FUNCTIONS TO fooddelivery_user;

-- ==============================================================================
-- STEP 6: Grant Additional Privileges
-- ==============================================================================

-- Allow creating extensions (if needed for PostGIS, etc.)
GRANT CREATE ON DATABASE fooddelivery TO fooddelivery_user;

-- ==============================================================================
-- STEP 7: Verify Setup
-- ==============================================================================

-- Show database
\l fooddelivery

-- Show user
\du fooddelivery_user

-- Show granted privileges
\dp

-- ==============================================================================
-- COMPLETE! You can now use these credentials:
-- ==============================================================================
-- Host: localhost
-- Port: 5432
-- Database: fooddelivery
-- User: fooddelivery_user
-- Password: Nishat@n1
-- Connection String: postgresql+asyncpg://fooddelivery_user:Nishat%40n1@localhost:5432/fooddelivery
-- Note: @ symbol is URL-encoded as %40 in connection strings
-- ==============================================================================

