# Update signing keys

`update.pub` is the appliance's baked update-verification key. `apply-update.sh`
verifies every dropped update bundle against it before applying — a tampered or
unsigned bundle is rejected.

The **private** key (`update.key`) is NOT in this repo and must live under
controlled custody (build box / HSM / offline media). Sign a bundle with:

```sh
openssl pkeyutl -sign -inkey update.key -rawin -in update.tar -out update.tar.sig
```

Generate a keypair (once):

```sh
openssl genpkey -algorithm ED25519 -out update.key
openssl pkey -in update.key -pubout -out update.pub
```
