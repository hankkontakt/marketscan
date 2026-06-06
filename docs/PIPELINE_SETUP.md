# Pipeline Setup Guide

## Supabase Connection Pooling

The application uses `DATABASE_URL` to connect to Supabase. For production scalability, **Supabase Connection Pooling** (port 6543 via PgBouncer) should be enabled.

### Step-by-step

1. **Go to Supabase Dashboard**
   Navigate to your project at [supabase.com/dashboard](https://supabase.com/dashboard).

2. **Open Connection Pooling**
   In the left sidebar, go to **Database** > **Connection Pooling**.

3. **Enable Connection Pooling**
   - Click **"Enable connection pooling"** if not already active.
   - Select **"Transaction mode"** (recommended for serverless/API usage).

4. **Copy the Connection String**
   - The pooler connection string will look like:
     ```
     postgresql://postgres.[project-ref]:[password]@[region].pooler.supabase.com:6543/postgres
     ```
   - Copy the full string.

5. **Set in `.env`**
   Open your `.env` file and set:
   ```env
   DATABASE_URL=postgresql://postgres.[project-ref]:[password]@[region].pooler.supabase.com:6543/postgres
   ```

6. **Verify**
   Run the pooler check workflow (GitHub Actions: `Check Pooler`) or test manually:
   ```bash
   psql "$DATABASE_URL" -c "SELECT 1"
   ```

### Troubleshooting

- **Port 6543 not connecting:** Make sure connection pooling is enabled in the Supabase dashboard.
- **Port 5432 still works** (direct connection) but is not recommended for production — it has a limited connection pool.
- **Auth and realtime features** still use 5432; the pooler is for database queries from the API and backend workers.
