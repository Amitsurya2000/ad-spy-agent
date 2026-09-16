import { Pool } from "pg";

// Lazy-initialized pool, so `next build` never needs a live database - it's
// only opened the first time an API route actually runs. Postgres here is
// only reachable from inside the Docker network (see docker-compose.yml),
// never exposed to the internet, so a plain connection string is enough -
// no service-role-key/RLS layer needed.
let pool: Pool | null = null;

export function getPool(): Pool {
  if (pool) return pool;

  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL must be set (see DEPLOY.md).");
  }

  pool = new Pool({ connectionString });
  return pool;
}
