# Decky Store Proxy

A simple proxy for the Decky Plugin Store catalogue and resources.
![proxy-diagram.svg](docs/diagrams/proxy-diagram.svg)

## API structure

`GET /` serves a small info page with useful links and proxy config information.

`GET /docs` serves the Swagger UI page for the API.


### Store API

- `GET /plugins` — relay the catalogue and substitute resource URLs.
  > **The proxy modifies the response**.
  > All artifact and image URLs are replaced with links to the proxy's _Resource API_.
  > For plugin versions whose `artifact` field is missing or `null`, the proxy generates an artifact URL from the version's hash.
  > 
  > This is needed to route resource traffic through the proxy.

- `POST /plugins/{plugin_name}/versions/{version_name}/increment` — relay installation statistics.\
  > Forwards the plugin name, version, and `isUpdate` flag to the upstream store.

### Resource API

- `GET /resources/hash/{hash}` — retrieve the artifact by hash from the default Decky CDN.
  > This endpoint is used when the upstream store omits the `artifact` field or sets it to `null`.
  > The version's hash is used to identify the artifact on the CDN.
  > 
  > The proxy uses the same URL pattern as Decky Loader for retrieving plugin artifacts:\
  > `https://cdn.tzatzikiweeb.moe/file/steam-deck-homebrew/versions/${hash}.zip` 

- `GET /resources/base64/{base64url}.{signature}` — retrieve an artifact or image from its original URL.
  > When the upstream store returns an artifact or image URL, the proxy encodes it using Base64URL, signs the encoded value with a secret key, and builds a resource URL for this endpoint.
  > 
  > **Why sign the URL?** To prevent third parties from using this server to fetch arbitrary URLs, including bots routing GET requests through it to hide their own IP addresses.
  > Signing restricts this endpoint to resource URLs that the proxy received from the upstream catalogue.

### CORS

For all endpoints, CORS allows the origin `https://steamloopback.host`, the `GET` method, and the `X-Decky-Version` header.


## Environment variables

All three variables are required. The Python application loads `.env` from the current working directory; existing environment variables take precedence.

| Variable               | Example                                | Contents                                                                                     | Purpose                     |
|------------------------|----------------------------------------|----------------------------------------------------------------------------------------------|-----------------------------|
| `DOMAIN`               | `decky.example.com`                    | Hostname without a scheme or path                                                            | Public proxy domain         |
| `STORE_URL`            | `https://plugins.deckbrew.xyz/plugins` | Absolute HTTP(S) catalogue URL without credentials, a query, a fragment, or a trailing slash | Upstream catalogue endpoint |
| `RESOURCE_SIGNING_KEY` | `random`, `0bf7ac39b5a4e7bf815e617e`   | A secret string, or the word `random` to generate a new key on every server start            | Resource URL signing key    |

With `random`, previously generated resource links stop working after a restart; clients must refresh the catalogue to obtain new links. To keep links valid across restarts, configure a fixed secret.

## Development

Prerequisites: uv and Python 3.14.8 (uv downloads it if needed).
Configure `.env` using the variables above.

- `uv sync --locked` - sync the development environment.
- `uv build --wheel` - build the release wheel.
- `uv run uvicorn decky_proxy.main:app --host 127.0.0.1 --port 8000` - run locally.
- `uv run uvicorn decky_proxy.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.0/8,::1/128` - run behind a local reverse proxy.

## License

Project code is licensed under the [MIT License](LICENSE).

IconPark icons used in the diagrams are licensed separately under
[Apache-2.0](docs/diagrams/icons/LICENSE-IconPark.txt).
