# Database Schema Visualizer

Interactive ERD (Entity-Relationship Diagram) generator for visualizing database schemas.

## Features

### Schema Import
- **SQL Import**: Paste CREATE TABLE statements to auto-generate diagrams
- **Sample Schema**: Load a sample e-commerce schema to explore
- **Manual Creation**: Add tables and columns manually

### Visual ERD Canvas
- **Drag & Drop**: Move tables around the canvas freely
- **Pan & Zoom**: Navigate large schemas easily (mouse wheel to zoom)
- **Mini Map**: Overview of entire schema in corner
- **Relationship Lines**: Curved bezier connections between related tables

### Column Types & Constraints
- **Primary Keys (🔑)**: Golden badge for PKs
- **Foreign Keys (🔗)**: Cyan badge for FKs
- **NOT NULL (NN)**: Red constraint tag
- **UNIQUE (UQ)**: Green constraint tag
- **Data Types**: Show/hide column types

### Relationship Detection
- Automatically detects REFERENCES in SQL
- Shows one-to-one, one-to-many, many-to-many
- Visual legend in sidebar

### Export Options
- **JSON Schema**: Full schema definition
- **SQL DDL**: Regenerate CREATE TABLE statements
- **PNG/SVG**: Image export (coming soon)

## Usage

1. **Import SQL**: Click "Import SQL" and paste your CREATE TABLE statements
2. **Or Load Sample**: Click "Load Sample Schema" for demo data
3. **Arrange**: Drag tables to organize, or click "Auto Arrange"
4. **Explore**: Zoom in/out, pan around, click tables to select
5. **Export**: Choose format and download

## Keyboard Shortcuts
- Mouse wheel: Zoom in/out
- Click + drag on canvas: Pan view
- Click + drag on table: Move table

## SQL Parsing Supported
```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    dept_id INT REFERENCES departments(id)
);
```

Parses:
- Column names and data types
- PRIMARY KEY constraint
- NOT NULL constraint
- UNIQUE constraint
- REFERENCES (foreign keys)

## Statistics Panel
- Total tables count
- Total columns count
- Relationships detected
- Primary keys count

## Display Options
- Show/hide data types
- Show/hide constraints
- Show/hide relationship lines

Built by PM2 for the Clawdbot pipeline.
