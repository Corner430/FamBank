'use strict';
const mysql = require('mysql2/promise');

let pool = null;

/**
 * Get or create MySQL connection pool.
 * In cloud function environment, the pool persists across warm invocations.
 */
function getPool() {
  if (!pool) {
    const addr = process.env.MYSQL_ADDRESS || '';
    const host = addr ? addr.split(':')[0] : '10.0.0.1';
    const port = addr ? parseInt(addr.split(':')[1]) : 3306;
    const user = process.env.MYSQL_USERNAME || 'root';
    const password = process.env.MYSQL_PASSWORD || '';
    const database = process.env.MYSQL_DBNAME || 'fambank-prod-5g8v3rta823bda48';

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'info',
      func: '_shared',
      message: 'Creating connection pool',
      data: { host, port, user, database, hasPassword: !!password },
    }));

    pool = mysql.createPool({
      host,
      port,
      user,
      password,
      database,
      waitForConnections: true,
      connectionLimit: 3,
      connectTimeout: 10000,
      charset: 'utf8mb4',
      supportBigNumbers: true,
      bigNumberStrings: true,
    });
  }
  return pool;
}

/**
 * Execute a query with connection from pool
 */
async function query(sql, params) {
  const [rows] = await getPool().execute(sql, params);
  return rows;
}

/**
 * Get a connection for transaction use
 */
async function getConnection() {
  return getPool().getConnection();
}

module.exports = { getPool, query, getConnection };
