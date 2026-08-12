# Local TLS assets

The Docker local profile expects these two untracked files in
`deploy/tls/local/`:

- `fullchain.pem`
- `privkey.pem`

They are only a local certificate and key for `https://kdafik.localhost`; never copy a
production certificate or key here. Generate them with PowerShell from the repository
root:

```powershell
./deploy/scripts/new-local-tls.ps1
```

The script first searches PATH and then standard OpenSSL and Git for Windows
installation paths. If it still cannot find OpenSSL, install it or add its bin
directory to PATH. If the browser warns about the self-signed certificate, inspect
and trust it only for this local hostname.
Do not import it as a general trusted certificate and do not reuse it outside the
local preview.
