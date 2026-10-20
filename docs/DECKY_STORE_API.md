# Decky Store Public Plugin API

This document describes pinned source behavior; deployment behavior was not verified.

Source project: [SteamDeckHomebrew/decky-plugin-store](https://github.com/SteamDeckHomebrew/decky-plugin-store/tree/1899e87ad2ba13eb1f390f51cfcb7ba5850f345b). Branch: `main`. Commit: `1899e87ad2ba13eb1f390f51cfcb7ba5850f345b`. Checked: 2026-10-21.

**Version Rejection Note**:
Across all API routes, a supplied `X-Decky-Version` beginning with lowercase `v` is parsed as SemVer after stripping whitespace and leading `v` characters.
Versions below `3.3.0` are rejected with code `426`. Pre-releases of `3.3.0`, such as `v3.3.0-pre1`, are exempt.
Missing, unprefixed, or unparsable values pass the version gate.
Rejection occurs before the endpoint runs, without incrementing a counter or consuming the rate allowance.
`Content-Type` is `text/plain; charset=utf-8`, and the body is `Unsupported loader version, please upgrade.`.

## GET /plugins

### Request

```http
GET /plugins?query=Example&hidden=false&sort_by=name&sort_direction=desc
Accept: application/json
```

**Important headers**

| Header            | Required | Meaning                                        |
|-------------------|----------|------------------------------------------------|
| `Accept`          | No       | `application/json` is suitable for the catalog |
| `X-Decky-Version` | No       | Loader version used by the version gate        |

No custom header is required.

**Query parameters**

| Parameter        | Type                           | Required | Default      | Meaning                                                                                                  |
|------------------|--------------------------------|----------|--------------|----------------------------------------------------------------------------------------------------------|
| `query`          | String                         | No       | Empty string | SQL `LIKE '%{query}%'` against plugin name only; case-sensitive on PostgreSQL; `%` and `_` are wildcards |
| `tags`           | Repeated strings               | No       | Empty list   | Requires every supplied tag; repeated and comma-separated values are accepted; empty values are ignored  |
| `hidden`         | Boolean                        | No       | `false`      | Selects visible plugins when false and all plugins, including hidden ones, when true                     |
| `sort_by`        | `name`, `date`, or `downloads` | No       | Omitted      | Selects name, earliest version creation time, or aggregate downloads; omission selects plugin ID         |
| `sort_direction` | `desc` or `asc`                | No       | `asc`        | `desc` for descending sort, `asc` - for ascending.                                                       |

No request body.

**Notes**

CORS permits the browser origin `https://steamloopback.host`, credentials, all methods and request headers, and exposes all response headers.

### Response

#### 200 - Plugin catalog

**Important headers**

| Header         | Meaning            |
|----------------|--------------------|
| `Content-Type` | `application/json` |

**Schema**

The body is an array of plugin objects. No matches return `[]`.

```typescript
type Response = {
  id: number;                   // Plugin ID (integer)
  name: string;                 // Plugin name
  author: string;
  description: string;
  tags: string[];               // Ordered by tag text
  versions: {                  // Ordered by creation time, newest first
    name: string;              // Version name; semantic-version syntax is not required
    hash: string;              // Package hash; format is not constrained by the schema
    created: string;           // Date-time
    downloads: number;         // Version download counter (integer)
    updates: number;           // Version update counter (integer)
  }[];
  visible: boolean;             // Catalog visibility
  image_url: string;            // Image URL
  downloads: number | null;     // Sum of version download counters (integer)
  updates: number | null;       // Sum of version update counters (integer)
  created: string | null;       // Earliest version creation time (date-time)
  updated: string | null;       // Latest version creation time (date-time)
}[];
```

**Notes**

An empty `versions` array is permitted.

#### 422 - Invalid query parameter

Invalid query parameter values produce FastAPI's standard validation error response. See [FastAPI request validation errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#override-request-validation-exceptions).

## GET /plugins/versions

### Request

```http
GET /plugins/versions
Accept: application/json
X-Decky-Version: v3.3.0
```

**Important headers**

| Header            | Required | Meaning                                              |
|-------------------|----------|------------------------------------------------------|
| `Accept`          | No       | `application/json` is suitable for the response      |
| `X-Decky-Version` | No       | Loader version used by the version gate              |

No custom header is required. No query parameters or request body are defined. Catalog filters and sorting parameters do not apply.

**Notes**

CORS permits the browser origin `https://steamloopback.host`, credentials, all methods and request headers, and exposes all response headers.

### Response

#### 200 - Latest plugin versions

**Important headers**

| Header         | Meaning            |
|----------------|--------------------|
| `Content-Type` | `application/json` |

**Schema**

The body is an object keyed by exact plugin name. Each value is a two-element array containing the latest version name and package hash. The schema below is a TypeScript type declaration, not a literal JSON response.

```typescript
type Response = {
  [plugin_name: string]: [version: string, hash: string];
} | null;
```

**Notes**

Visible and hidden plugins are included. Plugins without versions are omitted; no rows return `{}`. The latest version is selected by creation time descending, then version ID ascending, rather than by semantic-version comparison. No archive URL is emitted. The response model permits `null`, although the current database implementation returns an object.

## POST /plugins/{plugin_name}/versions/{version_name}/increment

### Request

```http
POST /plugins/Example/versions/1.0.0/increment?isUpdate=false
```

**Important headers**

| Header             | Required | Meaning                                                                                             |
|--------------------|----------|-----------------------------------------------------------------------------------------------------|
| `cf-connecting-ip` | No       | Used as client IP for rate limiting when present; otherwise the connection's client address is used |
| `X-Decky-Version`  | No       | Loader version used by the version gate                                                             |

No custom header is required. No `Content-Type` header is needed.

**Path parameters**

| Parameter      | Type   | Required | Meaning                                          |
|----------------|--------|----------|--------------------------------------------------|
| `plugin_name`  | String | Yes      | Exact plugin name from the catalog, URL-encoded  |
| `version_name` | String | Yes      | Exact version name from the catalog, URL-encoded |

**Query parameters**

| Parameter  | Type    | Required | Default | Meaning                                             |
|------------|---------|----------|---------|-----------------------------------------------------|
| `isUpdate` | Boolean | No       | `true`  | True increments updates; false increments downloads |

No request body.

**Notes**

The limit is two successful increments per fixed daily window per plugin name and client IP, shared across all versions and both counter modes. Failed requests do not consume the allowance.

CORS permits the browser origin `https://steamloopback.host`, credentials, all methods and request headers, and exposes all response headers.

### Response

#### 200 - Counter incremented

The requested version's update or download counter was incremented according to `isUpdate`. Subsequent catalog requests read the counters from the database.

#### 404 - Plugin or version not found

No plugin or version matches the supplied names. This response does not consume the allowance.

#### 429 - Rate allowance exhausted

The allowance is exhausted. This response can also occur for an unknown version. No rate-limit or `Retry-After` header is supplied.

#### 422 - Invalid query parameter

Invalid query parameter values produce FastAPI's standard validation error response. See [FastAPI request validation errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#override-request-validation-exceptions).
