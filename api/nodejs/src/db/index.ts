import Database from "better-sqlite3";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = process.env.DATABASE_PATH || path.join(__dirname, "../../data/rfp.db");

export const db = new Database(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS rfps (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    website_url TEXT,
    customer TEXT,
    industry TEXT,
    status TEXT DEFAULT 'uploaded',
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY,
    rfp_id TEXT NOT NULL,
    req_id TEXT NOT NULL,
    description TEXT,
    type TEXT,
    mandatory INTEGER DEFAULT 1,
    source_section TEXT,
    FOREIGN KEY (rfp_id) REFERENCES rfps(id)
  );

  CREATE TABLE IF NOT EXISTS responses (
    id TEXT PRIMARY KEY,
    rfp_id TEXT NOT NULL,
    requirement_id TEXT NOT NULL,
    response TEXT,
    status TEXT,
    confidence REAL,
    evidence TEXT,
    review_required INTEGER DEFAULT 1,
    review_status TEXT DEFAULT 'pending',
    model_used TEXT,
  FOREIGN KEY (rfp_id) REFERENCES rfps(id)
  );

  CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_id TEXT,
    action TEXT,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    document_type TEXT DEFAULT 'historical',
    industry TEXT,
    year INTEGER,
    approval_status TEXT DEFAULT 'approved',
    chunks_ingested INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
  );
`);

const rfpColumns = db.prepare("PRAGMA table_info(rfps)").all() as Array<{
  name: string;
}>;
if (!rfpColumns.some((column) => column.name === "website_url")) {
  db.exec("ALTER TABLE rfps ADD COLUMN website_url TEXT");
}
if (!rfpColumns.some((column) => column.name === "owner_id")) {
  db.exec("ALTER TABLE rfps ADD COLUMN owner_id TEXT");
}
if (!rfpColumns.some((column) => column.name === "submission_status")) {
  db.exec(
    "ALTER TABLE rfps ADD COLUMN submission_status TEXT DEFAULT 'published'"
  );
}
if (!rfpColumns.some((column) => column.name === "published_at")) {
  db.exec("ALTER TABLE rfps ADD COLUMN published_at TEXT");
}
